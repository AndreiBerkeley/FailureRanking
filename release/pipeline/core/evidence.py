"""Segment 1 — the fixed evidence loader.

By design decision (Andrei, 2026-08-17) this segment is static: one loader
over the frozen adapter-15 judge artifact and the scored-trace metadata.
Any reinterpretation of the judge's claims — gating, down-weighting,
re-reading — belongs in the trust axis, never in a second loader.

The loader is deliberately faithful: every failure point is kept with its
full attribute record; nothing is filtered or weighed here. Gold outcomes
are loaded separately and attached to the Dataset only when a scenario-1
configuration is intended; their presence is what grants the training-gold
capability that feedback options may require.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from .grid import Dataset


def _fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path).encode("utf-8"))
        digest.update(str(path.stat().st_mtime_ns).encode("utf-8"))
        digest.update(str(path.stat().st_size).encode("utf-8"))
    return digest.hexdigest()[:24]


def load_trace_metadata(traces_dir: Path) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for path in traces_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        trace_id = str(payload.get("trace_id") or path.stem)
        item = payload.get("metadata")
        if not isinstance(item, Mapping):
            raise ValueError(f"trace {trace_id} lacks metadata")
        metadata[trace_id] = dict(item)
    return metadata


def load_evidence(
    stage1_path: Path,
    traces_dir: Path,
    expected_diagnoses: int = 600,
) -> tuple[dict[int, dict[str, list[dict[str, Any]]]], str]:
    """candidate -> task -> list of failure-point records, plus fingerprint."""

    metadata = load_trace_metadata(traces_dir)
    stage1 = json.loads(stage1_path.read_text(encoding="utf-8"))
    if stage1.get("failure_count") != 0:
        raise ValueError("judge artifact contains runner failures")
    diagnoses = stage1.get("diagnoses")
    if not isinstance(diagnoses, list) or len(diagnoses) != expected_diagnoses:
        raise ValueError(
            f"expected {expected_diagnoses} diagnoses, found {len(diagnoses or [])}"
        )

    evidence: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(dict)
    for diagnosis in diagnoses:
        trace_id = str(diagnosis["trace_id"])
        meta = metadata[trace_id]
        candidate = int(meta["candidate_index"])
        task = str(meta["task_source_id"])
        if int(meta["evaluation_repeat"]) != 0:
            raise ValueError(f"trace {trace_id} is not repeat 0")
        if task in evidence[candidate]:
            raise ValueError(f"duplicate candidate/task {candidate}/{task}")
        evidence[candidate][task] = list(diagnosis.get("failure_points") or [])
    fingerprint = _fingerprint([stage1_path])
    return {c: dict(t) for c, t in evidence.items()}, fingerprint


def load_gold(root: Path) -> dict[int, dict[str, dict[int, float]]]:
    """candidate -> task -> repeat -> gold score (validation and, when a
    configuration declares scenario 1, segment-4 feedback)."""

    records: dict[int, dict[str, dict[int, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for path in root.glob("candidate_*/*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidate = int(payload["candidate_index"])
        task = str(payload["task"]["source_id"])
        repeat = int(payload["evaluation_repeat"])
        score = float(payload["gold_score"])
        existing = records[candidate][task].get(repeat)
        if existing is not None and existing != score:
            raise ValueError(
                f"conflicting gold candidate={candidate} task={task} repeat={repeat}"
            )
        records[candidate][task][repeat] = score
    return {c: {t: dict(r) for t, r in tasks.items()} for c, tasks in records.items()}


def build_dataset(
    stage1_path: Path,
    traces_dir: Path,
    tasks: set[str] | None = None,
    training_outcomes: Mapping[int, Mapping[str, float]] | None = None,
) -> Dataset:
    """Assemble the fixed Dataset. `tasks` restricts to a task subset (the
    shared 50); `training_outcomes` attaches repeat-0 gold for scenario-1
    configurations and grants the training-gold capability."""

    evidence, fingerprint = load_evidence(stage1_path, traces_dir)
    if tasks is not None:
        evidence = {
            candidate: {t: recs for t, recs in per.items() if t in tasks}
            for candidate, per in evidence.items()
        }
    if training_outcomes is not None:
        fingerprint = f"{fingerprint}+gold"
    return Dataset(
        evidence=evidence,
        fingerprint=fingerprint,
        outcomes=training_outcomes,
    )
