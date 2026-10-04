#!/usr/bin/env python3
"""Judge: apply a taxonomy to traces, one call per trace, adding modes as it goes.

    python judge.py --taxonomy <final_taxonomy.json> --traces <dir of trace files> --out <judge dir> \
        --model <provider/model> [--workers W] [--answers <answers.json>] [--structure <structure.json>] [--limit N] [--dry-run]

With --answers (JSON {trace_id: correct final answer}) each trace shows its correct answer at the top and the
concepts say how to use it, as in run.py --answers (the answer-provided variant).
Traces are judged in batches of W (default 6), in parallel, all with the same taxonomy.
With --no-new-modes the taxonomy stays fixed: an instance no mode fits is marked NONE, nothing is added. Each call reads
one trace, finds every failure instance, and gives each one a mode; an instance no mode fits gets a new
mode, proposed in the same call, and the new modes of one trace are distinct from each other. What the
judge considered and rejected is listed with the reason. At the end of each batch its new modes are
made distinct from each other (one call, when there are at least two; it replies with edits only) and
appended to the taxonomy with new ids, so every later batch is judged with them. Existing modes are
never changed. A trace too long for the context is split into parts as in run.py, one call per part.

Written at the end of each batch:
    <out>/traces/<trace file name>   the record the recovery pass (recovery/, from FailureRank) reads:
        python3 -m recovery.run --traces <same traces dir> --mapping <judge dir> --out <dir>
    <out>/taxonomy_extended.json     the taxonomy with every mode added so far

A point's turn follows recovery's grouping of messages into turns: a system message opens a turn and the
next assistant message closes it. --structure only supplies agent names, as it does for recovery.
Rerunning the same command replays saved replies and continues where it stopped (without --no-new-modes, keep the same
--workers, since the batches decide which modes each trace sees). With --no-new-modes the traces go through one
continuous pool of W workers instead of batches.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import itertools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import run as gen  # the generation pipeline: rendering, splitting, model calls, caching, edits

JUDGE = (gen.PROMPTS / "judge.md").read_text().strip()
JUDGE_FIXED = (gen.PROMPTS / "judge_fixed.md").read_text().strip()  # --no-new-modes: NONE instead of a new mode
NEW_MODES = (gen.PROMPTS / "judge_new_modes.md").read_text().strip()


def build(taxonomy_text: str, traces_text: str, new_modes: bool = True) -> str:
    body = JUDGE if new_modes else JUDGE_FIXED
    return gen.SEP.join([gen.CONCEPTS, gen.RULES,
                         body.replace("{taxonomy}", taxonomy_text).replace("{traces}", traces_text)])


def agent_name(system_message: str, idx: int, agents: list) -> str:
    """The same rule recovery renders turns with: 'Component:' when present, else the structure's agent list."""
    m = re.search(r"^Component:\s*(.+)$", system_message, re.M)
    name = m.group(1).strip() if m else (agents[idx] if idx < len(agents) else f"agent_{idx}")
    return name.replace(".predict", "")


def turn_map(trace: dict, agents: list):
    """message index -> turn number, and turn number -> agent. A message outside every turn (the task statement,
    a trailing tool result) goes to the turn before it, or the first turn."""
    where, names, k, sys_idx, open_ = {}, {}, 0, 0, False
    for i, m in enumerate(trace["messages"]):
        role, content = m.get("role"), m.get("content")
        content = content if isinstance(content, str) else json.dumps(content)
        if role == "system":
            k, open_ = k + 1, True
            names[k] = agent_name(content or "", sys_idx, agents)
            sys_idx += 1
            where[i] = k
        elif open_:
            where[i] = k
            open_ = role != "assistant"
        else:
            where[i] = k if k else None
    first = min(names) if names else None
    return {i: (t if t is not None else first) for i, t in where.items()}, names


def message_of(x):
    try:
        return int(x.get("message"))
    except (TypeError, ValueError):
        return None


