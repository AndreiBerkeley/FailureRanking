#!/usr/bin/env python3
"""Duplicate HoVer's candidates, the task split the optimizer ran on, and the
candidates' traces on that split from benchmarks/hover (the v3 capture) into
data/hover. Read-only on benchmarks/. Refuses to overwrite an existing
data/hover unless --force; with --force it rebuilds everything except scripts/,
so run the other migration scripts again afterwards.

Every check is recorded in the provenance files; a failed check aborts the run.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

from hoverlib import (NEW, OLD, TODAY, jdump, jload, jsonl_write, log, migrate_capture, provenance,
                      split2_records, write_capture_readme, write_outcomes, write_outcomes_readme,
                      write_tasks, write_tasks_readme, component_sha256)

SCRIPT = "data/hover/scripts/migrate_hover_from_benchmarks.py"
RUN = OLD / "pools" / "pool-2" / "runs" / "seed0"
GEN = OLD / "traces" / "traces-3" / "generation"
CAPTURE, SPLIT, GEPA_RUN = "cap-1", "gepa-1", "gepa-1"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if NEW.exists() and any(p for p in NEW.iterdir() if p.name != "scripts"):
        if not a.force:
            sys.exit(f"{NEW} already populated; pass --force to rebuild")
        for p in NEW.iterdir():
            if p.name != "scripts":
                shutil.rmtree(p) if p.is_dir() else p.unlink()

    # ---- split gepa-1 ----
    log("split")
    s2 = jload(OLD / "splits" / "split-2" / "split.json")
    train, val = s2["portions"]["train"], s2["portions"]["validation"]
    split_ids = set(train) | set(val)
    assert len(split_ids) == len(train) + len(val) == 550
    s3 = jload(OLD / "splits" / "split-3" / "split.json")
    assert set(s3["portions"]["generation"]) == split_ids
    rec = split2_records()
    jdump({"benchmark": "hover", "split_id": SPLIT,
           "purpose": f"the task partition the optimizer run {GEPA_RUN} was given",
           "portions": {"train": list(train), "validation": list(val)},
           "sizes": {"train": len(train), "validation": len(val)},
           "seed": s2["split_seed"], "protocol": s2["split_protocol"], "stratified_on": s2.get("stratified_on"),
           "source": s2["source"],
           "order": "as frozen in split-2; the optimizer consumed the portions in this order",
           "note": "equals the 'generation' portion of benchmarks/hover/splits/split-3"},
          NEW / "splits" / SPLIT / "split.json")
    jdump(provenance(SPLIT, "task split", ["benchmarks/hover/splits/split-2/split.json"],
                     {"train": len(train), "validation": len(val)},
                     {"disjoint": True, "equals_split3_generation": True}, SCRIPT),
          NEW / "splits" / SPLIT / "provenance.json")
    (NEW / "splits" / SPLIT / "README.md").write_text(f"""# {SPLIT} — the split the optimizer ran on

Train {len(train)} and validation {len(val)} task ids, frozen before the
optimizer run `{GEPA_RUN}` and consumed by it. Copied without reordering from
`benchmarks/hover/splits/split-2` (its `train` and `validation` portions).

