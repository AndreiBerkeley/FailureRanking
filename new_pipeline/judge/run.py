#!/usr/bin/env python3
"""Run the measurement judge over a trace set.

    python -m new_pipeline.judge.run --taxonomy <tax.json> --traces <dir> --out <dir>

One result per trace, which is one (task, candidate) pair. The result is a code
count map and nothing else; everything the run also learns travels in a sidecar
that no scoring path has to read.

    {"A.1": 2, "C.3": 1}

STAGES, each independently switchable

    panel   --annotators N   N independent readers, each given the taxonomy
    open    --open / --no-open   one reader given NO vocabulary, then a mapping
                                 pass onto the taxonomy with "none" allowed
    vote    --threshold K    a code fires when K of N annotators reported it

Deliberation is deliberately absent. Two reasons, both about this being the
scoring instrument rather than an instrument-improvement step. A threshold vote
is mechanically identical for every trace and every candidate, where a
deliberation's outcome turns on which annotator speaks first. And the vote split
is the raw material for a later confidence layer: recorded for free while the
annotators are independent, destroyed unrecoverably once they reconcile.

FAILURE IS NOT SILENCE
A trace whose calls did not all succeed is recorded with status "failed" and an
empty code map that no aggregation counts. "Judged, found nothing" and "we could
not judge this" must never collapse into the same empty dict, or missing evidence
becomes evidence of no failure. Partial panels are refused for the same reason a
vote threshold exists: 2 of 2 is not the evidence 2 of 4 is, and accepting it
would let a candidate whose traces fail more often be judged on a weaker panel.

GOLD
Stripped at the boundary by the shared rule in pipeline/goldfree.py, and the
removed keys are recorded per trace so the outcome-free claim is auditable.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median_low

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from new_pipeline import goldfree                                    # noqa: E402
from new_pipeline.judge import judge                          # noqa: E402
from new_pipeline.llm import gemini_call, llm_call, log       # noqa: E402


def _base_result(path: Path, clean, removed):
    md = clean.get("metadata") or {}
    return {"trace_id": clean.get("trace_id") or path.stem,
            "task_id": md.get("task_source_id"),
            "candidate_index": md.get("candidate_index"),
            "status": "failed", "codes": {}, "error": None, "gold_stripped": removed}


def _finish(result, panel, panel_turns, problems, open_counts, open_details, unmapped,
            expected, cfg):
    final, votes = judge.consolidate(panel, open_counts, cfg["threshold"], agg=median_low)
    src = defaultdict(list)
    for c in votes:
        if votes[c] >= cfg["threshold"]:
            src[c].append("panel")
    for c in open_counts:
        src[c].append("open")
    by_turn = defaultdict(Counter)
    for pt in panel_turns:
        for e in pt:
            for code in e["codes"]:
                by_turn[f"{e['turn']}:{e['agent']}"][code] += 1
    result.update({
        "status": "judged", "codes": final,
        "panel": {"annotators": panel, "votes": dict(votes), "n": cfg["annotators"],
                  "threshold": cfg["threshold"], "per_turn": panel_turns},
        "open": {"problems": problems, "mapped": open_counts,
                 "details": open_details, "unmapped": unmapped},
        "source": {c: src[c] for c in final},
        "turns": expected,
        "votes_by_turn": {k: dict(v) for k, v in by_turn.items()},
    })
    return result


def judge_batch(paths: list, taxonomy, tax_text, valid_ids, calls, cfg) -> dict:
    """Judge several traces in the same calls. Returns {path: result}.

    Every trace and every turn must be accounted for in each response; a
    response that drops one is re-asked once, then the whole batch is recorded
    failed (partial panels are refused, and a trace judged by fewer readers
    than its neighbours would be judged on weaker evidence).
    `calls` = {"panel": (call, model), "open": (call, model)}.
    """
    rendered, expected, results, blocks = {}, {}, {}, []
    for path in paths:
        raw = json.loads(path.read_text())
        clean, removed = goldfree.strip(raw)
        res = _base_result(path, clean, removed)
        tid = res["trace_id"]
        text, turns = judge.render_turns(clean, cfg["agents"], cfg["max_trace_chars"])
        if not turns:
            res["error"] = "trace renders with no agent turns"
        rendered[tid] = (text, turns); results[path] = res
        expected[tid] = [{"turn": t["turn"], "agent": t["agent"]} for t in turns]
        blocks.append(f"### trace {tid}\n{text}")
    live = [p for p in paths if results[p]["error"] is None]
    if not live:
        return results
    exp = {results[p]["trace_id"]: expected[results[p]["trace_id"]] for p in live}
    batch_text = "\n\n".join(b for p, b in zip(paths, blocks) if p in live)

    def fail_all(msg):
        for p in live:
            results[p]["error"] = msg
        return results

    pcall, pmodel = calls["panel"]
    ocall, omodel = calls["open"]

    # ---- panel -----------------------------------------------------------
    panel = {results[p]["trace_id"]: [] for p in live}
    panel_turns = {results[p]["trace_id"]: [] for p in live}
    for i in range(cfg["annotators"]):
        got = judge.annotate_batch(pcall, pmodel, batch_text, tax_text, valid_ids, exp)
        if got is None:
            return fail_all(f"annotator {i} failed after retries")
        for tid in panel:
            pt, tc = got.get(tid, ([], {}))
            panel[tid].append(tc); panel_turns[tid].append(pt)

    # ---- open branch -----------------------------------------------------
    problems = {tid: [] for tid in panel}
    open_counts = {tid: {} for tid in panel}
    details = {tid: [] for tid in panel}
    unmapped = {tid: [] for tid in panel}
    if cfg["open"]:
        got = judge.open_batch(ocall, omodel, batch_text, exp)
        if got is None:
            return fail_all("open pass failed after retries")
        for pr in got:
            if pr["trace_id"] in problems:
                problems[pr["trace_id"]].append(pr)
        flat = [pr for tid in problems for pr in problems[tid]]
        if flat:
            mapped = judge.map_open(ocall, omodel, [pr["problem"] for pr in flat],
                                    tax_text, valid_ids)
            if mapped is None:
                return fail_all("open mapping failed after retries")
            _, dets = mapped
            for d in dets:                       # join by index, never by text
                k = d.get("index")
                src = flat[k] if isinstance(k, int) and 0 <= k < len(flat) else None
                if src is None:
                    continue
                d["turn"] = src["turn"]; d["agent"] = src["agent"]
                tid = src["trace_id"]
                details[tid].append(d)
                if d.get("verdict") in ("stretch", "uncovered", "unanswered"):
                    unmapped[tid].append(d)
                for c in (d.get("codes") or []):
                    if c.get("fitness", 0) >= judge.FIT_GOOD:
                        open_counts[tid][c["code"]] = open_counts[tid].get(c["code"], 0) + 1

    for p in live:
        tid = results[p]["trace_id"]
        _finish(results[p], panel[tid], panel_turns[tid], problems[tid], open_counts[tid],
                details[tid], unmapped[tid], exp[tid], cfg)
    return results


def judge_one(path: Path, taxonomy, tax_text, valid_ids, call, model, cfg) -> dict:
    """Single-trace convenience over judge_batch (kept for tests and callers)."""
    calls = {"panel": (call, model), "open": (call, model)}
    if cfg.get("per_turn"):
        # one call per turn: batch of one, unit of one turn each
        raw = json.loads(path.read_text()); clean, removed = goldfree.strip(raw)
        res = _base_result(path, clean, removed)
        text, turns = judge.render_turns(clean, cfg["agents"], cfg["max_trace_chars"])
        if not turns:
            res["error"] = "trace renders with no agent turns"; return res
        tid = res["trace_id"]
        expected = [{"turn": t["turn"], "agent": t["agent"]} for t in turns]
        panel, panel_turns = [], []
        for i in range(cfg["annotators"]):
            pt_all, total = [], Counter()
            for t, e in zip(turns, expected):
                got = judge.annotate_batch(call, model, f"### trace {tid}\n{t['block']}",
                                           tax_text, valid_ids, {tid: [e]})
                if got is None:
                    res["error"] = f"annotator {i} failed after retries"; return res
                pt, tc = got.get(tid, ([], {})); pt_all.extend(pt); total.update(tc)
            panel.append(dict(total)); panel_turns.append(pt_all)
        problems, open_counts, dets, unm = [], {}, [], []
        if cfg["open"]:
            for t, e in zip(turns, expected):
                got = judge.open_batch(call, model, f"### trace {tid}\n{t['block']}", {tid: [e]})
                if got is None:
                    res["error"] = "open pass failed after retries"; return res
                problems.extend(got)
            if problems:
                mapped = judge.map_open(call, model, [p["problem"] for p in problems], tax_text, valid_ids)
                if mapped is None:
                    res["error"] = "open mapping failed after retries"; return res
                open_counts, dets = mapped
                for d in dets:
                    k = d.get("index"); src = problems[k] if isinstance(k, int) and 0 <= k < len(problems) else {}
                    d["turn"] = src.get("turn"); d["agent"] = src.get("agent")
                unm = [d for d in dets if d.get("verdict") in ("stretch", "uncovered", "unanswered")]
        return _finish(res, panel, panel_turns, problems, open_counts, dets, unm, expected, cfg)
    return judge_batch([path], taxonomy, tax_text, valid_ids, calls, cfg)[path]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--traces", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="gemini-3.6-flash",
                    help="gemini id, or openrouter/<vendor>/<model>")
    ap.add_argument("--structure", type=Path, default=None,
                    help="benchmark structure json; names the agents in turn headers")
    ap.add_argument("--thinking", choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"], default=None)
    ap.add_argument("--max-output", type=int, default=65536,
                    help="thinking tokens count against this")
    ap.add_argument("--timeout", type=int, default=900,
                    help="per-call read timeout in seconds. A batched prompt is "
                         "~50k tokens and a reasoning model under load can take "
                         "minutes on it; the transport default of 300 was timing "
                         "out the open reader and failing whole batches.")
    ap.add_argument("--per-turn", action="store_true",
                    help="one call per agent turn per reader, instead of one per trace")
    ap.add_argument("--traces-per-call", type=int, default=1,
                    help="traces judged in one call (each response must account for "
                         "every trace and every turn). Cuts calls by this factor.")
    ap.add_argument("--panel-model", default=None,
                    help="model for the panel annotators (default: --model)")
    ap.add_argument("--open-model", default=None,
                    help="model for the open reader and its mapping (default: --model)")
    ap.add_argument("--annotators", type=int, default=4)
    ap.add_argument("--threshold", type=int, default=2,
                    help="a code fires when this many annotators reported it")
    ap.add_argument("--open", dest="open", action="store_true", default=True)
    ap.add_argument("--no-open", dest="open", action="store_false",
                    help="panel only; drops the vocabulary-free reader")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-trace-chars", type=int, default=0,
                    help="0 = never elide (default). Eliding drops turns.")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tasks", type=Path, default=None,
                    help="JSON naming which task ids to judge: a bare list, or an "
                         "object addressed by --tasks-key. Traces for every other "
                         "task in --traces are skipped entirely.")
    ap.add_argument("--tasks-key", action="append", default=None, metavar="DOTTED.PATH",
                    help="path into the --tasks object, e.g. portions.set-B. "
                         "Repeatable; the union of all keys is judged.")
    ap.add_argument("--limit", type=int, help="judge only the first N traces")
    ap.add_argument("--no-retry-failed", action="store_true",
                    help="resume past failed traces instead of retrying them")
    ap.add_argument("--max-attempts", type=int, default=3,
                    help="give up on a trace after this many failed attempts")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the exact prompts for one trace; spend nothing")
    a = ap.parse_args()

    if a.per_turn and a.traces_per_call > 1:
        raise SystemExit("--per-turn and --traces-per-call > 1 are contradictory")
    if a.threshold > a.annotators:
        raise SystemExit(f"--threshold {a.threshold} exceeds --annotators "
                         f"{a.annotators}: no code could ever fire")

    taxonomy = json.loads(a.taxonomy.read_text())
    if "codes" not in taxonomy:
        raise SystemExit(f"{a.taxonomy} has no flat 'codes' list")
    tax_text = judge.render_taxonomy(taxonomy)
    valid_ids = {c["id"] for c in taxonomy["codes"]}

    files = sorted(p for p in a.traces.glob("*.json")
                   if p.name not in ("outcomes.json", "pool_manifest.json"))   # export_pool sidecars, not traces

    if a.tasks:
        doc = json.loads(a.tasks.read_text())
        want: set[str] = set()
        if a.tasks_key:
            for key in a.tasks_key:
                node = doc
                for part in key.split("."):
                    if not isinstance(node, dict) or part not in node:
                        raise SystemExit(f"--tasks-key {key!r}: no {part!r} in {a.tasks}")
                    node = node[part]
                if not isinstance(node, list):
                    raise SystemExit(f"--tasks-key {key!r} is {type(node).__name__}, not a list")
                want |= set(node)
        elif isinstance(doc, list):
            want = set(doc)
        else:
            raise SystemExit(f"{a.tasks} is an object; name the ids with --tasks-key")
        if not want:
            raise SystemExit(f"--tasks selected no task ids from {a.tasks}")
        kept, seen = [], set()
        for f in files:
            tid = (json.loads(f.read_text()).get("metadata") or {}).get("task_source_id")
            if tid in want:
                kept.append(f); seen.add(tid)
        missing = want - seen
        if missing:
            raise SystemExit(f"--tasks named {len(missing)} task(s) with no trace in "
                             f"{a.traces}, e.g. {sorted(missing)[:3]}")
        log(f"  --tasks: {len(want)} tasks -> {len(kept)} of {len(files)} traces "
            f"({len(kept)/max(len(want),1):.1f} candidates per task)")
        files = kept

    if a.limit:
        files = files[:a.limit]
    if not files:
        raise SystemExit(f"no traces in {a.traces}")

    agents = None
    if a.structure:
        agents = list(json.loads(a.structure.read_text())["discovered_agents"]["agents"])
    cfg = {"annotators": a.annotators, "threshold": a.threshold, "open": a.open,
           "max_trace_chars": a.max_trace_chars, "agents": agents,
           "per_turn": a.per_turn}

    if a.dry_run:
        clean, removed = goldfree.strip(json.loads(files[0].read_text()))
        tt, turns = judge.render_turns(clean, agents, a.max_trace_chars)
        units = len(turns) if a.per_turn else 1
        per_trace = (a.annotators * units + (units + 1 if a.open else 0)) / max(1, a.traces_per_call)
        print(f"traces: {len(files)}   codes: {len(valid_ids)}   "
              f"annotators: {a.annotators}   threshold: {a.threshold}   "
              f"open: {a.open}   per-turn: {a.per_turn}   turns in first trace: {len(turns)}")
        print(f"calls per trace: ~{per_trace:.2f}   total: ~{int(len(files) * per_trace)}   "
              f"traces/call: {a.traces_per_call}   panel: {a.panel_model or a.model}   "
              f"open: {a.open_model or a.model}   thinking: {a.thinking}   elision: "
              f"{'none' if not a.max_trace_chars else a.max_trace_chars}")
        print(f"gold stripped from this trace: {removed}\n")
        print("=" * 78 + "\nANNOTATOR PROMPT\n" + "=" * 78)
        print(judge.ANNOTATE_TURNS_PROMPT.format(layout=judge.TURN_LAYOUT, taxonomy=tax_text,
                                                 trace=tt, count_rule=judge.COUNT_RULE))
        print("=" * 78 + "\nOPEN PROMPT\n" + "=" * 78)
        print(judge.OPEN_TURNS_PROMPT.format(layout=judge.TURN_LAYOUT, trace=tt))
        print("=" * 78 + "\nMAPPING PROMPT\n" + "=" * 78)
        print(judge.MAP_PROMPT.format(taxonomy=tax_text,
                                      problems="0. <a problem from the open pass>"))
        print("\ndry run: nothing spent")
        return

    tdir = a.out / "traces"
    tdir.mkdir(parents=True, exist_ok=True)
    # A failed trace is missing evidence, not a result. Resuming past one would
    # let a transient outage permanently shrink the corpus -- and silently, since
    # the file exists and looks done. Failures are retried unless told otherwise,
    # with an attempt count so a trace that always fails is eventually left be.
    def wants_work(f):
        out = tdir / f"{f.stem}.json"
        if not out.exists():
            return True
        try:
            r = json.loads(out.read_text())
        except Exception:                                      # noqa: BLE001
            return True                       # unreadable is not a result either
        if r.get("status") == "judged":
            return False
        if a.no_retry_failed:
            return False
        return int(r.get("attempts", 1)) < a.max_attempts

    pending = [f for f in files if wants_work(f)]
    retried = sum(1 for f in pending if (tdir / f"{f.stem}.json").exists())
    if retried:
        log(f"  retrying {retried} previously-failed traces "
            f"(--no-retry-failed to skip, --max-attempts {a.max_attempts})")
    log(f"judge: {len(files)} traces, {len(pending)} to do, "
        f"{len(files) - len(pending)} already done")
    log(f"  {len(valid_ids)} codes | panel {a.annotators} (threshold "
        f"{a.threshold}) | open {a.open} | {a.workers} workers")

    kw = dict(temperature=a.temperature, retries=5, max_output=a.max_output,
              thinking=a.thinking, timeout=a.timeout)
    pcall, pmodel = llm_call(a.panel_model or a.model, **kw)
    ocall, omodel = llm_call(a.open_model or a.model, **kw)
    calls = {"panel": (pcall, pmodel), "open": (ocall, omodel)}
    log(f"  panel model {pmodel} | open model {omodel} | thinking {a.thinking} | "
        f"{a.traces_per_call} trace(s) per call")
    t0 = time.time()
    done = 0

    def attempts_of(f):
        prev = tdir / f"{f.stem}.json"
        if prev.exists():
            try:
                return int(json.loads(prev.read_text()).get("attempts", 1))
            except Exception:                                  # noqa: BLE001
                pass
        return 0

    def work(chunk):
        # A bug or an odd response in one batch must fail THAT batch, not the
        # run: an exception escaping a worker thread propagates through
        # fut.result() and stops everything, as it did once at 95/600.
        try:
            if a.per_turn:
                out = {}
                for f in chunk:
                    out[f] = judge_one(f, taxonomy, tax_text, valid_ids, pcall, pmodel, cfg)
            else:
                out = judge_batch(chunk, taxonomy, tax_text, valid_ids, calls, cfg)
        except Exception as exc:                                # noqa: BLE001
            log(f"  [!] batch of {len(chunk)} failed with {type(exc).__name__}: "
                f"{str(exc)[:120]}; recorded failed, will be retried")
            out = {}
            for f in chunk:
                raw = json.loads(f.read_text()); clean, removed = goldfree.strip(raw)
                r = _base_result(f, clean, removed)
                r["error"] = f"exception: {type(exc).__name__}: {str(exc)[:200]}"
                out[f] = r
        for f, r in out.items():
            r["attempts"] = attempts_of(f) + 1
        return out

    chunks = [pending[i:i + a.traces_per_call] for i in range(0, len(pending), a.traces_per_call)]
    # If the writing loop dies for any reason, queued batches must NOT keep
    # running: the default shutdown drains them, billing every call and
    # discarding every result. Measured once: 92 batches billed, 19 saved.
    ex = ThreadPoolExecutor(max_workers=a.workers)
    futs = [ex.submit(work, c) for c in chunks]
    try:
        for fut in as_completed(futs):
            for f, res in fut.result().items():
                (tdir / f"{f.stem}.json").write_text(json.dumps(res, indent=2))
                done += 1
                if done % 10 == 0 or done == len(pending):
                    log(f"  {done}/{len(pending)}  ({time.time()-t0:.0f}s)")
    except BaseException:
        log("  [!] writer loop interrupted; cancelling queued batches")
        ex.shutdown(wait=False, cancel_futures=True)
        raise
    ex.shutdown(wait=True)

    # ---- summary ---------------------------------------------------------
    results = [json.loads(p.read_text()) for p in sorted(tdir.glob("*.json"))]
    judged = [r for r in results if r["status"] == "judged"]
    failed = [r for r in results if r["status"] != "judged"]

    # per-candidate failure counts: if judging fails more often for one
    # candidate, exclusion is not neutral and the ranking inherits the bias
    fail_by_cand = Counter(r.get("candidate_index") for r in failed)
    fired = Counter()
    per_cand = defaultdict(lambda: {"traces": 0, "codes": Counter(), "by_agent": defaultdict(Counter)})
    for r in judged:
        c = r.get("candidate_index")
        per_cand[c]["traces"] += 1
        for code, n in r["codes"].items():
            fired[code] += 1
            per_cand[c]["codes"][code] += n
        for k, votes in (r.get("votes_by_turn") or {}).items():
            agent = k.split(":", 1)[1] if ":" in k else k
            for code, v in votes.items():
                if v >= r["panel"]["threshold"]:
                    per_cand[c]["by_agent"][agent][code] += 1

    summary = {
        "taxonomy": str(a.taxonomy),
        "traces": str(a.traces),
        "settings": {k: (str(v) if isinstance(v, Path) else v)
                     for k, v in vars(a).items()},
        "counts": {"total": len(results), "judged": len(judged),
                   "failed": len(failed)},
        "failed_by_candidate": {str(k): v for k, v in fail_by_cand.items()},
        "traces_firing_each_code": dict(fired.most_common()),
        "codes_never_fired": sorted(valid_ids - set(fired)),
        "unmapped_problems": sum(len(r.get("open", {}).get("unmapped") or [])
                                 for r in judged),
        "minutes": round((time.time() - t0) / 60, 1),
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2))
    (a.out / "profiles.json").write_text(json.dumps(
        {str(k): {"traces": v["traces"], "codes": dict(v["codes"]),
                  "by_agent": {ag: dict(cc) for ag, cc in v["by_agent"].items()}}
         for k, v in sorted(per_cand.items(), key=lambda x: (x[0] is None, x[0]))},
        indent=2))

    log("=" * 60)
    log(f"judged {len(judged)}/{len(results)}  failed {len(failed)}  "
        f"{summary['minutes']} min")
    if failed:
        log(f"  FAILED BY CANDIDATE: {summary['failed_by_candidate']} "
            "-- uneven failure across candidates biases the ranking")
    log(f"  codes that never fired: {len(summary['codes_never_fired'])} "
        f"of {len(valid_ids)}")
    log(f"  unmapped problems (never scored): {summary['unmapped_problems']}")
    log(f"  -> {a.out}/summary.json, profiles.json, traces/")


if __name__ == "__main__":
    main()
