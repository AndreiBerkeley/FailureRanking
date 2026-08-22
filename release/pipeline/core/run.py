"""The one-command pipeline: mapping in, ranking out.

    python -m core.run --mapping mapping.json --out ranking.json

or, for the current HoVer artifact (converted on the fly):

    python -m core.run \
        --adapter15 trials/2026-08-08-falat-recovery/scored_stage1_reflection_v9_adapter15.json \
        --traces trials/2026-08-08-falat-recovery/scored_traces \
        --out ranking.json [--save-mapping mapping.json]

The program installs the default gold-free options (segments 3 and 4
skipped), runs every segment automatically, and emits the ranking under
the fixed convention: higher score is better, ties share their average
rank. `--config` may name a JSON file choosing other registered options
per axis once more are reviewed in.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .bench import average_ranks
from .counting_options import install_counting_options
from .feedback_options import install_feedback_options
from .defaults import DEFAULT_CONFIGURATION
from .formula_options import install_formula_options, merge_uncapped_sum
from .relationship_options import install_relationship_options
from .trust_options import install_trust_options
from .grid import Configuration, run_configuration
from .mapping import (
    coarsen_mapping,
    convert_adapter15,
    convert_adapter15_gold,
    load_gold_file,
    load_mapping,
    mapping_to_dataset,
    save_mapping,
)
from .segments import AXES, RANKING_CONVENTION, Registry


def build_registry() -> Registry:
    """All reviewed options, installed explicitly (registries are empty
    at import; this is the program's configuration surface)."""

    registry = Registry()
    install_counting_options(registry)
    install_relationship_options(registry)
    install_formula_options(registry)
    install_feedback_options(registry)
    install_trust_options(registry)
    registry.register(
        "formula", "uncapped_sum", merge_uncapped_sum,
        description="plain within-task addition; no cap, no overlap handling",
    )
    return registry


def build_ranking(scores: Mapping[str, float]) -> list[dict[str, Any]]:
    candidates = sorted(scores)
    values = [scores[c] for c in candidates]
    ranks = average_ranks(values, higher_is_better=True)
    rows = [
        {"candidate": candidate, "score": scores[candidate], "rank": rank}
        for candidate, rank in zip(candidates, ranks)
    ]
    rows.sort(key=lambda row: (row["rank"], str(row["candidate"])))
    return rows


def run_pipeline(
    mapping_payload: Mapping[str, Any],
    configuration: Configuration | None = None,
    registry: Registry | None = None,
    training_outcomes: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, Any]:
    if registry is None:
        registry = build_registry()
    configuration = configuration or DEFAULT_CONFIGURATION
    dataset = mapping_to_dataset(mapping_payload, training_outcomes)
    result = run_configuration(registry, configuration, dataset)
    if result["status"] != "ok":
        raise RuntimeError(f"configuration not runnable: {result.get('reason')}")
    return {
        "benchmark": mapping_payload.get("benchmark"),
        "config": result["config"],
        "scenario_1": result["scenario_1"],
        "ranking_convention": dict(RANKING_CONVENTION),
        "scores": result["scores"],
        "ranking": build_ranking(result["scores"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--mapping", type=Path, help="portable mapping JSON")
    source.add_argument("--adapter15", type=Path, help="adapter-15 stage1 artifact")
    parser.add_argument("--traces", type=Path, help="scored traces dir (with --adapter15)")
    parser.add_argument("--save-mapping", type=Path, help="write the converted mapping")
    parser.add_argument("--config", type=Path, help="JSON: axis -> registered option")
    parser.add_argument(
        "--resolution", choices=("codes", "categories", "severity"), default="codes",
        help="segment-1 code resolution (mapping preprocessor)",
    )
    gold = parser.add_mutually_exclusive_group()
    gold.add_argument("--gold", type=Path,
                      help="portable training gold JSON {candidate:{task:score}}")
    gold.add_argument("--gold-root", type=Path,
                      help="adapter-15 gold directory (repeat-0 outcomes)")
    parser.add_argument("--list-options", action="store_true",
                        help="print registered options per axis and exit")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    if args.list_options:
        registry = build_registry()
        for axis in AXES:
            names = registry.names(axis) or ["(none registered)"]
            print(f"{axis}:")
            for name in names:
                print(f"  {name}")
        return 0
    if args.out is None:
        parser.error("--out is required unless --list-options")
    if args.mapping is None and args.adapter15 is None:
        parser.error("one of --mapping or --adapter15 is required")

    if args.adapter15 is not None:
        if args.traces is None:
            parser.error("--adapter15 requires --traces")
        payload = convert_adapter15(args.adapter15, args.traces)
        if args.save_mapping is not None:
            save_mapping(payload, args.save_mapping)
    else:
        payload = load_mapping(args.mapping)
    if args.resolution != "codes":
        payload = coarsen_mapping(payload, args.resolution)

    configuration = None
    if args.config is not None:
        configuration = Configuration.from_mapping(
            json.loads(args.config.read_text(encoding="utf-8"))
        )

    training_outcomes = None
    if args.gold is not None:
        training_outcomes = load_gold_file(args.gold)
    elif args.gold_root is not None:
        training_outcomes = convert_adapter15_gold(args.gold_root, payload)

    output = run_pipeline(payload, configuration, training_outcomes=training_outcomes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=1, sort_keys=True), encoding="utf-8")

    print(f"benchmark: {output['benchmark']}   "
          f"scenario-1: {output['scenario_1']}   (higher score = better)")
    for row in output["ranking"]:
        print(f"  rank {row['rank']:>4}  candidate {row['candidate']:>4}  "
              f"score {row['score']:+.4f}")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
