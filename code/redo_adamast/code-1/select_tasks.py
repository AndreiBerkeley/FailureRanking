#!/usr/bin/env python3
"""Pick the generation tasks of one benchmark at random and export their traces for two setups.

    python generation/select_tasks.py --benchmark swebench --initial 20 --seg1 5 --final 5 --models-per-task 3

Tasks are drawn at random from data/<benchmark>/traces/ (for bfcl: scenarios, one variant each), then
cut in order into initial generation, segment 1 and the final validation. Both setups use the same tasks:
  single-model/  one model, drawn once, its trace of every task
  multi-model/   L models drawn per task, all L traces of it
Where a model has several runs of a task, one is drawn at random.

Writes data/<benchmark>/<setup>/
  sample/<task no>_<trace_id>.json       initial + segment 1 tasks; run.py gives the last R*M files to segment 1
  validation/<task no>_<trace_id>.json   final validation tasks
  manifest.json                          seed, tasks per stage, model of every trace, run.py settings
Files hold the judge view only (trace_id, task_id, messages): no model, no outcome.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
OUTCOME_KEYS = {"score", "resolved", "outcome", "reward", "gold", "passed"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--initial", type=int, required=True, help="tasks for initial generation")
    ap.add_argument("--seg1", type=int, default=5, help="tasks for segment 1 (R*M in tasks)")
    ap.add_argument("--final", type=int, default=5, help="tasks for the final validation (F*M in tasks)")
    ap.add_argument("--models-per-task", type=int, default=3, help="L, for multi-model/")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--split", default=None, help="draw only tasks whose trace metadata has this split (e.g. test)")
    a = ap.parse_args()
    if a.seg1 != a.final:
        raise SystemExit("run.py uses one M for segment 1 and the final validation; keep --seg1 == --final")

    src = DATA / a.benchmark
    runs = collections.defaultdict(list)  # (task, model) -> records
    for f in sorted((src / "traces").glob("*.jsonl.gz")):
        for line in gzip.open(f, "rt"):
            r = json.loads(line)
            bad = OUTCOME_KEYS & set(r["judge_view"])
            if bad:
                raise SystemExit(f"trace {r['trace_id']} carries outcome keys {bad}; refusing to export")
            if a.split and r.get("metadata", {}).get("split") != a.split:
                continue
            runs[r["task_id"], r["candidate_id"]].append(r)
    models = sorted({m for _, m in runs})
    tasks = sorted({t for t, _ in runs})

    rng = random.Random(a.seed)
    n = a.initial + a.seg1 + a.final
    if a.benchmark == "bfcl":  # a scenario's variants share state and requests: draw scenarios, one variant each
        scen = collections.defaultdict(list)
        for t in tasks:
            scen[runs[t, models[0]][0]["metadata"]["scenario"]].append(t)
        picked = [rng.choice(sorted(scen[s])) for s in rng.sample(sorted(scen), n)]
    else:
        picked = rng.sample(tasks, n)
    stage = ["initial"] * a.initial + ["seg1"] * a.seg1 + ["final"] * a.final

    single = rng.choice(models)
    chosen = {"single-model": {t: [single] for t in picked}}
    if len(models) >= a.models_per_task:  # a one-model corpus gets only single-model/
        chosen["multi-model"] = {t: sorted(rng.sample(models, a.models_per_task)) for t in picked}

    for setup, by_task in chosen.items():
        out = src / setup
        if out.exists():
            raise SystemExit(f"{out} exists; move it to the Trash first")
        (out / "sample").mkdir(parents=True)
        (out / "validation").mkdir()
        listing = []
        for i, (t, st) in enumerate(zip(picked, stage)):
            for m in by_task[t]:
                r = rng.choice(sorted(runs[t, m], key=lambda x: x["repeat"]))
                keep = {"trace_id": r["trace_id"], "task_id": t, "messages": r["judge_view"]["messages"]}
                d = "validation" if st == "final" else "sample"
                (out / d / f"{i:02d}_{r['trace_id']}.json").write_text(json.dumps(keep))
                listing.append({"task_no": i, "stage": st, "task_id": t, "model": m, "repeat": r["repeat"],
                                "trace_id": r["trace_id"]})
        L = len(next(iter(by_task.values())))
        manifest = {
            "benchmark": a.benchmark, "setup": setup, "seed": a.seed, "source": str(src / "traces"),
            **({"split": a.split} if a.split else {}),
            "tasks": {"initial": a.initial, "seg1": a.seg1, "final": a.final, "pool": len(tasks)},
            "unit": "scenario, one variant each" if a.benchmark == "bfcl" else "task",
            "models_per_task": L, "models_pool": len(models),
            **({"model": single} if setup == "single-model" else {}),
            "run_py": {"--rounds": 1, "--final-rounds": 1, "--traces-per-round": a.seg1 * L,
                       "note": f"--traces-per-round M = {a.seg1} tasks x {L} traces; F*M = {a.final * L} validation traces"},
            "traces": listing,
            "note": "Judge view only. Model and outcome are not in the trace files.",
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
        print(f"{a.benchmark}/{setup}: {n} tasks ({a.initial}/{a.seg1}/{a.final}), L = {L}, "
              f"{sum(1 for x in listing if x['stage'] != 'final')} sample + "
              f"{sum(1 for x in listing if x['stage'] == 'final')} validation traces"
              + (f", model {single}" if setup == "single-model" else ""))


if __name__ == "__main__":
    main()