Every candidate in the registry was proposed and accepted or rejected on these
tasks. They are therefore forbidden for any scoring that claims to be free of
optimizer influence; they remain the right place to induce a taxonomy and to
study the candidates' own behaviour.
""")

    # ---- candidates ----
    log("candidates")
    p2 = jload(OLD / "pools" / "pool-2" / "candidates.json")
    p3 = jload(OLD / "pools" / "pool-3" / "candidates.json")
    assert p2["truncated_instruction_count"] == 0
    registry, by_alias = [], {}
    for c in p2["candidates"]:
        full = component_sha256(c["components"])
        row = {"candidate_id": "cnd-" + full[:12], "alias": c["candidate_id"], "benchmark": "hover",
               "program": "HoverMultiHop (4 components)", "components": c["components"],
               "component_sha256": full, "accepted": bool(c["accepted"]), "selection": c["selection"],
               "val_score": c.get("_val_score"),
               "origin": {"run": GEPA_RUN, "iteration_id": c["iteration_id"],
                          "parent_iteration_ids": c["parent_iteration_ids"], "minibatch_ids": c["minibatch_ids"],
                          "minibatch_before": c["minibatch_before"], "minibatch_after": c["minibatch_after"]},
               "legacy": {"pool": "pool-2", "candidate_id": c["candidate_id"], "prompt_hash": c["prompt_hash"]}}
        registry.append(row)
        by_alias[c["candidate_id"]] = row
    ids = [r["candidate_id"] for r in registry]
    assert len(set(ids)) == len(ids) == 40
    registry.sort(key=lambda r: r["candidate_id"])
    jsonl_write(registry, NEW / "candidates" / "registry.jsonl")
    jdump(provenance("candidates", "candidate registry", ["benchmarks/hover/pools/pool-2/candidates.json"],
                     {"candidates": 40, "accepted": sum(r["accepted"] for r in registry)},
                     {"ids_unique": True, "hashes_match_capture_candidate_map": True}, SCRIPT),
          NEW / "candidates" / "provenance.json")
    pool3_ids = sorted(by_alias[c["candidate_id"]]["candidate_id"] for c in p3["candidates"])
    sets_dir = NEW / "candidates" / "sets"
    p3prov = jload(OLD / "pools" / "pool-3" / "provenance.json")
    jdump({"set_id": "pool-2", "benchmark": "hover", "candidate_ids": sorted(ids), "rule": p2["selection"],
           "note": p2["note"], "legacy": "benchmarks/hover/pools/pool-2"}, sets_dir / "pool-2.json")
    jdump({"set_id": "pool-3", "benchmark": "hover", "candidate_ids": pool3_ids,
           "aliases": {by_alias[c["candidate_id"]]["candidate_id"]: c["candidate_id"] for c in p3["candidates"]},
           "rule": p3prov["produced_by"], "legacy": "benchmarks/hover/pools/pool-3"}, sets_dir / "pool-3.json")
    (sets_dir / "README.md").write_text("""# sets — named lists of candidate ids

A set is a list of ids pointing into `../registry.jsonl`, with the rule that
chose them. It never copies a candidate.

| set | size | rule |
|---|---:|---|
| `pool-2` | 40 | every candidate the optimizer run proposed: 20 accepted, 20 rejected drawn uniformly |
| `pool-3` | 12 | 8 accepted at even intervals over validation score, 4 rejected at even intervals; spans the full score range |
""")
    (NEW / "candidates" / "README.md").write_text("""# candidates — the HoVer candidate registry

One row per candidate in `registry.jsonl`. A candidate is a set of four
instruction texts for the four components of the HoVer multi-hop program.

| field | meaning |
|---|---|
| `candidate_id` | `cnd-` plus the first 12 hex of the sha256 of the components (sorted-key JSON); the identity every other file uses |
| `alias` | the human name it had in the source pool (`cand-004`) |
| `components` | the four instruction texts, keyed by component name |
| `accepted` | whether the optimizer accepted it onto its frontier |
| `val_score` | the optimizer's validation score on `splits/gepa-1` |
| `origin` | which optimizer run and iteration proposed it, and its parents |

`sets/` holds named lists of ids. `runs/` holds the optimizer run that produced
the candidates, one directory per run.
""")
    run_dir = NEW / "candidates" / "runs" / GEPA_RUN
    (run_dir / "logs").mkdir(parents=True)
    shutil.copyfile(RUN / "run_config.json", run_dir / "run_config.json")
    shutil.copyfile(RUN / "gepa_result.json", run_dir / "result.json")
    shutil.copyfile(RUN / "usage.json", run_dir / "usage.json")
    shutil.copytree(RUN / "usage_launches", run_dir / "usage_launches")
    g = RUN / "gepa_run"
    for name in ("run_log.txt", "run_log_stderr.txt", "run_log.json"):
        shutil.copyfile(g / name, run_dir / "logs" / name)
    for name in ("candidates.json", "gepa_state.json", "gepa_state.bin", "candidate_tree.html"):
        shutil.copyfile(g / name, run_dir / name)
    shutil.copytree(g / "pareto", run_dir / "pareto")
    shutil.copytree(g / "generated_best_outputs_valset", run_dir / "generated_best_outputs_valset")
    subprocess.run(["tar", "-czf", str(run_dir / "iterations.tar.gz"), "-C", str(g), "iterations"], check=True)
    p2prov = jload(OLD / "pools" / "pool-2" / "provenance.json")
    jdump(provenance(GEPA_RUN, "optimizer run", ["benchmarks/hover/pools/pool-2/runs/seed0"],
                     {"candidates_proposed": 40}, {"copied_whole": True}, SCRIPT,
                     {"optimizer": p2prov["produced_by"], "split": SPLIT}), run_dir / "provenance.json")
    (run_dir / "README.md").write_text(f"""# {GEPA_RUN} — the optimizer run that produced the candidates

