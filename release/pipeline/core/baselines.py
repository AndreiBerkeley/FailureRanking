"""The five reference baselines, computed directly.

These are the pre-framework scoring methods this work started from. Two of
them (persistent pairs, order-normalized) price a co-occurrence by how often
that candidate repeats it, which is a per-candidate statistic computed across
tasks; the module grid has no option that exposes that pricing, so all five
are implemented here as reference formulas rather than as module
configurations.

Two of the five ARE expressible as module configurations, and this is used as
a cross-check in the experiment runner:

    base amplitude  = counting:unique / relationships:none  / formula:uncapped_sum
    pair expansion  = counting:unique / relationships:pairs / formula:uncapped_sum

Every baseline is a per-task burden averaged over tasks. The package reports
scores in the shared convention "higher is better", so the returned score is

    score = 1 - mean task burden

which preserves the ordering of the original burden formulas exactly.
"""

from __future__ import annotations

import statistics
from collections import Counter
from itertools import combinations
from typing import Mapping, Sequence

MAX_ORDER = 6


def _task_modes(records: Sequence[Mapping]) -> frozenset[str]:
    return frozenset(str(record["code"]) for record in records)


def _combination_prevalence(
    task_sets: Sequence[frozenset[str]], min_order: int, max_order: int
) -> Counter:
    """How often each combination recurs across this candidate's tasks."""

    counts: Counter = Counter()
    for modes in task_sets:
        for order in range(min_order, min(len(modes), max_order) + 1):
            for combo in combinations(sorted(modes), order):
                counts[combo] += 1
    return counts


def base_amplitude(task_sets: Sequence[frozenset[str]]) -> float:
    """Mean number of distinct failure modes per task."""

    return statistics.mean(len(modes) for modes in task_sets)


def pair_expansion(task_sets: Sequence[frozenset[str]]) -> float:
    """Each mode costs one unit; each co-occurring pair costs one more."""

    return statistics.mean(
        len(modes) + len(modes) * (len(modes) - 1) / 2 for modes in task_sets
    )


def persistent_pairs(task_sets: Sequence[frozenset[str]]) -> float:
    """Modes at unit cost plus each pair weighted by the square of how often
    this candidate repeats it."""

    n = len(task_sets)
    counts = _combination_prevalence(task_sets, 2, 2)
    interaction = sum((count / n) ** 2 for count in counts.values())
    return base_amplitude(task_sets) + interaction


def full_combinations(task_sets: Sequence[frozenset[str]]) -> float:
    """Persistent pairs extended to every group size 2 through 6, nested."""

    n = len(task_sets)
    counts = _combination_prevalence(task_sets, 2, MAX_ORDER)
    interaction = sum((count / n) ** 2 for count in counts.values())
    return base_amplitude(task_sets) + interaction


def order_normalized(task_sets: Sequence[frozenset[str]]) -> float:
    """Like full combinations, but within each task every group size is
    averaged before summing, so no size can contribute more than one unit to
    a task however many groups of that size it contains."""

    n = len(task_sets)
    counts = _combination_prevalence(task_sets, 2, MAX_ORDER)
    burdens = []
    for modes in task_sets:
        interaction = 0.0
        for order in range(2, min(len(modes), MAX_ORDER) + 1):
            shares = [
                counts[combo] / n for combo in combinations(sorted(modes), order)
            ]
            if shares:
                interaction += statistics.mean(shares)
        burdens.append(len(modes) + interaction)
    return statistics.mean(burdens)


BASELINES = {
    "base amplitude": base_amplitude,
    "pair expansion": pair_expansion,
    "persistent pairs": persistent_pairs,
    "full combinations": full_combinations,
    "order normalized": order_normalized,
}


def score_candidates(
    mapping: Mapping, tasks: Sequence[str] | None = None
) -> dict[str, dict[str, float]]:
    """baseline name -> candidate -> score (higher is better)."""

    scores: dict[str, dict[str, float]] = {name: {} for name in BASELINES}
    for candidate, per_task in mapping["candidates"].items():
        keys = sorted(per_task) if tasks is None else sorted(tasks)
        task_sets = [_task_modes(per_task[task]) for task in keys]
        for name, fn in BASELINES.items():
            scores[name][str(candidate)] = 1.0 - fn(task_sets)
    return scores
