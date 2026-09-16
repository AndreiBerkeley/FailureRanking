#!/usr/bin/env python3
"""Run the two-reader/decider judge over a trace set.

    python3 -m new_pipeline.pointjudge.run --taxonomy <tax.json> --traces <dir> --out <dir>

One result per trace, which is one (task, candidate) pair. The scoring surface is
still a code count map, so anything that reads the panel judge's output reads
this one, but the count is now derived from located failure points:

    {"RL_03": 2, "RL_08": 1}

and every point behind it carries its step, its evidence span and its modes.

FIVE CALLS PER TRACE
    reader A   points (with the taxonomy in view), then modes over that list
    reader B   points (with no taxonomy), then modes over that list
    decider    validates, merges on the evidence, settles spans, assigns modes

FAILURE IS NOT SILENCE
A trace whose calls did not all succeed is recorded with status "failed" and an
empty code map that no aggregation counts. "Judged, found nothing" and "we could
not judge this" must never collapse into the same empty dict.

GOLD
Stripped at the boundary by new_pipeline/goldfree.py, and the removed keys are
recorded per trace so the outcome-free claim is auditable.

Design and open questions: judges/proposed/two-reader-decider.md
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from new_pipeline import goldfree                              # noqa: E402
from new_pipeline.llm import llm_call, log                     # noqa: E402
from new_pipeline.pointjudge import judge, prompts             # noqa: E402


def _base_result(path: Path, clean, removed):
    md = clean.get("metadata") or {}
    return {"trace_id": clean.get("trace_id") or path.stem,
            "task_id": md.get("task_source_id"),
            "candidate_index": md.get("candidate_index"),
            "status": "failed", "codes": {}, "error": None,
            "gold_stripped": removed}


def judge_one(path: Path, tax_text, valid_ids, calls, cfg) -> dict:
    """The five calls, in order, for one trace."""
    raw = json.loads(path.read_text())
    clean, removed = goldfree.strip(raw)
    res = _base_result(path, clean, removed)

    trace_text, turns = judge.render_turns(clean, cfg["agents"])
    if not turns:
        res["error"] = "trace renders with no agent turns"
        return res
    expected = [{"turn": t["turn"], "agent": t["agent"]} for t in turns]
    turn_agents = {t["turn"]: t["agent"] for t in expected}

    rcall, rmodel = calls["reader"]
    dcall, dmodel = calls["decider"]

    # A and B are independent chains: each reads the trace, then assigns modes to its own frozen
    # list, and only the decider needs both. Run the two chains concurrently, so one trace costs
    # three call-latencies (read, assign, decide) rather than five. The readers stay independent
    # -- they never see each other's work -- so this changes when calls are issued, nothing else.
    def chain(with_tax):
        got = judge.read_points(rcall, rmodel, trace_text, expected, tax_text if with_tax else None)
        if got is None:
            return None, None, "failed to report points"
        points, checked = got
        modes = judge.assign_modes(rcall, rmodel, points, tax_text, valid_ids)
        if modes is None:
            return None, None, "failed to assign modes"
        return (points, checked), modes, None

    # --readers a: only the taxonomy-holding reader runs, and its modes stand as the verdict.
    # There is no second opinion to reconcile, so the decider is skipped too. This buys a rate
    # for a code on the same footing as a full pass at a fifth of the calls, at the cost of the
    # blind-reader corroboration share -- so it measures prevalence, not reliability.
    if cfg.get("readers") == "a":
        (a_got, a_modes, a_err) = chain(True)
        if a_err:
            res["error"] = f"reader A {a_err}"
            return res
        a_points, a_checked = a_got
        # Shape these exactly like decider output so every downstream reader --
        # counts_from_points, the summary, the analysis scripts -- works unchanged.
        # from_a/from_b record provenance honestly: reader A found all of them, and
        # there was no reader B.
        points = []
        for i, (pt, m) in enumerate(zip(a_points, a_modes or [])):
            q = dict(pt)
            # assign_modes returns {"code": id, "fitness": int}; every downstream reader
            # wants plain ids, which is normally the decider's doing. Apply the same
            # FIT_GOOD threshold assign_modes uses to set none_fits, so `codes` and
            # `none_fits` cannot disagree. The scored fitnesses are kept under "modes".
            q["modes"] = m["codes"]
            q["codes"] = [c["code"] for c in m["codes"]
                          if c["fitness"] >= judge.FIT_GOOD]
            q["none_fits"] = m["none_fits"]
            q["missing"] = m["missing"]
            q["from_a"], q["from_b"] = i, None
            points.append(q)
        res.update({
            "status": "judged",
            "codes": judge.counts_from_points(points),
            "points": points,
            "rejected": [],
            "readers": {"a": {"points": a_points, "modes": a_modes, "checked": a_checked}},
            "single_reader": "a",
            "agreement": {"points": len(points), "found_by_both": 0, "only_a": len(points),
                          "only_b": 0, "decider_only": 0, "rejected": 0,
                          "uncovered": sum(1 for q in points if q["none_fits"])},
            "mode_agreement": {"shared_points": 0, "same_modes": 0, "different_modes": 0},
            "turns": expected,
        })
        return res

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="reader") as ex:
        fa = ex.submit(chain, True)
        fb = ex.submit(chain, False)
        (a_got, a_modes, a_err) = fa.result()
        (b_got, b_modes, b_err) = fb.result()
    if a_err:
        res["error"] = f"reader A {a_err}"
        return res
    if b_err:
        res["error"] = f"reader B {b_err}"
        return res
    a_points, a_checked = a_got
    b_points, b_checked = b_got

    decision = judge.decide(dcall, dmodel, trace_text,
                            judge.with_modes(a_points, a_modes),
                            judge.with_modes(b_points, b_modes),
                            tax_text, valid_ids, turn_agents)
    if decision is None:
        res["error"] = "decider failed"
        return res

    res.update({
        "status": "judged",
        "codes": judge.counts_from_points(decision["points"]),
        "points": decision["points"],
        "rejected": decision["rejected"],
        "readers": {
            "a": {"points": a_points, "modes": a_modes, "checked": a_checked},
            "b": {"points": b_points, "modes": b_modes, "checked": b_checked},
        },
        "agreement": judge.agreement(decision),
        "mode_agreement": judge.mode_agreement(decision, a_modes, b_modes),
        "coverage": judge.coverage(a_modes, b_modes, decision),
        "turns": expected,
    })
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--traces", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="gemini-3.6-flash",
                    help="a Gemini id, or openrouter/<vendor>/<model>")
    ap.add_argument("--reader-model", default=None, help="overrides --model for A and B")
    ap.add_argument("--decider-model", default=None,
                    help="overrides --model for the decider, which reads the full "
                         "trace plus both point lists and is the call worth spending on")
    ap.add_argument("--structure", type=Path, default=None,
                    help="benchmark structure json; names the agents in turn headers")
    ap.add_argument("--thinking", choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"], default=None)
    ap.add_argument("--max-output", type=int, default=65536)
    ap.add_argument("--timeout", type=int, default=300,
                    help="per socket operation; a stalled read fails and retries "
                         "rather than parking a worker")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tasks", type=Path, default=None,
                    help="split json naming the task ids to judge")
    ap.add_argument("--tasks-key", action="append", default=None, metavar="DOTTED.PATH")
    ap.add_argument("--limit", type=int, default=None, help="first N traces, for a sample")
    ap.add_argument("--no-retry-failed", action="store_true")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--readers", choices=["both", "a"], default="both",
                    help="'a' runs only the taxonomy-holding reader and skips the decider "
                         "(1/5 the calls; gives prevalence, not agreement)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the exact prompts and spend nothing; writes no files")
    a = ap.parse_args()

    taxonomy = json.loads(a.taxonomy.read_text())
    if "codes" not in taxonomy:
        raise SystemExit(f"{a.taxonomy} has no flat 'codes' list")
    tax_text = judge.render_taxonomy(taxonomy)
    valid_ids = {c["id"] for c in taxonomy["codes"]}

    files = sorted(p for p in a.traces.glob("*.json")
                   if p.name not in ("outcomes.json", "pool_manifest.json"))
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
                    raise SystemExit(f"--tasks-key {key!r} is not a list")
                want |= set(node)
        elif isinstance(doc, list):
            want = set(doc)
        else:
            raise SystemExit(f"{a.tasks} is an object; name the ids with --tasks-key")
        kept, seen = [], set()
        for f in files:
            tid = (json.loads(f.read_text()).get("metadata") or {}).get("task_source_id")
            if tid in want:
                kept.append(f); seen.add(tid)
        missing = want - seen
        if missing:
            raise SystemExit(f"--tasks named {len(missing)} task(s) with no trace in "
                             f"{a.traces}, e.g. {sorted(missing)[:3]}")
        log(f"  --tasks: {len(want)} tasks -> {len(kept)} of {len(files)} traces")
        files = kept
    if a.limit:
        files = files[:a.limit]
    if not files:
        raise SystemExit(f"no traces in {a.traces}")

    agents = None
    if a.structure:
        agents = list(json.loads(a.structure.read_text())["discovered_agents"]["agents"])
    cfg = {"agents": agents, "readers": a.readers}

    if a.dry_run:
        clean, removed = goldfree.strip(json.loads(files[0].read_text()))
        tt, turns = judge.render_turns(clean, agents)
        per = 2 if a.readers == "a" else 5
        print(f"traces: {len(files)}   codes: {len(valid_ids)}   turns in first trace: "
              f"{len(turns)}   calls per trace: {per}   total: {len(files) * per}")
        print(f"reader: {a.reader_model or a.model}   decider: "
              f"{'(none: --readers a)' if a.readers == 'a' else a.decider_model or a.model}"
              f"   thinking: {a.thinking}")
        print(f"gold stripped from this trace: {removed}\n")
        shown = [
            ("READER A, PASS 1 (with the taxonomy)", prompts.READER_A_POINTS.format(
                layout=prompts.TURN_LAYOUT, point_rule=prompts.POINT_RULE,
                every_turn=prompts.EVERY_TURN, taxonomy=tax_text, trace=tt)),
            ("READER B, PASS 1 (no taxonomy)", prompts.READER_B_POINTS.format(
                layout=prompts.TURN_LAYOUT, point_rule=prompts.POINT_RULE,
                every_turn=prompts.EVERY_TURN, trace=tt)),
            ("PASS 2, EITHER READER", prompts.ASSIGN_MODES.format(
                taxonomy=tax_text,
                points="0. turn 2 · agent create_query_hop2\n"
                       "   problem : <one sentence>\n   evidence: <the span>")),
            ("THE DECIDER", prompts.DECIDE.format(
                layout=prompts.TURN_LAYOUT, point_rule=prompts.POINT_RULE,
                taxonomy=tax_text, trace=tt,
                a_points="<reader A's numbered points, with its modes>",
                b_points="<reader B's numbered points, with its modes>")),
        ]
        if a.readers == "a":
            shown = [x for x in shown if "READER B" not in x[0] and "DECIDER" not in x[0]]
        for title, body in shown:
            print("=" * 78 + f"\n{title}\n" + "=" * 78)
            print(body)
        print("\ndry run: nothing spent")
        return

    tdir = a.out / "traces"
    tdir.mkdir(parents=True, exist_ok=True)

    def attempts_of(f):
        prev = tdir / f"{f.stem}.json"
        if prev.exists():
            try:
                return int(json.loads(prev.read_text()).get("attempts", 1))
            except Exception:                                  # noqa: BLE001
                pass
        return 0

    def wants_work(f):
        out = tdir / f"{f.stem}.json"
        if not out.exists():
            return True
        try:
            r = json.loads(out.read_text())
        except Exception:                                      # noqa: BLE001
            return True
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
    log(f"pointjudge: {len(files)} traces, {len(pending)} to do, "
        f"{len(files) - len(pending)} already done")
    shape = ("1 reader x 2 passes, no decider" if a.readers == "a"
             else "2 readers x 2 passes + decider")
    log(f"  {len(valid_ids)} codes | {shape} | {a.workers} workers")

    kw = dict(temperature=a.temperature, retries=5, max_output=a.max_output,
              thinking=a.thinking, timeout=a.timeout)
    rcall, rmodel = llm_call(a.reader_model or a.model, **kw)
    dcall, dmodel = llm_call(a.decider_model or a.model, **kw)
    calls = {"reader": (rcall, rmodel), "decider": (dcall, dmodel)}
    log(f"  reader {rmodel} | decider {dmodel} | thinking {a.thinking}")
    t0, done = time.time(), 0

    def work(f):
        try:
            r = judge_one(f, tax_text, valid_ids, calls, cfg)
        except Exception as exc:                               # noqa: BLE001
            log(f"  [!] {f.stem} failed with {type(exc).__name__}: {str(exc)[:120]}; "
                "recorded failed, will be retried")
            raw = json.loads(f.read_text()); clean, removed = goldfree.strip(raw)
            r = _base_result(f, clean, removed)
            r["error"] = f"exception: {type(exc).__name__}: {str(exc)[:200]}"
        r["attempts"] = attempts_of(f) + 1
        return f, r

    ex = ThreadPoolExecutor(max_workers=a.workers)
    futs = [ex.submit(work, f) for f in pending]
    try:
        for fut in as_completed(futs):
            f, res = fut.result()
            (tdir / f"{f.stem}.json").write_text(json.dumps(res, indent=2))
            done += 1
            if done % 10 == 0 or done == len(pending):
                log(f"  {done}/{len(pending)}  ({time.time()-t0:.0f}s)")
    except BaseException:
        log("  [!] writer loop interrupted; cancelling queued traces")
        ex.shutdown(wait=False, cancel_futures=True)
        raise
    ex.shutdown(wait=True)

    # ---- summary ---------------------------------------------------------
    results = [json.loads(p.read_text()) for p in sorted(tdir.glob("*.json"))]
    judged = [r for r in results if r["status"] == "judged"]
    failed = [r for r in results if r["status"] != "judged"]
    fired, agree, magree = Counter(), Counter(), Counter()
    per_cand = defaultdict(lambda: {"traces": 0, "codes": Counter(),
                                    "by_agent": defaultdict(Counter)})
    uncovered = []
    for r in judged:
        c = r.get("candidate_index")
        per_cand[c]["traces"] += 1
        for code, n in r["codes"].items():
            fired[code] += 1
            per_cand[c]["codes"][code] += n
        # by_agent counts distinct STEPS, the same rule as `codes`. Counting points
        # instead would make a turn carrying three points of one code read as 3
        # here and 1 there, and the two numbers would stop being comparable.
        steps = set()
        for p in r["points"]:
            for code in p["codes"]:
                steps.add((p.get("agent") or "?", p["turn"], code))
            if p["none_fits"] and p.get("missing"):
                uncovered.append(p["missing"])
        for agent, _turn, code in steps:
            per_cand[c]["by_agent"][agent][code] += 1
        agree.update(r.get("agreement") or {})
        magree.update(r.get("mode_agreement") or {})

    summary = {
        "taxonomy": str(a.taxonomy), "traces": str(a.traces),
        "judge": ("pointjudge: taxonomy reader only, two passes, no decider"
                  if a.readers == "a" else
                  "pointjudge: two readers, two passes each, one decider"),
        "settings": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items()},
        "counts": {"total": len(results), "judged": len(judged), "failed": len(failed)},
        "failed_by_candidate": {str(k): v for k, v in
                                Counter(r.get("candidate_index") for r in failed).items()},
        "traces_firing_each_code": dict(fired.most_common()),
        "codes_never_fired": sorted(valid_ids - set(fired)),
        "reader_agreement": dict(agree),
        "mode_agreement": dict(magree),
        "uncovered_points": len(uncovered),
        "uncovered_described": uncovered[:50],
        "minutes": round((time.time() - t0) / 60, 1),
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2))
    (a.out / "profiles.json").write_text(json.dumps(
        {str(k): {"traces": v["traces"], "codes": dict(v["codes"]),
                  "by_agent": {ag: dict(cc) for ag, cc in v["by_agent"].items()}}
         for k, v in sorted(per_cand.items(), key=lambda x: (x[0] is None, x[0]))}, indent=2))

    log("=" * 60)
    log(f"judged {len(judged)}/{len(results)}  failed {len(failed)}  {summary['minutes']} min")
    if failed:
        log(f"  FAILED BY CANDIDATE: {summary['failed_by_candidate']} "
            "-- uneven failure across candidates biases the ranking")
    a_ = summary["reader_agreement"]
    if a_.get("points"):
        log(f"  points {a_['points']}: both readers {a_.get('found_by_both', 0)}, "
            f"A only {a_.get('only_a', 0)}, B only {a_.get('only_b', 0)}, "
            f"decider only {a_.get('decider_only', 0)}, rejected {a_.get('rejected', 0)}")
    m_ = summary["mode_agreement"]
    if m_.get("shared_points"):
        log(f"  modes on shared points: {m_.get('same_modes', 0)} same, "
            f"{m_.get('different_modes', 0)} different of {m_['shared_points']}")
    log(f"  points nothing fits (never scored): {summary['uncovered_points']}")
    log(f"  codes that never fired: {len(summary['codes_never_fired'])} of {len(valid_ids)}")
    log(f"  -> {a.out}/summary.json, profiles.json, traces/")


if __name__ == "__main__":
    main()
