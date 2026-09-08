"""Segment 3 — relationships between failure modes (reviewed 2026-08-18).

What we consider between modes, on top of (or instead of) the base
per-mode instances from segment 2:

  none          base instances pass through unchanged
  pairs         add unordered co-occurrence pairs ("A.6+C.2")
  groups        add all groups sizes 2..6 (nested)
  groups_only   groups sizes 2..6 INSTEAD of the base instances
  signatures    the task's exact distinct-code set as ONE instance
                ("sig:A.6+C.2"), replacing the base instances
  ordered_pairs add direction-aware pairs by first occurrence
                ("B.6->A.8")

Group multiplicity follows the counting basis: group items are built from
the task's records, and when the base instances carry multiplicity
(counting = total), each group is repeated by the product of its codes'
occurrence counts (Andrei's worked example: A.6 x2 with C.2 x2 gives the
pair four counts). Under unique or flagged bases, groups appear once.
Flags stay at the singles level; group ids use plain codes.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Mapping, Sequence

from .segments import Registry

MAX_GROUP_ORDER = 6


def _counts(records: Sequence[Mapping[str, Any]]) -> Counter:
    return Counter(str(r["code"]) for r in records)


def _base_carries_multiplicity(base: Sequence[str]) -> bool:
    return len(base) != len(set(base))


def _group_items(
    records: Sequence[Mapping[str, Any]],
    with_multiplicity: bool,
    min_order: int = 2,
) -> list[str]:
    counts = _counts(records)
    distinct = sorted(counts)
    items: list[str] = []
    for order in range(min_order, min(len(distinct), MAX_GROUP_ORDER) + 1):
        for group in combinations(distinct, order):
            label = "+".join(group)
            if not with_multiplicity:
                items.append(label)
                continue
            multiplicity = 1
            for code in group:
                multiplicity *= counts[code]
            items.extend([label] * multiplicity)
    return items


def rel_none(base: Sequence[str], records: Sequence[Mapping[str, Any]]) -> list[str]:
    return list(base)


def rel_pairs(base: Sequence[str], records: Sequence[Mapping[str, Any]]) -> list[str]:
    pairs = [
        item
        for item in _group_items(records, _base_carries_multiplicity(base))
        if item.count("+") == 1
    ]
    return list(base) + pairs


def rel_groups(base: Sequence[str], records: Sequence[Mapping[str, Any]]) -> list[str]:
    return list(base) + _group_items(records, _base_carries_multiplicity(base))


def rel_groups_only(
    base: Sequence[str], records: Sequence[Mapping[str, Any]]
) -> list[str]:
    return _group_items(records, _base_carries_multiplicity(base))


def rel_signatures(
    base: Sequence[str], records: Sequence[Mapping[str, Any]]
) -> list[str]:
    distinct = sorted({str(r["code"]) for r in records})
    return [f"sig:{'+'.join(distinct)}"] if distinct else []


def rel_ordered_pairs(
    base: Sequence[str], records: Sequence[Mapping[str, Any]]
) -> list[str]:
    first_seen: dict[str, int] = {}
    for index, record in enumerate(records):
        first_seen.setdefault(str(record["code"]), index)
    ordered = sorted(first_seen, key=lambda code: first_seen[code])
    items = list(base)
    for earlier, later in combinations(ordered, 2):
        items.append(f"{earlier}->{later}")
    return items


def install_relationship_options(registry: Registry) -> None:
    registry.register(
        "relationships", "none", rel_none,
        description="per-mode instances only, no relationship structure",
    )
    registry.register(
        "relationships", "pairs", rel_pairs,
        description="add unordered co-occurrence pairs",
    )
    registry.register(
        "relationships", "groups", rel_groups,
        description="add all groups sizes 2-6, nested",
    )
    registry.register(
        "relationships", "groups_only", rel_groups_only,
        description="groups sizes 2-6 instead of per-mode instances",
    )
    registry.register(
        "relationships", "signatures", rel_signatures,
        description="the task's exact code set as one instance",
    )
    registry.register(
        "relationships", "ordered_pairs", rel_ordered_pairs,
        description="add direction-aware pairs by first occurrence",
    )
