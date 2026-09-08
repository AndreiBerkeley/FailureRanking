#!/usr/bin/env python3
"""Regenerate every number reported in this package.

Reads only files shipped inside the package:

    ../setup/judge_mapping.json   the judge's failure findings (pipeline input)
    ../dataset/outcomes.jsonl     evaluator scores (validation targets only)
    ../dataset/splits.json        which tasks are evidence, which are held out

Produces results.json and RESULTS.md.

    python run_all.py

Sections produced
-----------------
1. the five reference baselines
2. the full module grid over every registered option
3. the best configuration overall and per target
4. the best configuration containing each individual module
5. a cross-check that two baselines match their module equivalents exactly
"""

from __future__ import annotations

import itertools
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "pipeline"))

from core import bench  # noqa: E402
from core.baselines import score_candidates as baseline_scores  # noqa: E402
from core.grid import Configuration, run_configuration  # noqa: E402
from core.mapping import load_mapping, mapping_to_dataset  # noqa: E402
from core.run import build_registry  # noqa: E402

MAPPING = HERE.parent / "setup" / "judge_mapping.json"
OUTCOMES = HERE.parent / "dataset" / "outcomes.jsonl"
SPLITS = HERE.parent / "dataset" / "splits.json"


def load_targets() -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Build the two validation targets and the training outcomes.

    cross_seed      mean evaluator score over repeats 1-4 on the evidence tasks
    generalization  mean evaluator score on the 250 held-out tasks (repeat 0)
    training        repeat-0 evidence-task scores, for gold feedback modules
    """

    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    evidence = set(splits["evidence_tasks"])
    heldout = set(splits["heldout_tasks"])

    cross: dict[str, list[float]] = {}
    gen: dict[str, list[float]] = {}
    training: dict[str, dict[str, float]] = {}
    for line in OUTCOMES.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        candidate = str(row["candidate"])
        task, repeat, score = row["task_id"], int(row["repeat"]), float(row["score"])
        if task in evidence and repeat > 0:
            cross.setdefault(candidate, []).append(score)
        if task in heldout and repeat == 0:
            gen.setdefault(candidate, []).append(score)
        if task in evidence and repeat == 0:
            training.setdefault(candidate, {})[task] = score
    targets = {
        "cross_seed": {c: statistics.mean(v) for c, v in cross.items()},
        "generalization": {c: statistics.mean(v) for c, v in gen.items()},
    }
    return targets, training


def pair_counts(scores: dict[str, float], target: dict[str, float]) -> dict[str, int]:
    """Concordant, discordant and tied candidate pairs, for interpreting tau."""

    candidates = sorted(scores)
    counts = {"concordant": 0, "discordant": 0, "tied": 0}
    for i, a in enumerate(candidates):
        for b in candidates[i + 1 :]:
            ds, dt = scores[a] - scores[b], target[a] - target[b]
            if ds == 0 or dt == 0:
                counts["tied"] += 1
            elif (ds > 0) == (dt > 0):
                counts["concordant"] += 1
            else:
                counts["discordant"] += 1
    return counts


def evaluate(scores: dict[str, float], targets) -> dict[str, dict[str, float]]:
    out = {}
    for name, target in targets.items():
        metrics = dict(bench.compare(scores, target))
        metrics["pairs"] = pair_counts(scores, target)
        out[name] = metrics
    return out


def main() -> int:
    mapping = load_mapping(MAPPING)
    targets, training = load_targets()
    registry = build_registry()
    dataset = mapping_to_dataset(mapping, training)

    # ---- 1. reference baselines, plus the outcome-only comparison
    baselines = {}
    outcome_only = {
        candidate: statistics.mean(per_task.values())
        for candidate, per_task in training.items()
    }
    baselines["outcome success rate (not failure evidence)"] = {
        "scores": outcome_only,
        "evaluation": evaluate(outcome_only, targets),
        "note": (
            "the evaluator's own repeat-0 success rate on the same 50 tasks; "
            "the comparison baseline, not a failure-evidence method"
        ),
    }
    for name, scores in baseline_scores(mapping).items():
        baselines[name] = {"scores": scores, "evaluation": evaluate(scores, targets)}

    # ---- 2. full module grid
    grid = []
    axes = (
        registry.names("counting"),
        registry.names("relationships"),
        [None, *registry.names("trust")],
        [None, *registry.names("feedback")],
        registry.names("formula"),
    )
    for counting, relationships, trust, feedback, formula in itertools.product(*axes):
        config = Configuration.from_mapping(
            {
                "counting": counting,
                "relationships": relationships,
                "trust": trust,
                "feedback": feedback,
                "formula": formula,
            }
        )
        result = run_configuration(registry, config, dataset)
        if result["status"] != "ok":
            continue
        scores = {str(k): round(float(v), 10) for k, v in result["scores"].items()}
        ev = evaluate(scores, targets)
        grid.append(
            {
                "config": {
                    "counting": counting,
                    "relationships": relationships,
                    "trust": trust or "-",
                    "feedback": feedback or "-",
                    "formula": formula,
                },
                "label": f"{counting}/{relationships}/{trust or '-'}/"
                f"{feedback or '-'}/{formula}",
                "uses_training_outcomes": result["scenario_1"],
                "cross_seed_tau": round(ev["cross_seed"]["kendall_tau_b"], 4),
                "generalization_tau": round(
                    ev["generalization"]["kendall_tau_b"], 4
                ),
                "cross_seed_top1": ev["cross_seed"]["tie_aware_top1_hit"],
                "generalization_top1": ev["generalization"]["tie_aware_top1_hit"],
                "scores": scores,
            }
        )

    # ---- 5. cross-check the two module-expressible baselines
    def by_label(label: str):
        return next(row for row in grid if row["label"] == label)

    checks = {}
    for name, label in (
        ("base amplitude", "unique/none/-/-/uncapped_sum"),
        ("pair expansion", "unique/pairs/-/-/uncapped_sum"),
    ):
        direct = baselines[name]["scores"]
        via_modules = by_label(label)["scores"]
        delta = max(abs(direct[c] - via_modules[c]) for c in direct)
        checks[name] = {"module_configuration": label, "max_abs_difference": delta}
        if delta > 1e-9:
            raise AssertionError(f"{name} does not match {label}: delta {delta}")

    # ---- 3/4. distinct configurations, champions, best per module
    seen: dict[tuple, dict] = {}
    for row in grid:
        key = tuple(sorted(row["scores"].items()))
        if key not in seen or len(row["label"]) < len(seen[key]["label"]):
            seen[key] = row
    distinct = [
        row for row in seen.values() if len(set(row["scores"].values())) > 1
    ]
    for row in distinct:
        row["average_tau"] = round(
            (row["cross_seed_tau"] + row["generalization_tau"]) / 2, 4
        )

    champions = {
        "best_average": max(distinct, key=lambda r: r["average_tau"]),
        "best_cross_seed": max(distinct, key=lambda r: r["cross_seed_tau"]),
        "best_generalization": max(distinct, key=lambda r: r["generalization_tau"]),
        "best_gold_free": max(
            (r for r in distinct if not r["uses_training_outcomes"]),
            key=lambda r: r["average_tau"],
        ),
    }
    top1_both = [
        r
        for r in distinct
        if r["cross_seed_top1"] == 1.0 and r["generalization_top1"] == 1.0
    ]
    if top1_both:
        champions["best_top1_both"] = max(top1_both, key=lambda r: r["average_tau"])

    per_module: dict[str, dict[str, dict]] = {}
    for axis in ("counting", "relationships", "trust", "feedback", "formula"):
        per_module[axis] = {}
        for option in sorted({row["config"][axis] for row in distinct}):
            pool = [row for row in distinct if row["config"][axis] == option]
            per_module[axis][option] = max(pool, key=lambda r: r["average_tau"])

    results = {
        "candidates": sorted(mapping["candidates"]),
        "targets": targets,
        "baselines": baselines,
        "grid_cells": len(grid),
        "distinct_score_vectors": len(distinct),
        "champions": champions,
        "best_per_module": per_module,
        "baseline_module_crosscheck": checks,
        "grid": grid,
    }
    (HERE / "results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"grid cells {len(grid)} | distinct score vectors {len(distinct)}")
    print("\nbaselines (cross-seed tau / generalization tau)")
    for name, item in baselines.items():
        ev = item["evaluation"]
        print(
            f"  {name:<20} {ev['cross_seed']['kendall_tau_b']:+.3f} / "
            f"{ev['generalization']['kendall_tau_b']:+.3f}"
        )
    print("\ncross-check vs module configurations: "
          + ", ".join(f"{k} delta {v['max_abs_difference']:.1e}"
                      for k, v in checks.items()))
    print("\nchampions")
    for name, row in champions.items():
        print(
            f"  {name:<22} {row['cross_seed_tau']:+.3f} / "
            f"{row['generalization_tau']:+.3f}   {row['label']}"
        )
    print(f"\nwrote {HERE / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
