"""Segment 6 — formula options, version 1 (reviewed 2026-08-18).

The within-task combination: how the task's instances (with their trust
weights and feedback influences) become one bounded task burden.

The five assumed-game combiners from the segment-5/6 review, ordered by
their overlap assumption:

  uncapped_sum  none: overlaps billed once per instance touching them
  capped_sum    additive but a task cannot exceed "fully failed" (1)
  noisy_or      instances are independent chances to break the task
  max           total overlap: the strongest instance is the whole story
  pie_signed    inclusion-exclusion: singles added, even-order groups
                subtracted, odd-order groups added; the overlap is
                cancelled by the observed group structure itself

Bounded combiners (all but uncapped_sum) clip each entry value into
[0, 1] before combining, so the task burden stays in [0, 1] and task
quality (1 - burden) stays interpretable.

Honest note recorded at review time: with flat unit values (no trust, no
feedback), the four bounded combiners all collapse to the same method —
the union indicator, "did anything fail on this task at all" (candidate
score = clean-task rate). They separate as soon as segment 3 or 4
supplies non-unit values. This is expected and tested, not a defect.

`pie_signed` reads each instance's group order from its category id
(the segment-2 conventions: "A.6" order 1, "A.6+C.2" order 2, "A.6|once"
order 1, "sig:..." order 1, "A.6->C.2" order 2) and applies sign
(-1)^(order+1). With singles-only categorization it therefore equals the
plain sum; it becomes a distinct method when group instances exist.
Truncated series (categorize at singles+pairs) are Bonferroni-style
bounds and may go negative on dense tasks; burden is floored at 0.
Measured-valuation PIE arrives with the segment-4 review.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .segments import Registry

Entry = Mapping[str, Any]


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def group_order(item: Any) -> int:
    """Group order from the segment-2 category id conventions."""

    label = str(item)
    if label.startswith("sig:"):
        return 1
    if "->" in label:
        return 2
    return label.count("+") + 1


def merge_uncapped_sum(entries: Sequence[Entry], candidate_context=None) -> float:
    return sum(float(e["value"]) for e in entries)


def merge_capped_sum(entries: Sequence[Entry], candidate_context=None) -> float:
    return min(1.0, sum(_clip(e["value"]) for e in entries))


def merge_noisy_or(entries: Sequence[Entry], candidate_context=None) -> float:
    survival = 1.0
    for entry in entries:
        survival *= 1.0 - _clip(entry["value"])
    return 1.0 - survival


def merge_max(entries: Sequence[Entry], candidate_context=None) -> float:
    return max((_clip(e["value"]) for e in entries), default=0.0)


def merge_pie_signed(entries: Sequence[Entry], candidate_context=None) -> float:
    total = 0.0
    for entry in entries:
        sign = 1.0 if group_order(entry["item"]) % 2 == 1 else -1.0
        total += sign * _clip(entry["value"])
    return _clip(total)


def install_formula_options(registry: Registry) -> None:
    registry.register(
        "formula", "capped_sum", merge_capped_sum,
        description="additive within task, capped at fully-failed",
    )
    registry.register(
        "formula", "noisy_or", merge_noisy_or,
        description="independent-chances OR gate, saturating below 1",
    )
    registry.register(
        "formula", "max", merge_max,
        description="winner-take-all: the strongest instance is the task burden",
    )
    registry.register(
        "formula", "pie_signed", merge_pie_signed,
        description="inclusion-exclusion over group instances, sign by order",
    )
