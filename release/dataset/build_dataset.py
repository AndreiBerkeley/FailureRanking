#!/usr/bin/env python3
"""Build the shipped dataset files from the source evaluation run.

This script documents provenance; a reader of the package does not need to
run it, because its outputs (tasks.jsonl, outcomes.jsonl, splits.json) are
shipped. It requires the original GEPA evaluation run, which is not part of
this package.

Outputs
-------
tasks.jsonl     one line per task: task_id, claim, required_titles
outcomes.jsonl  one line per evaluated run: candidate, task_id, repeat, score
splits.json     the evidence/held-out partition actually used

Usage
-----
python build_dataset.py --run <path to evaluation run> --out .
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def build(run: Path, out: Path) -> None:
    traces = run / "evaluation" / "traces"
    gold_root = run / "evaluation" / "gold_do_not_pass_to_judge"

    # ---- claims: read once from any candidate's traces (task text is shared)
    claims: dict[str, str] = {}
    for path in sorted((traces / "candidate_000").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        task_id = str(record["task"]["source_id"])
        claim = str(record["input"]["claim"])
        if task_id in claims and claims[task_id] != claim:
            raise ValueError(f"claim text differs across runs of task {task_id}")
        claims[task_id] = claim

    # ---- gold: required evidence titles, and every evaluated outcome
    required: dict[str, list[str]] = {}
    outcomes: list[dict] = []
    repeats_per_task: dict[str, set[int]] = defaultdict(set)
    for path in sorted(gold_root.glob("candidate_*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        task_id = str(record["task"]["source_id"])
        candidate = int(record["candidate_index"])
        repeat = int(record["evaluation_repeat"])
        # de-duplicate titles, preserve first-seen order
        titles, seen = [], set()
        for title in record.get("gold_supporting_titles") or []:
            if title not in seen:
                seen.add(title)
                titles.append(title)
        if task_id in required and required[task_id] != titles:
            raise ValueError(f"required titles differ across runs of task {task_id}")
        required[task_id] = titles
        outcomes.append(
            {
                "candidate": candidate,
                "task_id": task_id,
                "repeat": repeat,
                "score": float(record["gold_score"]),
            }
        )
        repeats_per_task[task_id].add(repeat)

    missing = set(required) - set(claims)
    if missing:
        raise ValueError(f"{len(missing)} tasks have gold but no claim text")

    # ---- split: tasks carrying repeats 1-4 are the evidence subset
    evidence = sorted(t for t, r in repeats_per_task.items() if r == {0, 1, 2, 3, 4})
    heldout = sorted(t for t, r in repeats_per_task.items() if r == {0})
    if len(evidence) != 50 or len(heldout) != 250:
        raise ValueError(f"unexpected split: {len(evidence)} / {len(heldout)}")

    out.mkdir(parents=True, exist_ok=True)
    with (out / "tasks.jsonl").open("w", encoding="utf-8") as handle:
        for task_id in sorted(required):
            handle.write(
                json.dumps(
                    {
                        "task_id": task_id,
                        "claim": claims[task_id],
                        "required_titles": required[task_id],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    with (out / "outcomes.jsonl").open("w", encoding="utf-8") as handle:
        for row in sorted(
            outcomes, key=lambda r: (r["candidate"], r["task_id"], r["repeat"])
        ):
            handle.write(json.dumps(row) + "\n")
    (out / "splits.json").write_text(
        json.dumps(
            {
                "evidence_tasks": evidence,
                "heldout_tasks": heldout,
                "note": (
                    "Evidence tasks were run five times per candidate (repeats "
                    "0-4); held-out tasks once (repeat 0). Scoring uses repeat-0 "
                    "traces of the evidence tasks only."
                ),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"tasks {len(required)} | outcomes {len(outcomes)} | "
        f"evidence {len(evidence)} | held-out {len(heldout)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    build(args.run, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
