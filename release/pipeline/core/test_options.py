#!/usr/bin/env python3
"""Tests for the reviewed counting / relationships / formula options,
including Andrei's worked A.6/C.2 example. Run: python3 -m core.test_options"""

from __future__ import annotations

from collections import Counter

from core.counting_options import (
    counting_flagged,
    counting_total,
    counting_unique,
    install_counting_options,
)
from core.formula_options import (
    group_order,
    install_formula_options,
    merge_capped_sum,
    merge_max,
    merge_noisy_or,
    merge_pie_signed,
    merge_uncapped_sum,
)
from core.relationship_options import (
    install_relationship_options,
    rel_groups,
    rel_groups_only,
    rel_ordered_pairs,
    rel_pairs,
    rel_signatures,
)
from core.segments import Registry

# Andrei's example: A.6 twice, C.2 twice, interleaved.
EXAMPLE = [{"code": "A.6"}, {"code": "C.2"}, {"code": "A.6"}, {"code": "C.2"}]


# ------------------------------------------------------- counting (seg 2)
def test_counting_bases():
    assert counting_unique(EXAMPLE) == ["A.6", "C.2"]
    assert counting_flagged(EXAMPLE) == ["A.6|repeated", "C.2|repeated"]
    assert counting_total(EXAMPLE) == ["A.6", "A.6", "C.2", "C.2"]
    assert counting_flagged([{"code": "B.1"}]) == ["B.1|once"]


# -------------------------------------------------- relationships (seg 3)
def test_pairs_unique_example_three_instances():
    base = counting_unique(EXAMPLE)
    assert sorted(rel_pairs(base, EXAMPLE)) == ["A.6", "A.6+C.2", "C.2"]


def test_pairs_total_example_eight_counts():
    base = counting_total(EXAMPLE)
    counts = Counter(rel_pairs(base, EXAMPLE))
    assert counts["A.6"] == 2 and counts["C.2"] == 2
    assert counts["A.6+C.2"] == 4                    # 2 x 2 product
    assert len(counts) == 3


def test_flag_stays_at_singles_level():
    records = EXAMPLE + [{"code": "B.1"}]
    items = rel_pairs(counting_flagged(records), records)
    assert "A.6|repeated" in items and "B.1|once" in items
    assert "A.6+C.2" in items and "A.6+B.1" in items   # pairs on plain codes


def test_groups_and_groups_only():
    records = [{"code": c} for c in ("X", "Y", "Z")]
    base = counting_unique(records)
    assert len(rel_groups(base, records)) == 3 + 3 + 1
    assert sorted(rel_groups_only(base, records)) == [
        "X+Y", "X+Y+Z", "X+Z", "Y+Z"
    ]


def test_signatures_one_instance():
    assert rel_signatures(counting_unique(EXAMPLE), EXAMPLE) == ["sig:A.6+C.2"]
    assert rel_signatures([], []) == []


def test_ordered_pairs_first_occurrence():
    records = [{"code": "B.6"}, {"code": "A.8"}, {"code": "B.6"}]
    items = rel_ordered_pairs(counting_unique(records), records)
    assert "B.6->A.8" in items and "A.8->B.6" not in items


# -------------------------------------------------------- formula (seg 6)
def entries(*pairs):
    return [{"item": item, "value": value} for item, value in pairs]


def test_group_order_conventions():
    assert group_order("A.6") == 1
    assert group_order("A.6|repeated") == 1
    assert group_order("A.6+C.2") == 2
    assert group_order("sig:A.6+C.2") == 1
    assert group_order("B.6->A.8") == 2


def test_heterogeneous_values_separate_formulas():
    e = entries(("A", 0.6), ("B", 0.4))
    assert merge_uncapped_sum(e) == 1.0
    assert abs(merge_noisy_or(e) - (1 - 0.4 * 0.6)) < 1e-12
    assert merge_max(e) == 0.6
    e2 = entries(("A", 0.3), ("B", 0.2))
    assert merge_capped_sum(e2) == 0.5


def test_unit_value_collapse_and_pie_telescoping():
    e = entries(("A", 1.0), ("B", 1.0), ("A+B", 1.0))
    assert merge_capped_sum(e) == merge_noisy_or(e) == merge_max(e) == 1.0
    assert merge_pie_signed(e) == 1.0                # 1 + 1 - 1
    full = entries(("X", 1), ("Y", 1), ("Z", 1),
                   ("X+Y", 1), ("X+Z", 1), ("Y+Z", 1), ("X+Y+Z", 1))
    assert merge_pie_signed(full) == 1.0             # telescopes
    truncated = entries(("X", 0.2), ("Y", 0.2), ("Z", 0.2),
                        ("X+Y", 0.5), ("X+Z", 0.5), ("Y+Z", 0.5))
    assert merge_pie_signed(truncated) == 0.0        # floored


# ------------------------------------------------------------- installers
def test_installers_register_reviewed_names():
    registry = Registry()
    install_counting_options(registry)
    install_relationship_options(registry)
    install_formula_options(registry)
    assert registry.names("counting") == ["flagged", "total", "unique"]
    assert registry.names("relationships") == [
        "groups", "groups_only", "none", "ordered_pairs", "pairs", "signatures"
    ]
    assert registry.names("formula") == [
        "capped_sum", "max", "noisy_or", "pie_signed"
    ]


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                fails += 1
                print(f"FAIL {name}: {exc}")
    raise SystemExit(fails)
