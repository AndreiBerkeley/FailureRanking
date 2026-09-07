#!/usr/bin/env python3
"""Trust option tests. Run: python3 -m core.test_trust"""

from core.trust_options import outcome_link_weight


def rec(code, link=None):
    r = {"code": code}
    if link is not None:
        r["outcome_link"] = link
    return r


def test_gate_any_record_of_code():
    records = [rec("A", "unlikely"), rec("A", "direct"), rec("B", "possible")]
    assert outcome_link_weight("A", records, mode="gate") == 1.0
    assert outcome_link_weight("B", records, mode="gate") == 0.0


def test_ordinal_best_per_code():
    records = [rec("A", "unlikely"), rec("A", "possible"), rec("B", "likely")]
    assert outcome_link_weight("A", records, mode="ordinal") == 0.5
    assert outcome_link_weight("B", records, mode="ordinal") == 0.75


def test_groups_take_min_of_members():
    records = [rec("A", "direct"), rec("B", "unlikely")]
    assert outcome_link_weight("A+B", records, mode="gate") == 0.0
    assert outcome_link_weight("A+B", records, mode="ordinal") == 0.25
    assert outcome_link_weight("A.6|repeated", [rec("A.6", "likely")], mode="ordinal") == 0.75


def test_missing_testimony_fully_trusted():
    records = [rec("A")]
    assert outcome_link_weight("A", records, mode="gate") == 1.0
    assert outcome_link_weight("A", records, mode="ordinal") == 1.0


def test_absent_code_zero():
    assert outcome_link_weight("Z", [rec("A", "direct")], mode="gate") == 0.0


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
