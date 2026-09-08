#!/usr/bin/env python3
"""Capture the 12 pool-3 candidates on a portion of data/hover/splits/pools-1/fills.json.

Adapted from benchmarks/hover/scripts/run_eval_v3.py (2026-09-06): the split file
defaults to the pools-1 fill lists, the output lands under data/hover/traces/_incoming/,
and the task model is a flag so the same runner serves the Gemini route and the
OpenRouter route. Everything else is the original runner.

Run with the GEPA_Experiments virtual environment:
    /Users/andreicojocaru/Desktop/GEPA_Experiments/.venv/bin/python data/hover/scripts/capture_pool.py --split judging --repeats 1

Original notes follow.

Run a candidate pool on any portion of a split, producing traces and gold.

v3 of run_eval_v2: the portion is whatever the split file names, rather than a
fixed pair, because the stability study needs `judging` and `generalization`
portions that did not exist when v2 was written. Everything else -- gold kept
apart from judge inputs, resumability, the frozen converter -- is unchanged.

Serves both scored splits:

    --split generalization --repeats 1    the bench target; gold only
    --split measurement    --repeats 5    the method's input; gold + traces

Reuses hover_gepa_baseline.evaluation.evaluate_frontier_candidates, so gold
lands in `gold_do_not_pass_to_judge/` and traces land beside it in the shape the
frozen AdaMAST converter expects. Generalization does not need traces; they are
written anyway because the helper always writes them, and are simply not
converted (see --emit-corpus).

Resumable: a (candidate, task, repeat) whose trace and gold both exist is
skipped, so an interrupted run continues from the identical command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
BENCH = REPO / "benchmarks" / "hover"
DATA = REPO / "data" / "hover"
HOVER_SRC = Path("/Users/andreicojocaru/Desktop/GEPA_Experiments/src")
HOVER_DATA = Path("/Users/andreicojocaru/Desktop/GEPA_Experiments/data/hover")
CONVERTER = REPO / "legacy" / "trials" / "2026-08-07-adamast-taxonomy-generation"
DEFAULT_TASK_MODEL = "gemini/gemini-3.1-flash-lite"
T0 = time.time()


def log(msg: str, *, head: bool = False) -> None:
    el = time.time() - T0
    if head:
        print(f"\n{'=' * 78}\n[{el:7.1f}s] {msg}\n{'=' * 78}", flush=True)
    else:
        print(f"[{el:7.1f}s] {msg}", flush=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", required=True,
                   help="portion name; must exist in --split-file")
    p.add_argument("--repeats", type=int, required=True)
    p.add_argument("--pool", type=Path, default=BENCH / "pools" / "pool-3" / "candidates.json")
    p.add_argument("--split-file", type=Path,
                   default=DATA / "splits" / "pools-1" / "fills.json")
    p.add_argument("--out", type=Path, default=None, help="default: data/hover/traces/_incoming/pools-1-<split>")
    p.add_argument("--task-model", default=DEFAULT_TASK_MODEL,
                   help="gemini/<model> uses GEMINI_API_KEY directly; openrouter/google/<model> uses OPENROUTER_API_KEY")
    p.add_argument("--emit-corpus", action="store_true",
                   help="also convert traces to AdaMAST format (measurement only)")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--limit-tasks", type=int, default=None, help="smoke: use only the first N tasks")
    p.add_argument("--limit-candidates", type=int, default=None, help="smoke: use only the first N candidates")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> None:
    a = parse_args()
    out = a.out or (DATA / "traces" / "_incoming" / f"pools-1-{a.split}")
    TASK_MODEL = a.task_model
    log(f"HoVer pools-1 capture — portion={a.split}, repeats={a.repeats}, model={TASK_MODEL}", head=True)

    spec = json.loads(a.split_file.read_text())
    if a.split not in spec["portions"]:
        raise SystemExit(f"{a.split!r} is not a portion of {a.split_file}; "
                         f"available: {sorted(spec['portions'])}")
    ids = spec["portions"][a.split]
    if a.limit_tasks:
        ids = ids[: a.limit_tasks]
    others = set().union(*(set(spec["portions"][k]) for k in spec["portions"] if k != a.split))
    assert not (set(ids) & others), f"{a.split} overlaps another portion"
    log(f"  {a.split}: {len(ids)} tasks (disjoint from every other portion: asserted)")

    pool = json.loads(a.pool.read_text())["candidates"]
    # The label derives from the pool actually passed. It used to be a fixed
    # literal, which mislabelled every artifact of the pool-3 capture.
    pool_id = a.pool.parent.name
    if a.limit_candidates:
        pool = pool[: a.limit_candidates]
    n_roll = len(pool) * len(ids) * a.repeats
    log(f"  {pool_id}: {len(pool)} candidates ({sum(1 for c in pool if c['accepted'])} accepted, "
        f"{sum(1 for c in pool if not c['accepted'])} sampled rejects)")
    log(f"  -> {len(pool)} x {len(ids)} x {a.repeats} = {n_roll:,} rollouts")

    sys.path.insert(0, str(HOVER_SRC))
    import dspy
    from hover_gepa_baseline.program import HoverMultiHop
    from hover_gepa_baseline.retrieval import configure_retriever
    from hover_gepa_baseline.evaluation import evaluate_frontier_candidates

    log("configuring the BM25 retriever ...")
    configure_retriever(HOVER_DATA)
    log("  retriever ready")

    raw = out / "raw"
    states = raw / "candidate_states"
    states.mkdir(parents=True, exist_ok=True)
    # evaluate_frontier_candidates reads exactly candidate_index, state_file and
    # component_sha256 from each record; a bare components dict is not enough.
    REQUIRED = ("candidate_index", "state_file", "component_sha256")
    records = []
    for i, c in enumerate(pool):
        prog = HoverMultiHop()
        names = {n for n, _ in prog.named_predictors()}
        missing = names - set(c["components"])
        if missing:
            raise SystemExit(f"{c['candidate_id']} lacks instructions for {sorted(missing)}")
        for name, pred in prog.named_predictors():
            pred.signature = pred.signature.with_instructions(c["components"][name])
        rel = f"candidate_states/cand_{i:03d}.json"
        prog.save(str(raw / rel))
        canonical = json.dumps(c["components"], sort_keys=True).encode("utf-8")
        records.append({"candidate_index": i, "state_file": rel,
                        "component_sha256": hashlib.sha256(canonical).hexdigest(),
                        "pool_candidate_id": c["candidate_id"], "accepted": c["accepted"]})
    for r in records:
        bad = [k for k in REQUIRED if k not in r]
        if bad:
            raise SystemExit(f"record {r['candidate_index']} lacks {bad}")
    manifest = {"schema_version": 1,
                "frontier_candidate_indices": list(range(len(records))),
                "candidates": records}
    (out / "candidate_map.json").write_text(json.dumps(manifest, indent=2) + "\n")
    log(f"  wrote {len(records)} candidate state files; manifest validated")

    if a.dry_run:
        log("  dry run complete — state files written, manifest valid, no model calls.")
        return
    key = "OPENROUTER_API_KEY" if TASK_MODEL.startswith("openrouter/") else "GEMINI_API_KEY"
    if not os.environ.get(key):
        raise SystemExit(f"{key} is not set in this shell; export it and relaunch.")

    log("rebuilding examples from the frozen IDs ...")
    from datasets import load_dataset
    ds = load_dataset("hover-nlp/hover", split="train", trust_remote_code=True)
    want, by_id = set(ids), {}
    for i, row in enumerate(ds):
        facts = row.get("supporting_facts") or []
        titles = [f[0] if isinstance(f, (list, tuple)) else f.get("key") for f in facts]
        if len({t for t in titles if t}) != 3:
            continue
        sid = row.get("uid") or row.get("id") or f"train-{i}"
        if sid in want:
            by_id[sid] = dspy.Example(
                claim=row["claim"], supporting_facts=row["supporting_facts"],
                label=row.get("label"), source_index=i, source_id=sid).with_inputs("claim")
    if want - set(by_id):
        raise SystemExit(f"{len(want - set(by_id))} frozen IDs absent from HoVer")
    examples = [by_id[i] for i in ids]
    log(f"  rebuilt {len(examples)} examples")

    # 503 bursts from Gemini hit every in-flight worker at once, and the
    # evaluation helper re-raises, so one burst aborts the whole run. Three
    # aborts in 54 minutes on this run; 8 retries absorbs the burst in-process
    # instead of relying on a relaunch.
    task_lm = dspy.LM(TASK_MODEL, max_tokens=8192, cache=False, num_retries=8)
    dspy.configure(lm=task_lm)
    log(f"running {n_roll:,} rollouts, {a.workers} workers", head=True)
    log("  resumable: a (candidate, task, repeat) already on disk is skipped")
    evaluate_frontier_candidates(run_dir=raw, candidate_manifest=manifest,
                                 evaluation_set=examples, task_lm=task_lm,
                                 repeats=a.repeats, num_threads=a.workers)
    log("  rollouts complete")

    log("collecting gold outcomes", head=True)
    idx = {r["candidate_index"]: r["pool_candidate_id"] for r in records}
    outcomes: dict[str, dict[str, dict[str, float]]] = {}
    n = 0
    for f in sorted((raw / "evaluation" / "gold_do_not_pass_to_judge").rglob("*.json")):
        g = json.loads(f.read_text())
        cid = idx[int(g["candidate_index"])]
        rep = str(g["evaluation_repeat"])
        outcomes.setdefault(cid, {}).setdefault(rep, {})[str(g["task"]["source_id"])] = float(g["gold_score"])
        n += 1
    (out / "outcomes.json").write_text(json.dumps(
        {"benchmark": "hover", "pool": pool_id, "split_id": spec["split_id"],
         "task_model": TASK_MODEL, "split": a.split, "repeats": a.repeats, "candidates": len(records),
         "tasks": len(ids), "records": n, "outcomes": outcomes}, indent=2, sort_keys=True) + "\n")
    log(f"  wrote {n:,} gold records for {len(outcomes)} candidates -> {out/'outcomes.json'}")
    means = {c: sum(v.values())/len(v) for c, r in outcomes.items() for v in [next(iter(r.values()))]}
    if means:
        import statistics
        vals = sorted(means.values())
        log(f"  accuracy at repeat 0: min {vals[0]:.4f} max {vals[-1]:.4f} "
            f"mean {statistics.mean(vals):.4f} spread {vals[-1]-vals[0]:.4f}")

    if a.emit_corpus:
        log("converting traces to AdaMAST format", head=True)
        sys.path.insert(0, str(CONVERTER))
        from convert_traces import convert
        corpus = out / "corpus"
        corpus.mkdir(parents=True, exist_ok=True)
        k = 0
        for f in sorted((raw / "evaluation" / "traces").rglob("*.json")):
            t = json.loads(f.read_text())
            if t.get("status") != "ok":
                continue
            c = convert(t)
            c["metadata"].update({"split": a.split, "pool": pool_id})
            (corpus / f"{c['trace_id']}.json").write_text(json.dumps(c, indent=1))
            k += 1
        log(f"  wrote {k:,} AdaMAST traces -> {corpus}")


if __name__ == "__main__":
    main()
