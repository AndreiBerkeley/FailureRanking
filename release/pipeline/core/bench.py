"""The fixed test bench — segment 7's convention plus the frozen targets
and metrics. Never varies between experiments, so every grid cell ever run
is directly comparable.

Targets:
  cross_seed      mean gold over repeats 1-4 on the shared 50 tasks;
  generalization  mean gold over the disjoint 250 tasks at repeat 0.

Metrics per (score, target): Kendall tau-b, Spearman rho, mean absolute
rank error, tie-aware top-1 hit. Scores follow the fixed ranking
convention (higher is better) and targets are success rates, so both
sides share one direction — no flips anywhere.
"""

from __future__ import annotations

import statistics
from typing import Any, Mapping, Sequence

from .segments import RANKING_CONVENTION


def average_ranks(values: Sequence[float], higher_is_better: bool = True) -> list[float]:
    """Rank 1 = best; exact ties share their average position."""

    order = sorted(
        range(len(values)),
        key=lambda i: (-values[i] if higher_is_better else values[i]),
    )
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while (
            end + 1 < len(order)
            and values[order[end + 1]] == values[order[position]]
        ):
            end += 1
        average = (position + end) / 2 + 1
        for index in order[position : end + 1]:
            ranks[index] = average
        position = end + 1
    return ranks


def kendall_tau_b(x: Sequence[float], y: Sequence[float]) -> float:
    n = len(x)
    concordant = discordant = 0
    ties_x = ties_y = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx == 0 and dy == 0:
                ties_x += 1
                ties_y += 1
            elif dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif (dx > 0) == (dy > 0):
                concordant += 1
            else:
                discordant += 1
    pairs = n * (n - 1) / 2
    denom = ((pairs - ties_x) * (pairs - ties_y)) ** 0.5
    return 0.0 if denom == 0 else (concordant - discordant) / denom


def spearman_rho(x: Sequence[float], y: Sequence[float]) -> float:
    rx = average_ranks(x)
    ry = average_ranks(y)
    mean_x, mean_y = statistics.mean(rx), statistics.mean(ry)
    cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry))
    var_x = sum((a - mean_x) ** 2 for a in rx)
    var_y = sum((b - mean_y) ** 2 for b in ry)
    denom = (var_x * var_y) ** 0.5
    return 0.0 if denom == 0 else cov / denom


def tie_aware_top1_hit(x: Sequence[float], y: Sequence[float]) -> float:
    """1.0 when the tied-best groups share at least one candidate."""

    best_x = max(x)
    best_y = max(y)
    group_x = {i for i, v in enumerate(x) if v == best_x}
    group_y = {i for i, v in enumerate(y) if v == best_y}
    return 1.0 if group_x & group_y else 0.0


def compare(
    scores: Mapping[int, float],
    target: Mapping[int, float],
) -> dict[str, float]:
    """Grade one configuration's scores against one target. Both sides are
    higher-is-better by the fixed convention; no direction flip."""

    assert RANKING_CONVENTION["direction"] == "higher_is_better"
    candidates = sorted(scores)
    x = [scores[c] for c in candidates]
    y = [target[c] for c in candidates]
    rank_x = average_ranks(x)
    rank_y = average_ranks(y)
    return {
        "kendall_tau_b": kendall_tau_b(x, y),
        "spearman_rho": spearman_rho(x, y),
        "mean_absolute_rank_error": statistics.mean(
            abs(a - b) for a, b in zip(rank_x, rank_y)
        ),
        "tie_aware_top1_hit": tie_aware_top1_hit(x, y),
    }


def build_targets(
    gold: Mapping[int, Mapping[str, Mapping[int, float]]],
    shared_tasks: Sequence[str],
    disjoint_tasks: Sequence[str],
) -> dict[str, dict[int, float]]:
    cross_seed = {
        candidate: statistics.mean(
            gold[candidate][task][repeat]
            for task in shared_tasks
            for repeat in (1, 2, 3, 4)
        )
        for candidate in gold
    }
    generalization = {
        candidate: statistics.mean(
            gold[candidate][task][0] for task in disjoint_tasks
        )
        for candidate in gold
    }
    return {"cross_seed": cross_seed, "generalization": generalization}


def grade(
    results: Sequence[Mapping[str, Any]],
    targets: Mapping[str, Mapping[int, float]],
) -> list[dict[str, Any]]:
    """Grade every ok grid cell against every target."""

    graded = []
    for result in results:
        if result.get("status") != "ok":
            graded.append(dict(result))
            continue
        scores = {int(k): float(v) for k, v in result["scores"].items()}
        entry = dict(result)
        entry["evaluation"] = {
            name: compare(scores, target) for name, target in targets.items()
        }
        graded.append(entry)
    return graded
