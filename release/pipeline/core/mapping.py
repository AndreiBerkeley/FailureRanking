"""The portable pipeline input: a judge mapping, benchmark-agnostic.

The whole pipeline runs from one self-contained JSON document — the
mapping — regardless of which benchmark, judge, or training set produced
it:

    {
      "schema_version": 1,
      "benchmark": "<free-form label>",
      "candidates": {
        "<candidate id>": {
          "<task id>": [ {"code": "<failure mode>", ...extras}, ... ],
          ...
        },
        ...
      }
    }

Each record needs only `code` — the judged failure mode. Every other
field is carried through untouched as material for the trust segment
(segment 3); the core pipeline never interprets extras.

`convert_adapter15` turns the current HoVer artifact into this contract,
so the existing data is just one instance of the general input.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .evidence import load_evidence
from .grid import Dataset

MAPPING_SCHEMA_VERSION = 1

#: adapter-15 point fields carried into record extras for later trust use.
ADAPTER15_EXTRA_FIELDS = (
    "judge_confidence",
    "evidence_strength",
    "evidence_span_verified",
    "outcome_link",
    "recovery_status",
    "severity",
    "objective_relevance",
    "candidate_attribution",
)


def convert_adapter15(stage1_path: Path, traces_dir: Path) -> dict[str, Any]:
    """Flatten the adapter-15 artifact into the portable mapping: one
    record per primary taxonomy assignment, extras carried through."""

    evidence, _ = load_evidence(stage1_path, traces_dir)
    candidates: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for candidate, tasks in evidence.items():
        per_task: dict[str, list[dict[str, Any]]] = {}
        for task, points in tasks.items():
            records = []
            for point in points:
                extras = {
                    key: point.get(key)
                    for key in ADAPTER15_EXTRA_FIELDS
                    if point.get(key) is not None
                }
                for assignment in point.get("taxonomy_mappings") or []:
                    if assignment.get("primary_or_secondary") != "primary":
                        continue
                    code = assignment.get("code")
                    if not code:
                        continue
                    record = {"code": str(code), **extras}
                    confidence = assignment.get("mapping_confidence")
                    if confidence is not None:
                        record["mapping_confidence"] = confidence
                    records.append(record)
            per_task[task] = records
        candidates[str(candidate)] = per_task
    return {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "benchmark": "hover-adapter15",
        "candidates": candidates,
    }


def validate_mapping(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != MAPPING_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported mapping schema {payload.get('schema_version')!r}"
        )
    candidates = payload.get("candidates")
    if not isinstance(candidates, Mapping) or not candidates:
        raise ValueError("mapping has no candidates")
    for candidate, tasks in candidates.items():
        if not isinstance(tasks, Mapping) or not tasks:
            raise ValueError(f"candidate {candidate!r} has no tasks")
        for task, records in tasks.items():
            if not isinstance(records, list):
                raise ValueError(f"{candidate}/{task} records are not a list")
            for record in records:
                if not isinstance(record, Mapping) or not record.get("code"):
                    raise ValueError(
                        f"{candidate}/{task} contains a record without a code"
                    )


def mapping_to_dataset(
    payload: Mapping[str, Any],
    training_outcomes: Mapping[Any, Mapping[str, float]] | None = None,
) -> Dataset:
    """Turn a validated mapping into the runner's Dataset. Candidate ids
    are kept as given (stringly) so the contract stays benchmark-neutral."""

    validate_mapping(payload)
    evidence = {
        candidate: {task: list(records) for task, records in tasks.items()}
        for candidate, tasks in payload["candidates"].items()
    }
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:24]
    outcomes = None
    if training_outcomes is not None:
        outcomes = {
            str(candidate): dict(tasks)
            for candidate, tasks in training_outcomes.items()
        }
        fingerprint = f"{fingerprint}+gold"
    capabilities: set[str] = set()
    all_records = [
        record
        for tasks in evidence.values()
        for records in tasks.values()
        for record in records
    ]
    if any("recovery_status" in record for record in all_records):
        capabilities.add("recovery_labels")
    if any("outcome_link" in record for record in all_records):
        capabilities.add("outcome_link")
    return Dataset(
        evidence=evidence,
        fingerprint=fingerprint,
        outcomes=outcomes,
        capabilities=frozenset(capabilities),
    )


def coarsen_mapping(payload: Mapping[str, Any], resolution: str) -> dict[str, Any]:
    """Segment-1 code-resolution preprocessor (decision 2026-08-18):
    resolution belongs to what arrives, not to how it is used.

    "codes"      — unchanged (full resolution).
    "categories" — every code collapses to its leading letter before the
                   dot (A.6 -> A), the taxonomy-category view.
    "severity"   — every code collapses to the record's judged severity
                   level (from the extras; "unknown" when absent), so
                   counting and relationships operate on severity classes.
    """

    validate_mapping(payload)
    if resolution == "codes":
        return dict(payload)
    if resolution not in ("categories", "severity"):
        raise ValueError(f"unknown resolution {resolution!r}")
    candidates: dict[str, Any] = {}
    for candidate, tasks in payload["candidates"].items():
        candidates[candidate] = {
            task: [
                {**record,
                 "code": (str(record["code"]).split(".")[0]
                          if resolution == "categories"
                          else str(record.get("severity") or "unknown"))}
                for record in records
            ]
            for task, records in tasks.items()
        }
    return {**payload, "candidates": candidates,
            "resolution": resolution}


def load_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_mapping(payload)
    return payload


def load_gold_file(path: Path) -> dict[str, dict[str, float]]:
    """Portable training gold: {candidate: {task: outcome}}. Candidate ids
    are strings, matching the mapping contract."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise ValueError("gold file must map candidates to task outcomes")
    return {
        str(candidate): {str(t): float(v) for t, v in tasks.items()}
        for candidate, tasks in payload.items()
    }


def convert_adapter15_gold(
    gold_root: Path, mapping_payload: Mapping[str, Any]
) -> dict[str, dict[str, float]]:
    """Repeat-0 gold for exactly the mapping's candidates and tasks."""

    from .evidence import load_gold

    gold = load_gold(gold_root)
    outcomes: dict[str, dict[str, float]] = {}
    for candidate, tasks in mapping_payload["candidates"].items():
        per = gold[int(candidate)]
        outcomes[str(candidate)] = {
            task: float(per[task][0]) for task in tasks
        }
    return outcomes


def save_mapping(payload: Mapping[str, Any], path: Path) -> None:
    validate_mapping(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