GEPA, seed 0, on split `{SPLIT}`, task model `gemini/gemini-3.1-flash-lite`,
reflection model `gemini/gemini-3.1-pro-preview`. Run 2026-08-29 as
`benchmarks/hover/pools/pool-2/runs/seed0`; copied whole here on {TODAY}.

| file | what it is |
|---|---|
| `run_config.json` | every setting the run was launched with |
| `result.json` | the optimizer's own result object: frontier, parents, per-instance bests |
| `usage.json`, `usage_launches/` | cost and call counts |
| `candidates.json`, `gepa_state.json`, `gepa_state.bin` | the optimizer's candidate list and resumable state |
| `pareto/`, `generated_best_outputs_valset/`, `candidate_tree.html` | its frontier, best outputs, and lineage view |
| `logs/` | stdout, stderr, structured log |
| `iterations.tar.gz` | the full per-iteration tree, archived whole |

The candidates harvested from this run are the registry in `../../registry.jsonl`.
""")

    # ---- cap-1 ----
    log("traces")
    r = migrate_capture(src=GEN, capture_id=CAPTURE, split_id=SPLIT, portions=["train", "validation"],
                        allowed_tasks=split_ids, rec=rec, by_alias=by_alias, expected_tasks=550,
                        captured_on="2026-09-01",
                        derives_from=["benchmarks/hover/traces/traces-3/generation", "benchmarks/hover/pools/pool-3",
                                      "benchmarks/hover/splits/split-3"],
                        script=SCRIPT, description="pool-3 on the optimizer's split, one run each")
    write_capture_readme(CAPTURE, "pool-3 on the optimizer's split, one run each", f"""12 candidates (set `pool-3`) × 550 tasks (split `{SPLIT}`, train and validation
portions) × 1 repeat = 6,600 traces. Solver `gemini/gemini-3.1-flash-lite`.
Captured 2026-09-01 as `benchmarks/hover/traces/traces-3/generation`; duplicated
here on {TODAY} with every identity re-keyed to the registries and verified by hash.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what was expected, what is present, audit results |
| `index.jsonl` | one row per trace: ids, status, call count, cost, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces, one candidate per file, one trace per line |
| `program_states/<candidate_id>.json` | the DSPy program state that ran, as saved by the runner |

A body holds the full run record (`input`, `prediction`, every `lm_call`) and,
under `judge_view`, the outcome-blind message list exactly as it was emitted for
judging. No gold appears anywhere in this directory; scores are in
`../../outcomes/{CAPTURE}.jsonl` and the gold itself in `../../tasks/tasks.jsonl`.

These tasks are the ones the optimizer saw. Under the project's rules they are
forbidden for any scoring that claims to be free of optimizer influence. The
two taxonomies in `../../taxonomies/` were induced from traces in this capture.
""")
    portions_of = {t: [f"{SPLIT}/train"] for t in train}
    portions_of.update({t: [f"{SPLIT}/validation"] for t in val})
    n = write_tasks(r["claims"], r["gold_by_task"], rec, portions_of, SCRIPT,
                    ["benchmarks/hover/splits/split-2/split.json", "benchmarks/hover/traces/traces-3/generation"])
    write_tasks_readme()
    write_outcomes(CAPTURE, r["outcome_rows"], [f"data/hover/traces/{CAPTURE}", "data/hover/tasks/tasks.jsonl"], SCRIPT)
    write_outcomes_readme()
    log(f"done: traces {len(r['index_rows'])} tasks {n} candidates {len(registry)} statuses {dict(r['status_counter'])}")


if __name__ == "__main__":
    main()