def read_reply(res, t, where, names, text, ids, seq, new_modes, allow_new=True):
    """Points and rejected points from one reply. The reply's new modes are added to `new_modes` under
    provisional ids from `seq`; points carry those ids until the batch assigns final ones."""
    new = {}
    for m in (res.get("new_modes") or []) if allow_new else []:
        if isinstance(m, dict) and m.get("name"):
            pid = next(seq)
            new[str(m.get("id"))] = {"id": pid, **{f: m.get(f) for f in gen.EDIT_FIELDS}, "origin": "observed",
                                     "instances": [], "possible_at": [], "added_by": "judge"}
    points, rejected = [], []
    for x in res.get("instances") or []:
        raw = gen.norm_mode(x.get("mode"))
        is_new = raw in new
        mode = new[raw]["id"] if is_new else raw
        fits = is_new or mode in ids
        q, msg = x.get("quote"), message_of(x)
        points.append({"turn": where.get(msg), "agent": names.get(where.get(msg)), "message": msg,
                       "evidence": q or "", "problem": x.get("what_went_wrong"), "missing": x.get("missing"),
                       "codes": [mode] if fits else [],
                       "none_fits": not (fits and not is_new),  # no mode of the taxonomy as it stood fitted
                       "added_mode": mode if is_new else None,
                       "none_fits_what": x.get("none_fits") if raw == "NONE" else None,
                       "unknown_mode": None if fits or raw == "NONE" else raw,
                       "quote_valid": q is None or gen.canon(q) in gen.canon(text)})
        if is_new:
            new[raw]["instances"].append({"trace_id": t["trace_id"], "quote": q, "missing": x.get("missing"),
                                          "what_went_wrong": x.get("what_went_wrong")})
    for x in res.get("rejected") or []:
        msg = message_of(x)
        rejected.append({"turn": where.get(msg), "agent": names.get(where.get(msg)), "message": msg,
                         "evidence": x.get("quote") or "", "why": x.get("why")})
    new_modes += [m for m in new.values() if m["instances"]]
    return points, rejected


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taxonomy", type=Path, required=True, help="a taxonomy from run.py (final_taxonomy.json)")
    ap.add_argument("--traces", type=Path, required=True, help="dir with one JSON file per trace")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--workers", type=int, default=6,
                    help="W: calls in flight at once; a continuous pool with --no-new-modes, else batches of W traces")
    ap.add_argument("--no-new-modes", action="store_true",
                    help="keep the taxonomy fixed: mark unfitted instances NONE instead of adding modes")
    ap.add_argument("--structure", type=Path, default=None, help="optional; agent names only")
    ap.add_argument("--answers", type=Path, default=None,
                    help="JSON {trace_id: correct final answer}: the judge sees each trace's answer (answer-provided variant)")
    ap.add_argument("--limit", type=int, default=None, help="first N traces")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--context-tokens", type=int, default=1_000_000, help="the model's context window")
    ap.add_argument("--reserve-chars", type=int, default=200_000)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-output", type=int, default=32768)
    ap.add_argument("--price-in", type=float, default=None, help="USD per million input tokens, for the estimate")
    a = ap.parse_args()
    if not a.dry_run and not a.model:
        raise SystemExit("--model is required unless --dry-run")
    a.prompt_chars = (a.context_tokens - a.max_output) * 3
    trace_budget = a.prompt_chars - a.reserve_chars

    tax = json.loads(a.taxonomy.read_text())
    tax = list(tax["taxonomy"] if isinstance(tax, dict) else tax)
    initial_ids = [m["id"] for m in tax]
    agents = list(json.loads(a.structure.read_text())["discovered_agents"]["agents"]) if a.structure else []
    files = sorted(a.traces.glob("*.json"))[: a.limit]
    if a.answers:
        gen.use_answers(a.answers)
        missing = [f.stem for f in files if json.loads(f.read_text())["trace_id"] not in gen.ANSWERS]
        if missing:
            raise SystemExit(f"{a.answers} has no answer for {missing}")
    batches = [files[i:i + a.workers] for i in range(0, len(files), a.workers)]
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "traces").mkdir(exist_ok=True)
    gen.log(f"judging {len(files)} traces from {a.traces} "
            + (f"with {a.workers} workers, taxonomy fixed" if a.no_new_modes else f"in {len(batches)} batches of {a.workers}")
            + f", starting with {len(tax)} modes; model {a.model}; {'DRY RUN' if a.dry_run else 'LIVE'}")

    r = gen.Runner(a)
    per_mode, failed, added = Counter(), [], []
    n_points = n_rejected = n_existing = n_bad_quote = n_inst = 0

    def finish(f, t, d):
        """Write one trace's record and add it to the totals."""
        nonlocal n_points, n_rejected, n_existing, n_bad_quote
        names = turn_map(t, agents)[1]
        rec = {"trace_id": t["trace_id"], "task_id": t.get("task_id"), "attempts": 1, "turns": len(names)}
        if d["errors"]:
            rec.update(status="failed", error="; ".join(d["errors"]), codes={}, points=[], rejected=[])
            failed.append(t["trace_id"])
        else:
            seen = defaultdict(set)
            for p in d["points"]:
                for c in p["codes"]:
                    seen[c].add(p["turn"])
            rec.update(status="judged", error=None, points=d["points"], rejected=d["rejected"],
                       modes_added=sorted({p["added_mode"] for p in d["points"] if p["added_mode"]}),
                       codes={c: len(v) for c, v in sorted(seen.items())})
            n_points += len(d["points"])
            n_rejected += len(d["rejected"])
            n_existing += sum(not p["none_fits"] for p in d["points"])
            n_bad_quote += sum(not p["quote_valid"] for p in d["points"])
            per_mode.update(c for p in d["points"] for c in p["codes"])
        (a.out / "traces" / f.name).write_text(gen.dump(rec))

    def one(tax_text, u):
        try:
            return r.ask(f"judge_{gen.ukey(u)}", "judge", build(tax_text, gen.block([u]), not a.no_new_modes))
        except SystemExit as e:  # a trace whose reply never parses is recorded as failed, not fatal
            return {"_error": str(e)}

    if a.no_new_modes:
        # The taxonomy never changes, so every trace is independent: one pool, and a worker takes the next call as
        # soon as it is free (no batch waits for its slowest trace). A trace is written when all its parts are back.
        tax_text, ids = gen.dump(gen.slim(tax)), {m["id"] for m in tax}
        traces = [json.loads(f.read_text()) for f in files]
        jobs = [(fi, u) for fi, t in enumerate(traces) for u in gen.split_trace(t, trace_budget)]
        left = Counter(fi for fi, _ in jobs)
        got = defaultdict(dict)  # trace index -> part number -> reply
        done = 0
        if not a.dry_run:
            (a.out / "taxonomy_extended.json").write_text(gen.dump({"taxonomy": tax, "added": [], "from": str(a.taxonomy)}))
        with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(one, tax_text, u): (fi, u) for fi, u in jobs}
            for fut in cf.as_completed(futs):
                fi, u = futs[fut]
                got[fi][u["part"]] = fut.result()
                left[fi] -= 1
                if left[fi]:
                    continue
                t, d = traces[fi], {"points": [], "rejected": [], "errors": []}
                for _, res in sorted(got.pop(fi).items()):  # parts in order
                    if a.dry_run:
                        continue
                    if "_error" in (res or {}):
                        d["errors"].append(res["_error"])
                        continue
                    where, names = turn_map(t, agents)
                    pts, rej = read_reply(res or {}, t, where, names, gen.render(t), ids, None, [], allow_new=False)
                    d["points"] += pts
                    d["rejected"] += rej
                if not a.dry_run:
                    finish(files[fi], t, d)
                done += 1
                if not a.dry_run and (done % 25 == 0 or done == len(files)):
                    gen.log(f"{done}/{len(files)} traces judged; {len(failed)} failed")
        batches = []  # the batch path below does not run

    for bn, batch in enumerate(batches, 1):
        traces = [json.loads(f.read_text()) for f in batch]
        tax_text, ids = gen.dump(gen.slim(tax)), {m["id"] for m in tax}
        jobs = [(ti, u) for ti, t in enumerate(traces) for u in gen.split_trace(t, trace_budget)]

        with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
            replies = list(ex.map(lambda job: one(tax_text, job[1]), jobs))

        if a.dry_run and not a.no_new_modes:  # one distinctness call per batch at most
            r.ask(f"judge_new_modes_b{bn:03d}", "new_modes", gen.SEP.join(
                [gen.CONCEPTS, gen.RULES, NEW_MODES.replace("{modes}", gen.dump(gen.stub_taxonomy(4)))]))
        if a.dry_run:
            continue

        # read every reply of the batch; new modes get provisional ids
        new_modes, per_trace = [], defaultdict(lambda: {"points": [], "rejected": [], "errors": []})
        seq = (f"B{bn}-{k}" for k in itertools.count(1))
        for (ti, _), res in zip(jobs, replies):
            t, d = traces[ti], per_trace[ti]
            if "_error" in (res or {}):
                d["errors"].append(res["_error"])
                continue
            where, names = turn_map(t, agents)
            pts, rej = read_reply(res or {}, t, where, names, gen.render(t), ids, seq, new_modes,
                                  allow_new=not a.no_new_modes)
            d["points"] += pts
            d["rejected"] += rej

        # end of batch: make the new modes distinct from each other, then give them final ids
        alias, merge_log = {}, []
        if len(new_modes) >= 2:
            edits = r.ask(f"judge_new_modes_b{bn:03d}", "new_modes", gen.SEP.join(
                [gen.CONCEPTS, gen.RULES, NEW_MODES.replace("{modes}", gen.dump(new_modes))]))
            new_modes, merge_log = gen.apply_edits(new_modes, edits)
            for c in merge_log:
                if c["change"] == "merged":
                    alias.update({i: c["into"] for i in c["ids"]})
        n = gen.next_free(tax)
        final = {}
        for m in new_modes:
            final[m["id"]] = f"FM-{n:02d}"
            m["id"] = final[m["id"]]
            m.pop("merged_from", None)
            m["proposed_in"] = sorted({i["trace_id"] for i in m["instances"]})
            for i in m["instances"]:
                n_inst += 1
                i["instance_id"] = f"J{n_inst}"
            n += 1
        gen.rename_refs(new_modes, {p: final[alias.get(p, p)] for p in set(alias) | set(final)})
        tax += new_modes
        added += [m["id"] for m in new_modes]

        for ti, (f, t) in enumerate(zip(batch, traces)):
            d = per_trace[ti]
            for p in d["points"]:
                if p["added_mode"]:
                    p["added_mode"] = final[alias.get(p["added_mode"], p["added_mode"])]
                    p["codes"] = [p["added_mode"]]
            finish(f, t, d)
        (a.out / "taxonomy_extended.json").write_text(gen.dump({"taxonomy": tax, "added": added,
                                                               "from": str(a.taxonomy)}))
        gen.log(f"batch {bn}/{len(batches)}: {sum(len(per_trace[i]['points']) for i in range(len(traces)))} points; "
                f"{len(new_modes)} modes added ({len(tax)} now)"
                + (f"; {sum(1 for c in merge_log if c['change'] == 'merged')} merges among new modes" if merge_log else "")
                + (f"; {sum(1 for i in range(len(traces)) if per_trace[i]['errors'])} traces FAILED"
                   if any(per_trace[i]["errors"] for i in range(len(traces))) else ""))

    if not a.dry_run:
        summary = {"taxonomy": str(a.taxonomy), "traces_dir": str(a.traces), "model": a.model, "workers": a.workers,
                   "answers": str(a.answers) if a.answers else None,
                   "judge": "one pass per trace, batches in parallel; " + ("taxonomy fixed, unfitted instances NONE"
                            if a.no_new_modes else "modes for unfitted instances added after each batch"),
                   "traces": len(files), "failed": failed, "points": n_points, "rejected": n_rejected,
                   "fit_existing_mode": round(n_existing / n_points, 3) if n_points else None,
                   "modes_start": len(initial_ids), "modes_added": added, "quotes_not_verbatim": n_bad_quote,
                   "points_per_mode": dict(per_mode.most_common()),
                   "starting_modes_never_used": sorted(set(initial_ids) - set(per_mode)),
                   "possible_modes_points": {m["id"]: per_mode.get(m["id"], 0) for m in tax if m.get("gap") == "possible"}}
        from call_report import billed, report as call_report
        summary["cost"] = billed(a.out)
        (a.out / "summary.json").write_text(gen.dump(summary))
        (a.out / "call_report.txt").write_text(call_report(a.out) + "\n")
        gen.log(f"{len(files) - len(failed)} judged, {len(failed)} failed; {n_points} points, {n_rejected} rejected; "
                f"{summary['fit_existing_mode']} fitted an existing mode; {len(added)} modes added; "
                f"{n_bad_quote} quotes not verbatim")

    total = sum(s["input_tokens_est"] for s in r.stats.values())
    calls = sum(s["calls"] for s in r.stats.values())
    line = f"{calls} calls, about {total:,} input tokens"
    if a.dry_run:
        line += (" (taxonomy fixed)" if a.no_new_modes else
                 " (with the starting taxonomy, which grows during a live run; one distinctness call per batch at most)")
    if a.price_in:
        line += f"; input cost at ${a.price_in}/M: ${total / 1e6 * a.price_in:,.2f} (output not included)"
    print(line)


if __name__ == "__main__":
    main()
