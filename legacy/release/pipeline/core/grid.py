"""Grid runner: compose one option per variable axis into a scoring
pipeline, enumerate the valid cross-product, and cache every cell.

A configuration names one registered option per mandatory axis and
optionally one per optional axis (trust, feedback). The runner:

1. validates the configuration against the registry;
2. applies the compatibility mask: every option's `requires` tags must be
   covered by the dataset's capabilities plus the other chosen options'
   `provides` tags — incoherent cells are skipped, not errored;
3. composes the pipeline and produces one score per candidate. Task-first
   and higher-is-better: segment 6 merges each task into a burden, the
   runner converts it to a task quality (1 - burden), and the candidate
   score is the plain mean quality over tasks;
4. records whether the configuration consumed training gold (scenario 1),
   inferred from any chosen option requiring the training-gold tag; and
5. caches results keyed by (configuration, dataset fingerprint).

Segment 1 is the fixed evidence loader (see core/evidence.py); segment 7
is the fixed ranking convention (segments.RANKING_CONVENTION), applied by
the bench. Neither is a grid axis.

The registry ships empty; running a grid before options are registered
yields an empty result set, by design.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .segments import AXES, OPTIONAL_AXES, Option, RANKING_CONVENTION, Registry

GOLD_TAG = "training_gold"          # capability tag marking gold consumption


@dataclass(frozen=True)
class Configuration:
    """One cell of the grid: option name per axis (None = optional skip)."""

    choices: tuple[tuple[str, str | None], ...]

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, str | None]) -> "Configuration":
        unknown = set(mapping) - set(AXES)
        if unknown:
            raise ValueError(f"unknown axes in configuration: {sorted(unknown)}")
        choices = []
        for axis in AXES:
            name = mapping.get(axis)
            if name is None and axis not in OPTIONAL_AXES:
                raise ValueError(f"mandatory axis {axis!r} has no option")
            choices.append((axis, name))
        return cls(tuple(choices))

    def as_dict(self) -> dict[str, str | None]:
        return dict(self.choices)

    def label(self) -> str:
        return " | ".join(
            f"{axis}:{name if name is not None else '-'}"
            for axis, name in self.choices
        )


@dataclass
class Dataset:
    """The fixed segment-1 product plus capabilities for the mask.

    evidence: candidate -> task -> list of failure-point records, exactly
        as the fixed loader produced them.
    outcomes: candidate -> task -> training outcome; present only when the
        dataset carries gold, which adds the training-gold capability.
    fingerprint: stable identifier of the underlying artifacts, used as
        the cache key component.
    """

    evidence: Mapping[int, Mapping[str, Any]]
    fingerprint: str
    outcomes: Mapping[int, Mapping[str, float]] | None = None
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def all_capabilities(self) -> frozenset[str]:
        caps = set(self.capabilities)
        if self.outcomes is not None:
            caps.add(GOLD_TAG)
        return frozenset(caps)


def resolve(registry: Registry, config: Configuration) -> dict[str, Option | None]:
    resolved: dict[str, Option | None] = {}
    for axis, name in config.choices:
        resolved[axis] = None if name is None else registry.get(axis, name)
    return resolved


def mask_ok(
    resolved: Mapping[str, Option | None], dataset: Dataset
) -> tuple[bool, str]:
    """Every requirement must be covered by dataset capabilities or another
    chosen option's provides."""

    provided = set(dataset.all_capabilities())
    for option in resolved.values():
        if option is not None:
            provided |= option.provides
    for option in resolved.values():
        if option is None:
            continue
        missing = option.requires - provided
        if missing:
            return False, (
                f"option {option.axis}:{option.name} requires "
                f"{sorted(missing)} which nothing provides"
            )
    return True, ""


def uses_gold(resolved: Mapping[str, Option | None]) -> bool:
    return any(
        option is not None and GOLD_TAG in option.requires
        for option in resolved.values()
    )


def run_configuration(
    registry: Registry,
    config: Configuration,
    dataset: Dataset,
) -> dict[str, Any]:
    """Score every candidate under one configuration (see segments.py for
    the axis contracts)."""

    resolved = resolve(registry, config)
    ok, reason = mask_ok(resolved, dataset)
    if not ok:
        return {"status": "skipped", "reason": reason, "config": config.as_dict()}

    counting = resolved["counting"]
    relationships = resolved["relationships"]
    trust = resolved["trust"]
    feedback = resolved["feedback"]
    formula = resolved["formula"]
    assert counting and relationships and formula

    scores: dict[int, float] = {}
    for candidate, tasks in dataset.evidence.items():
        candidate_context: dict[str, Any] = {
            "candidate": candidate,
            "tasks": tasks,
            "outcomes": None
            if dataset.outcomes is None
            else dataset.outcomes.get(candidate),
        }
        # a feedback option may precompute per-candidate state once
        if feedback is not None and hasattr(feedback.fn, "prepare"):
            candidate_context["feedback_state"] = feedback.fn.prepare(
                candidate_context, **feedback.params
            )
        qualities = []
        for task in sorted(tasks):
            records = tasks[task]
            base = counting.fn(records, **counting.params)
            items = relationships.fn(base, records, **relationships.params)
            entries = []
            for item in items:
                weight = (
                    1.0
                    if trust is None
                    else float(trust.fn(item, records, **trust.params))
                )
                influence = (
                    1.0
                    if feedback is None
                    else float(
                        feedback.fn(item, candidate_context, **feedback.params)
                    )
                )
                entries.append(
                    {
                        "item": item,
                        "weight": weight,
                        "influence": influence,
                        "value": weight * influence,
                    }
                )
            burden = float(
                formula.fn(entries, candidate_context, **formula.params)
            )
            qualities.append(1.0 - burden)
        scores[candidate] = statistics.mean(qualities) if qualities else 1.0

    return {
        "status": "ok",
        "config": config.as_dict(),
        "label": config.label(),
        "scenario_1": uses_gold(resolved),
        "scores": scores,
        "ranking": dict(RANKING_CONVENTION),
    }


def enumerate_configurations(registry: Registry) -> Iterable[Configuration]:
    """Full cross-product (masked later); optional axes include the skip."""

    axes_options: list[list[str | None]] = []
    for axis in AXES:
        names: list[str | None] = list(registry.names(axis))
        if axis in OPTIONAL_AXES:
            names = [None, *names]
        axes_options.append(names)
    if any(not axis_options for axis_options in axes_options):
        return iter(())      # a mandatory axis has no options: empty grid
    return (
        Configuration(tuple(zip(AXES, combo)))
        for combo in itertools.product(*axes_options)
    )


def _cache_key(config: Configuration, dataset: Dataset) -> str:
    payload = json.dumps(
        {"config": config.as_dict(), "dataset": dataset.fingerprint},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def run_grid(
    registry: Registry,
    dataset: Dataset,
    cache_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Run every configuration; reuse cached cells when possible."""

    results = []
    for config in enumerate_configurations(registry):
        cache_path = (
            None
            if cache_dir is None
            else cache_dir / f"{_cache_key(config, dataset)}.json"
        )
        if cache_path is not None and cache_path.exists():
            results.append(json.loads(cache_path.read_text(encoding="utf-8")))
            continue
        result = run_configuration(registry, config, dataset)
        if cache_path is not None and result["status"] == "ok":
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(result, sort_keys=True), encoding="utf-8"
            )
        results.append(result)
    return results
