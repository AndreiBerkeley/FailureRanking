#!/usr/bin/env python3
"""Export the test traces of a setup: traces of every task generation did not use.

    python generation/export_test.py --benchmark swebench                                    # single-model
    python generation/export_test.py --benchmark tau2bench --setup multi-model --models-per-task 3 --all-runs

Reads data/<benchmark>/<setup>/manifest.json for the generation tasks (and, single-model, its model). The test tasks
are all the others (for bfcl: all other scenarios, one variant each, drawn at random).
  single-model  the setup's model; where it has several runs of a task, one drawn at random
  multi-model   L models drawn at random per task (--models-per-task), or every model (--all-models); one run each
                drawn at random, or every run of each (--all-runs); all test tasks, or N drawn at random (--tasks N)

Writes data/<benchmark>/<setup>/test/<trace_id>.json (judge view only: trace_id, task_id, messages) and adds a "test"
section to the manifest with the task, model and run of every trace.
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
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--setup", default="single-model", choices=["single-model", "multi-model"])
    ap.add_argument("--models-per-task", type=int, default=3, help="L, multi-model only")
    ap.add_argument("--all-runs", action="store_true", help="multi-model: every run of each drawn model, not one")
    ap.add_argument("--all-models", action="store_true", help="multi-model: every model on every test task")
    ap.add_argument("--tasks", type=int, default=None, help="multi-model: draw this many test tasks at random")
    a = ap.parse_args()
    if a.setup == "multi-model":
        return multi(a)

    setup = DATA / a.benchmark / "single-model"
    man = json.loads((setup / "manifest.json").read_text())
    model = man["model"]
    used = {x["task_id"] for x in man["traces"]}

    runs = collections.defaultdict(list)  # task -> this model's records
    for line in gzip.open(DATA / a.benchmark / "traces" / f"{model}.jsonl.gz", "rt"):
        r = json.loads(line)
        if OUTCOME_KEYS & set(r["judge_view"]):
            raise SystemExit(f"trace {r['trace_id']} carries outcome keys; refusing to export")
        runs[r["task_id"]].append(r)

    rng = random.Random(a.seed)
    if a.benchmark == "bfcl":  # a scenario's variants share state and requests: no variant of a used scenario
        scen = collections.defaultdict(list)
        for t, rs in runs.items():
            scen[rs[0]["metadata"]["scenario"]].append(t)
        used_scen = {runs[t][0]["metadata"]["scenario"] for t in used}
        tasks = [rng.choice(sorted(scen[s])) for s in sorted(scen) if s not in used_scen]
    else:
        tasks = [t for t in sorted(runs) if t not in used]

    out = setup / "test"
    if out.exists():
        raise SystemExit(f"{out} exists; move it to the Trash first")
    out.mkdir()
    listing = []
    for t in tasks:
        r = rng.choice(sorted(runs[t], key=lambda x: x["repeat"]))
        (out / f"{r['trace_id']}.json").write_text(
            json.dumps({"trace_id": r["trace_id"], "task_id": t, "messages": r["judge_view"]["messages"]}))
        listing.append({"task_id": t, "repeat": r["repeat"], "trace_id": r["trace_id"]})
    man["test"] = {"seed": a.seed, "model": model, "tasks": len(tasks),
                   "unit": "scenario, one variant each" if a.benchmark == "bfcl" else "task",
                   "rule": "every task generation did not use; one run per task",
                   "traces": listing}
    (setup / "manifest.json").write_text(json.dumps(man, indent=1))
    print(f"{a.benchmark}: {len(tasks)} test traces of {model} -> {out}")


def multi(a):
    setup = DATA / a.benchmark / "multi-model"
    man = json.loads((setup / "manifest.json").read_text())
    used = {x["task_id"] for x in man["traces"]}
    runs = collections.defaultdict(list)  # (task, model) -> records
    for f in sorted((DATA / a.benchmark / "traces").glob("*.jsonl.gz")):
        for line in gzip.open(f, "rt"):
            r = json.loads(line)
            if OUTCOME_KEYS & set(r["judge_view"]):
                raise SystemExit(f"trace {r['trace_id']} carries outcome keys; refusing to export")
            runs[r["task_id"], r["candidate_id"]].append(r)
    models = sorted({m for _, m in runs})
    all_tasks = sorted({t for t, _ in runs})

    rng = random.Random(a.seed)
    if a.benchmark == "bfcl":  # no variant of a used scenario; one variant per other scenario
        scen = collections.defaultdict(list)
        for t in all_tasks:
            scen[runs[t, models[0]][0]["metadata"]["scenario"]].append(t)
        used_scen = {runs[t, models[0]][0]["metadata"]["scenario"] for t in used}
        tasks = [rng.choice(sorted(scen[s])) for s in sorted(scen) if s not in used_scen]
    else:
        tasks = [t for t in all_tasks if t not in used]
    if a.tasks:
        tasks = sorted(rng.sample(tasks, a.tasks))

    out = setup / "test"
    if out.exists():
        raise SystemExit(f"{out} exists; move it to the Trash first")
    out.mkdir()
    listing = []
    for t in tasks:
        for m in (models if a.all_models else sorted(rng.sample(models, a.models_per_task))):
            rs = sorted(runs[t, m], key=lambda x: x["repeat"])
            for r in (rs if a.all_runs else [rng.choice(rs)]):
                (out / f"{r['trace_id']}.json").write_text(
                    json.dumps({"trace_id": r["trace_id"], "task_id": t, "messages": r["judge_view"]["messages"]}))
                listing.append({"task_id": t, "model": m, "repeat": r["repeat"], "trace_id": r["trace_id"]})
    per_task = f"all {len(models)} models" if a.all_models else f"{a.models_per_task} models drawn"
    man["test"] = {"seed": a.seed, "models_per_task": len(models) if a.all_models else a.models_per_task,
                   "all_runs": a.all_runs, "tasks": len(tasks),
                   "unit": "scenario, one variant each" if a.benchmark == "bfcl" else "task",
                   "rule": (f"{a.tasks} tasks drawn at random from those" if a.tasks else "every task")
                           + f" generation did not use; {per_task} per task; "
                           + ("every run of each" if a.all_runs else "one run of each, drawn at random"),
                   "traces": listing}
    (setup / "manifest.json").write_text(json.dumps(man, indent=1))
    print(f"{a.benchmark}/multi-model: {len(tasks)} test tasks, {len(listing)} traces -> {out}")


if __name__ == "__main__":
    main()
