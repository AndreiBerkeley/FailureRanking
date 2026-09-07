#!/usr/bin/env python3
"""Generation only, v2 framework. No gate, no judge, no refinement.

    python -m new_pipeline.generation.run --benchmark X --corpus <dir> --structure <f> --out <d>

Six model calls: domain analysis, subject-matter mechanisms, role mechanisms,
applicability, consolidation, rule validation. Contracts and trace selection are
free. Every stage writes its raw response before it is parsed, so a bad response
is diagnosable and re-runnable without paying again, and every stage is skipped
if its artifact already exists.

The corpus is passed through outcome-blind. It is not filtered by result and no
result reaches a prompt: goldfree.strip runs on every trace and the run refuses
to start if anything survives it.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from new_pipeline import goldfree                                    # noqa: E402
from new_pipeline.judge import judge as jrender               # noqa: E402
from new_pipeline.llm import gemini_call, llm_call, log       # noqa: E402
from new_pipeline.generation import contracts, prompts           # noqa: E402


def batches(corpus: Path, n_tasks: int, per_task: int, budget: int, seed: int = 0,
            trace_ids: list | None = None, agents: list | None = None,
            per_turn: bool = False, turns_per_call: int = 1):
    """Draw TASKS first, then candidates within each, at full trace length.

    Vocabulary coverage is bounded by task diversity, not by trace count. A
    fourth candidate failing a problem already seen adds an instance; a new
    problem can add a mechanism. Measured: raising traces from 24 to 72 within
    one 30-task slice grew findings 30 -> 75 but codes only 5 -> 6, because the
    tasks were exhausted long before the vocabulary was.

    Outcome fields are stripped here rather than refused. The reader must never
    see them, but requiring a pre-stripped corpus meant the raw pools -- which
    hold several times the task diversity -- could not be used at all.

    Traces are never truncated to fit a budget: eliding a long trace removed
    every turn the candidate wrote, and the reader then reported that the agent
    produced no output. The corpus is split across calls instead.

    When `trace_ids` is given the internal draw is bypassed: exactly those
    traces, in that order, are used, and n_tasks / per_task are ignored. This is
    how a sample recorded as an artifact is fed in, so the taxonomy's
    provenance names the same traces the sample does.
    """
    by_task = {}
    by_id = {}
    stripped = set()
    for p in sorted(corpus.glob("*.json")):
        raw = json.loads(p.read_text())
        clean, removed = goldfree.strip(raw)
        stripped.update(removed)
        md = clean.get("metadata") or {}
        tid = md.get("task_source_id")
        if tid is None:
            continue
        by_task.setdefault(tid, []).append((md.get("candidate_index"), clean))
        by_id[clean.get("trace_id")] = (tid, clean)

    if trace_ids is not None:
        missing = [t for t in trace_ids if t not in by_id]
        if missing:
            raise SystemExit(f"{len(missing)} requested trace ids not in corpus, "
                             f"first: {missing[:3]}")
        picked = [by_id[t][1] for t in trace_ids]
        tasks = sorted({by_id[t][0] for t in trace_ids})
    else:
        rng = random.Random(seed)
        tasks = sorted(by_task)
        rng.shuffle(tasks)
        tasks = tasks[:n_tasks]

        picked = []
        for tid in tasks:
            entries = sorted(by_task[tid], key=lambda e: str(e[0]))
            rng.shuffle(entries)
            picked.extend(c for _, c in entries[:per_task])

    # One candidate per batch. A conformance batch is shown its agents'
    # contracts, and those differ by candidate, so mixing candidates in a
    # batch means judging some traces against rules they never had.
    # Turns are delineated explicitly (instructions / input / output per
    # agent), and every batch records which turns each trace has, so the
    # observation pass can be held to one account per turn.
    from new_pipeline.generation.render import render_turns
    # Each item is (trace_id, rendered text, [turn entries it holds]). Whole
    # traces by default; with per_turn, one item per agent turn, holding only
    # that turn's block. By the contract rule a turn is judged against its own
    # instructions and input, so nothing else in the trace bears on it, and a
    # call that sees one turn spends its attention on that turn alone.
    if per_turn:
        budget = 0          # grouping is by turn count below, not by chars
    by_cand, n_rendered = {}, 0
    for clean in picked:
        ci = (clean.get("metadata") or {}).get("candidate_index")
        tid = clean.get("trace_id")
        body, turns = render_turns(clean, agents)
        if not turns:
            raise SystemExit(
                f"trace {tid} renders with no agent turns; "
                "the reader would see nothing the candidate wrote")
        n_rendered += 1
        meta = [{"turn": t["turn"], "agent": t["agent"]} for t in turns]
        if per_turn:
            for t, m in zip(turns, meta):
                head = (f"### trace {tid}  (this batch holds turn {t['turn']} of "
                        f"{len(turns)} only; account for that turn)")
                by_cand.setdefault(ci, []).append((tid, f"{head}\n{t['block']}", [m]))
        else:
            by_cand.setdefault(ci, []).append((tid, f"### trace {tid}\n{body}", meta))

    out = []
    for ci in sorted(by_cand, key=lambda k: (k is None, k)):
        groups, cur, size = [], [], 0
        for item in by_cand[ci]:
            r = item[1]
            full = (len(cur) >= max(1, turns_per_call)) if per_turn else \
                   (cur and size + len(r) > budget)
            if cur and full:
                groups.append(cur); cur, size = [], 0
            cur.append(item); size += len(r)
        if cur:
            groups.append(cur)
        for g in groups:
            expected = {}
            for tid, _, meta in g:
                expected.setdefault(tid, []).extend(meta)
            ids = list(expected)
            out.append(("\n\n".join(r for _, r, _ in g), ids, ci, expected))
    return out, n_rendered, len(tasks), sorted(stripped)


def salvage(raw: str):
    """Parse a response that embeds verbatim trace text, tolerating the two ways
    that reliably breaks.

    A reader asked to quote exact spans must put arbitrary characters inside JSON
    strings. Trace text carries backslashes (mathematical notation especially),
    which arrive as invalid escapes; and a long quote can leave the response cut
    off mid-string. Both cost the whole batch under a strict parse, when most of
    the findings in it are intact and recoverable.

    Salvage never invents content. It repairs escaping, and it truncates to the
    last complete entry -- so what is returned is a prefix of what was said, and
    the shortfall is visible to the coverage check downstream.
    """
    import re
    try:
        return json.loads(raw), None
    except Exception as first:
        pass
    fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw)   # lone backslash -> escaped
    try:
        return json.loads(fixed), "repaired invalid escapes"
    except Exception:
        pass
    # cut back to the last complete trace object and close the structure
    for cut in range(len(fixed), 0, -1):
        if fixed[cut - 1] != "}":
            continue
        for tail in ("]}", "}]}", "}]}]}"):
            try:
                d = json.loads(fixed[:cut] + tail)
                if isinstance(d, dict) and d.get("traces"):
                    return d, f"truncated response salvaged at {cut}/{len(raw)} chars"
            except Exception:
                continue
    return None, None


def turns_ok(d, expected: dict):
    """Every trace in the batch, and every turn of each, must be accounted for.
    `expected` maps trace_id -> [{"turn": k, "agent": name}, ...]."""
    ts = d.get("traces")
    if not isinstance(ts, list) or not ts:
        return "expected a non-empty 'traces' list"
    got = {str(x.get("trace_id")): x for x in ts if isinstance(x, dict)}
    miss = [t for t in expected if t not in got]
    if miss:
        return (f"{len(miss)} of {len(expected)} traces are absent from the "
                f"response: {miss[:4]}. Every trace must appear.")
    problems = []
    for tid, turns in expected.items():
        want = [t["turn"] for t in turns]
        entries = got[tid].get("turns")
        if not isinstance(entries, list):
            problems.append(f"{tid}: no 'turns' list")
            continue
        have = []
        for e in entries:
            if isinstance(e, dict):
                try:
                    have.append(int(e.get("turn")))
                except (TypeError, ValueError):
                    pass
        absent = [k for k in want if k not in have]
        if absent:
            problems.append(f"{tid}: turns {absent} of {want} have no entry")
        for e in entries:
            if not isinstance(e, dict) or (e.get("findings") or []):
                continue
            ledger = e.get("steps")
            if isinstance(ledger, list):
                if len(ledger) < 2:
                    problems.append(f"{tid}: turn {e.get('turn')} ledger has "
                                    f"{len(ledger)} step(s); it was not walked")
                continue
            if not str(e.get("checked") or "").strip():
                problems.append(f"{tid}: turn {e.get('turn')} has no findings "
                                "and no 'checked' account")
    if problems:
        return ("Every turn of every trace needs exactly one entry, with "
                "'checked' filled in when findings are empty. Problems: "
                + "; ".join(problems[:5]))
    return None


def flatten_turns(x: dict, kind: str) -> tuple[list, int]:
    """Findings of one trace entry, each stamped with turn, agent, kind.
    Returns (findings, steps_checked summed over turns)."""
    out, steps = [], 0
    for e in (x.get("turns") or []):
        if not isinstance(e, dict):
            continue
        ledger = e.get("steps")
        if isinstance(ledger, list):
            steps += len(ledger)
        else:
            try:
                steps += int(e.get("steps_checked") or 0)
            except (TypeError, ValueError):
                pass
        for f in (e.get("findings") or []):
            if isinstance(f, dict):
                f["turn"] = e.get("turn")
                f["agent"] = e.get("agent")
                f["kind"] = kind
                out.append(f)
    return out, steps


def call_stage(name, prompt, out: Path, call, model, log_prefix=""):
    raw_f = out / f"{name}.raw.txt"
    json_f = out / f"{name}.json"
    (out / f"{name}.prompt.txt").write_text(prompt)
    if json_f.exists():
        log(f"  {name}: already done")
        return json.loads(json_f.read_text())
    log(f"  {name}: calling ({len(prompt):,} char prompt){log_prefix}")
    t0 = time.time()
    # An unparseable response used to end the run. It is usually a cut answer,
    # which a re-ask often completes; each failed attempt is kept on disk.
    parse_retries = 2
    for k in range(1, parse_retries + 2):
        raw = call(prompt, model)
        if raw is None:
            raise SystemExit(f"{name}: no response; prompt at {out / (name + '.prompt.txt')}")
        d, note = salvage(raw)
        if d is not None:
            raw_f.write_text(raw)               # saved BEFORE further checks
            break
        fail_f = out / f"{name}.fail{k}.raw.txt"
        fail_f.write_text(raw)
        if k > parse_retries:
            raise SystemExit(f"{name}: unparseable after {parse_retries} re-asks, "
                             f"last saved at {fail_f}")
        log(f"  {name}: [!] unparseable response ({len(raw):,} chars), saved at "
            f"{fail_f.name}; re-asking ({k}/{parse_retries})")
    if note:
        log(f"  {name}: [!] {note}")
    json_f.write_text(json.dumps(d, indent=2))
    log(f"  {name}: ok ({time.time()-t0:.0f}s, {len(raw):,} chars)")
    return d


def require(d, name, check, out: Path, prompt, call, model, retries=2):
    """Re-ask when a response does not satisfy its schema, keeping the best.

    Asking politely for a shape at the end of a very long prompt does not get
    one: the model returns its own field names and the parser silently reads
    None. Naming the violation and re-asking is cheap, and it is the difference
    between a missing field and a dropped finding.

    Retries do not improve monotonically. One attempt accounted for 122 of 168
    observations and the next returned nothing at all, so keeping the LAST
    attempt threw away the good one. Every attempt is scored and the best is
    kept; exhausting the retries returns that best with a warning rather than
    losing the stage.
    """
    def score(cand):
        """Lower is better: 0 clean, 1 has a problem, 2 unusable."""
        if not isinstance(cand, dict) or not cand:
            return 2
        return 0 if not check(cand) else 1

    best, best_score = d, score(d)
    for attempt in range(retries + 1):
        problem = check(best) if best_score < 2 else "unusable response"
        if best_score == 0:
            return best
        if attempt == retries:
            if best_score == 2:
                raise SystemExit(f"{name}: no usable response after {retries} "
                                 f"retries: {problem}")
            log(f"  {name}: [!] keeping best attempt despite: {problem}")
            return best
        log(f"  {name}: schema violation ({problem}); re-asking")
        fix = (prompt + "\n\n## CORRECTION\n"
               "Your previous response did not satisfy the required shape:\n"
               f"  {problem}\n"
               "Return the SAME content in the exact shape specified above. Use "
               "those field names literally. Do not rename, nest, or substitute "
               "them, and do not drop content to make it fit.")
        raw = call(fix, model)
        if raw is None:
            log(f"  {name}: no response on retry {attempt+1}")
            continue
        (out / f"{name}.retry{attempt+1}.raw.txt").write_text(raw)
        cand, _ = salvage(raw)
        cand_score = score(cand)
        if cand_score < best_score:
            best, best_score = cand, cand_score
            (out / f"{name}.json").write_text(json.dumps(best, indent=2))
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--structure", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--tasks", type=int, default=100,
                    help="distinct tasks to draw; this, not trace count, bounds "
                         "how much of the vocabulary can be found")
    ap.add_argument("--per-task", type=int, default=1,
                    help="candidates sampled per task")
    ap.add_argument("--trace-ids", type=Path, default=None,
                    help="file with one trace id per line; use exactly these "
                         "traces and ignore --tasks/--per-task")
    ap.add_argument("--work-ledger", action="store_true",
                    help="work pass returns a per-step ledger (2a-ledger schema) "
                         "instead of a count and a one-line summary")
    ap.add_argument("--turns-per-call", type=int, default=1,
                    help="with --per-turn-work: how many consecutive turns of one "
                         "candidate share a call (1 = one turn per call)")
    ap.add_argument("--per-turn-work", action="store_true",
                    help="run the work pass one agent turn per item: each item "
                         "holds one turn's instructions, input and output. More "
                         "calls, each small; the reader's attention is on one "
                         "turn at a time")
    ap.add_argument("--work-batch-chars", type=int, default=70000,
                    help="character budget for the step-by-step work pass; small "
                         "because re-deriving every step cannot be done at skim "
                         "depth across a large batch")
    ap.add_argument("--batch-chars", type=int, default=260000,
                    help="character budget per observation call; traces are "
                         "grouped to fit it and never truncated")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--thinking", choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"],
                    default=None, help="Gemini thinking level; unset = model default")
    ap.add_argument("--max-output", type=int, default=32768)
    ap.add_argument("--timeout", type=int, default=900,
                    help="per-call read timeout; a 250k-char prompt takes far "
                         "longer than the default")
    ap.add_argument("--dry-run", action="store_true",
                    help="build every prompt and report sizes; spend nothing")
    a = ap.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    structure = json.loads(a.structure.read_text())

    log("=" * 66)
    log(f"GENERATION v2  benchmark={a.benchmark}  (no gate, no judge, no refinement)")
    log("=" * 66)

    by_cand = contracts.extract_all(a.corpus, structure)
    (a.out / "contracts.json").write_text(json.dumps(
        {str(k): v for k, v in by_cand.items()}, indent=2))
    ctext_by = {ci: contracts.render(cs) for ci, cs in by_cand.items()}
    ctext_all = contracts.render_all(by_cand)
    n_versions = len({c["instructions"] for cs in by_cand.values() for c in cs})
    log(f"contracts: {len(by_cand)} candidates, "
        f"{len(next(iter(by_cand.values()), []))} agents, {n_versions} distinct "
        f"instruction sets ({len(ctext_all):,} chars rendered) -- free")

    ids = None
    if a.trace_ids is not None:
        ids = [l.strip() for l in a.trace_ids.read_text().splitlines() if l.strip()]
        (a.out / "trace_ids.txt").write_text("\n".join(ids) + "\n")
        log(f"fixed sample: {len(ids)} trace ids from {a.trace_ids}")
    agents = list(structure["discovered_agents"]["agents"])
    groups, n, n_tasks, stripped = batches(a.corpus, a.tasks, a.per_task,
                                           a.batch_chars, trace_ids=ids, agents=agents)
    work_groups, _, _, _ = batches(a.corpus, a.tasks, a.per_task,
                                   a.work_batch_chars, trace_ids=ids, agents=agents,
                                   per_turn=a.per_turn_work, turns_per_call=a.turns_per_call)
    total = sum(len(g) for g, _, _, _ in groups)
    per = f"{n / max(n_tasks, 1):.1f}" if ids else str(a.per_task)
    log(f"traces: {n} over {n_tasks} tasks ({per}/task), full length, "
        f"{total:,} chars -- free "
        f"({len(work_groups)} work batches, {len(groups)} conformance)")
    log(f"  outcome fields stripped before any prompt: {stripped or 'none present'}")
    traces = groups[0][0]   # later stages see one representative batch

    call, a.model = llm_call(a.model, temperature=a.temperature, retries=5,
                             max_output=a.max_output, timeout=a.timeout,
                             thinking=a.thinking)
    P = {}
    P["stage1"] = prompts.build("stage1", traces=traces)

    if a.dry_run:
        # later stages depend on earlier output; size them with placeholders
        stub = "<produced by the previous stage>"
        P["stage2a"] = prompts.build("stage2a", traces=groups[0][0])
        P["stage2b"] = prompts.build("stage2b", contracts=ctext_by[groups[0][2]],
                                     traces=groups[0][0])
        P["stage3"] = prompts.build("stage3", observations=stub, domain=stub,
                                    contracts=ctext_all)
        P["stage4"] = prompts.build("stage4", modes=stub, contracts=ctext_all,
                                    traces=traces)
        P["stage5"] = prompts.build("stage5", codes=stub)
        P["stage6"] = prompts.build("stage6")
        log("-" * 66)
        for k in ("stage1", "stage2a", "stage2b", "stage3", "stage4", "stage5",
                  "stage6"):
            log(f"  {k}: {len(P[k]):,} chars  (~{len(P[k])//4:,} tokens)")
            (a.out / f"{k}.prompt.txt").write_text(P[k])
        log(f"  6 calls for this benchmark. prompts written to {a.out}")
        log("dry run: nothing spent")
        return

    t0 = time.time()
    dom = call_stage("stage1_domain", P["stage1"], a.out, call, a.model)

    # --- discovery: no framework, per trace, miss nothing ---
    def obs_ok(d):
        ts = d.get("traces")
        if not isinstance(ts, list) or not ts:
            return "expected a non-empty 'traces' list"
        if not any(isinstance(x, dict) and "findings" in x for x in ts):
            return "no trace entry carries a 'findings' list"
        return None

    # Two passes per batch. The work check is not shown the contracts at all:
    # with them in view a reader satisfies "report what is wrong" with the first
    # rule violation it sees and never examines the reasoning.
    seen = {}
    work_stage = "stage2a_ledger" if a.work_ledger else "stage2a"
    passes = [("work", work_stage, work_groups, lambda g, ci: {"traces": g}),
              ("conformance", "stage2b", groups,
               lambda g, ci: {"contracts": ctext_by[ci], "traces": g})]
    for tag, stage, grps, mk in passes:
        for i, (g, ids, ci, expected) in enumerate(grps, 1):
            pg = prompts.build(stage, **mk(g, ci))
            nm = f"stage2{tag[0]}_{tag}_{i}"

            def covered_ok(d, _exp=expected):
                return turns_ok(d, _exp)

            d = call_stage(nm, pg, a.out, call, a.model,
                           log_prefix=f"  [{tag} {i}/{len(grps)}]")
            d = require(d, nm, covered_ok, a.out, pg, call, a.model)
            for x in d["traces"]:
                if not isinstance(x, dict):
                    continue
                tid = str(x.get("trace_id"))
                rec = seen.setdefault(tid, {"trace_id": tid, "findings": [],
                                            "steps_checked": 0, "turns": []})
                fs, steps = flatten_turns(x, tag)
                rec["steps_checked"] = max(rec.get("steps_checked") or 0, steps)
                rec["findings"].extend(fs)
                if tag == "work":
                    rec["turns"] = [{"turn": e.get("turn"), "agent": e.get("agent"),
                                     "checked": e.get("checked")}
                                    for e in (x.get("turns") or []) if isinstance(e, dict)]
    seen_traces = list(seen.values())
    obs = {"traces": seen_traces}
    (a.out / "stage2_observation.json").write_text(json.dumps(obs, indent=2))
    n_find = sum(len(x.get("findings") or []) for x in seen_traces)
    covered = len(seen_traces)
    n_work = sum(1 for x in seen_traces for f in x["findings"]
                 if f.get("kind") == "work")
    steps = sum(int(x.get("steps_checked") or 0) for x in seen_traces)
    log(f"  observed: {n_find} findings across {covered}/{n} traces "
        f"({n_work} work, {n_find - n_work} conformance); "
        f"{steps} substantive steps walked")
    if covered < n:
        log(f"  [!] {n - covered} traces were not reported on")
    # A step-by-step pass reporting one or two steps for a substantial trace did
    # not walk it. The count is the only evidence that the pass did what it was
    # asked, so a shortfall is surfaced rather than assumed away.
    thin = [x["trace_id"] for x in seen_traces
            if int(x.get("steps_checked") or 0) <= 2]
    if thin:
        log(f"  [!] {len(thin)} of {covered} traces report <=2 substantive steps "
            f"checked; the work pass may have skimmed them (e.g. {thin[:3]})")

    # --- abstraction: the framework applies here ---
    p3 = prompts.build("stage3", observations=json.dumps(obs, indent=2),
                       domain=json.dumps(dom, indent=2), contracts=ctext_all)
    modes = call_stage("stage3_abstraction", p3, a.out, call, a.model)

    def modes_ok(d):
        ms = d.get("modes")
        if not isinstance(ms, list) or not ms:
            return "expected a non-empty 'modes' list"
        bad = [m for m in ms if not isinstance(m, dict) or not m.get("name")
               or m.get("column") not in ("general", "domain")]
        if bad:
            return (f"{len(bad)} of {len(ms)} modes lack a 'name' or a 'column' "
                    "of exactly 'general' or 'domain'")
        # Accounting is part of the contract, not a request. Asking for it held
        # at 24 traces and silently failed at 72: observations vanished without
        # appearing in "unplaced", which is indistinguishable from never having
        # been observed. A dropped observation is a lost mechanism.
        placed = sum(len(m.get("incidents") or []) for m in ms)
        skipped = len(d.get("unplaced") or [])
        lost = n_find - placed - skipped
        # Tolerance, because the check exists to catch SYSTEMATIC loss, not to
        # demand perfection. Refusing a response that accounted for 74 of 75
        # discards a good taxonomy over one observation; refusing one that
        # accounted for 51 of 75 is the whole point. Whatever slips through is
        # recorded rather than forgiven silently.
        if lost > max(2, int(0.05 * n_find)):
            return (f"{n_find} observations were given; {placed} appear as "
                    f"incidents and {skipped} in 'unplaced', leaving {lost} "
                    "unaccounted for. Every observation must appear in exactly "
                    "one of the two, even if several share a mode and even if "
                    "the reason is that it is not a mechanism.")
        return None
    modes = require(modes, "stage3_abstraction", modes_ok, a.out, p3, call, a.model,
                    retries=3)
    ms = modes["modes"]
    unplaced = modes.get("unplaced") or []
    _placed = sum(len(m.get("incidents") or []) for m in ms)
    _lost = n_find - _placed - len(modes.get("unplaced") or [])
    if _lost > 0:
        log(f"  [!] {_lost} of {n_find} observations unaccounted for "
            "(within tolerance; recorded in the artifact)")
    log(f"  abstracted: {len(ms)} modes "
        f"({sum(1 for m in ms if m['column']=='general')} general, "
        f"{sum(1 for m in ms if m['column']=='domain')} domain), "
        f"{len(unplaced)} observations unplaced")

    allm = {"modes": ms}
    app = call_stage("stage4_applicability",
                     prompts.build("stage4", modes=json.dumps(allm, indent=2),
                                   contracts=ctext_all, traces=traces),
                     a.out, call, a.model)
    spec = [x.get("specialised_code") for x in (app.get("applicability") or [])
            if x.get("verdict") == "specialise" and x.get("specialised_code")]
    flags = [x for x in (app.get("applicability") or []) if x.get("verdict") == "flag"]
    log(f"  applicability: {len(spec)} specialised, {len(flags)} flagged")

    cons = call_stage("stage5_consolidation",
                      prompts.build("stage5", codes=json.dumps(
                          {**allm, "specialised": spec}, indent=2)),
                      a.out, call, a.model)
    tax = cons.get("taxonomy", [])
    log(f"  consolidated: {len(ms)} + {len(spec)} -> {len(tax)} codes")

    # Validation judges each code in isolation, so a merged code that is far too
    # broad reads as clean: the defect exists only relative to what it replaced.
    # It therefore gets the provenance as well as the taxonomy.
    def val_ok(d):
        if not isinstance(d, dict):
            return "expected an object with 'checks' and 'taxonomy'"
        tx = d.get("taxonomy")
        if not isinstance(tx, list) or not tx:
            return ("expected a corrected 'taxonomy' list, not verdicts alone. "
                    "Emit the taxonomy with every correction applied.")
        ck = d.get("checks") or []
        failed = [c for c in ck if isinstance(c, dict) and any(
            c.get(k) not in ("yes", "ok", "n/a", None) for k in
            ("column_ok", "is_mechanism", "contract_ok", "agent_free",
             "granularity", "observable", "evidence_ok", "merge_ok"))]
        if failed and not d.get("corrections"):
            return (f"{len(failed)} codes failed a check but 'corrections' is "
                    "empty. A failing check must produce a correction.")
        return None

    p6 = (prompts.build("stage6")
          + "\n\n## THE TAXONOMY\n" + json.dumps(tax, indent=2)
          + "\n\n## WHAT EACH CODE CAME FROM\n"
          + json.dumps(cons.get("provenance", []), indent=2)
          + "\n\n## THE MODES BEFORE CONSOLIDATION\n"
          + json.dumps(ms, indent=2))
    val = call_stage("stage6_validation", p6, a.out, call, a.model)
    val = require(val, "stage6_validation", val_ok, a.out, p6, call, a.model,
                  retries=3)
    corrected = val.get("taxonomy") or tax
    ncorr = len(val.get("corrections") or [])
    log(f"  validated: {len(tax)} -> {len(corrected)} codes after {ncorr} "
        "correction(s)")
    tax = corrected

    final = {"benchmark": a.benchmark, "framework": "v2",
             "produced_by": "new_pipeline.generation.run (generation, stages 1-6)",
             "contracts": [c["agent"] for c in next(iter(by_cand.values()), [])],
             "observations": {"findings": n_find, "traces_covered": covered,
                              "work": n_work, "conformance": n_find - n_work},
             "modes_before_consolidation": len(ms),
             "unplaced_observations": unplaced,
             "observations_unaccounted": _lost,
             "codes": tax,
             "validation": val,
             "applicability": app.get("applicability", []),
             "flagged_for_evidence": flags,
             "provenance": cons.get("provenance", []),
             "minutes": round((time.time() - t0) / 60, 1)}
    (a.out / "taxonomy_v2.json").write_text(json.dumps(final, indent=2))
    log("=" * 66)
    log(f"DONE  {len(tax)} codes  {final['minutes']} min  -> {a.out}/taxonomy_v2.json")


if __name__ == "__main__":
    main()
