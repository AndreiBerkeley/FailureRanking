#!/usr/bin/env python3
"""Unit tests for recovery_graph.py (SPEC.md rules). Run: python3 test_recovery_graph.py"""

from recovery_graph import analyze, task_mode_recovery


def occ(*pairs):
    return [{"id": i, "step": s} for i, s in pairs]


def test_chain_persists():
    r = analyze(occ(("F1", 2), ("F2", 5)),
                [{"src": "F1", "dst": "F2", "label": "follow_up"},
                 {"src": "F2", "dst": "OUTPUT", "label": "follow_up"}])
    assert r["F1"]["status"] == "persisted" and r["F1"]["position"] == "root"
    assert r["F1"]["sigma"] == 1.0
    assert r["F2"]["status"] == "persisted" and r["F2"]["position"] == "leaf"
    assert r["F2"]["sigma"] == 0.0


def test_correction_before_consumption_recovers():
    r = analyze(occ(("F1", 2), ("F2", 7)),
                [{"src": "F1", "dst": "F2", "label": "follow_up"},        # consumed at 7
                 {"src": "F1", "dst": "F2", "label": "correction",
                  "consume_step": 5},                                     # fixed at 5 < 7
                 {"src": "F2", "dst": "OUTPUT", "label": "follow_up"}])
    assert r["F1"]["status"] == "recovered"
    assert r["F2"]["status"] == "persisted" and r["F2"]["position"] == "isolated"


def test_correction_after_consumption_persists():
    r = analyze(occ(("F1", 2), ("F2", 3), ("C", 5)),
                [{"src": "F1", "dst": "F2", "label": "follow_up"},        # consumed at 3
                 {"src": "F1", "dst": "C", "label": "correction"},        # fixed at 5 > 3
                 {"src": "F2", "dst": "OUTPUT", "label": "follow_up"},
                 {"src": "C", "dst": "OUTPUT", "label": "no_influence"}])
    assert r["F1"]["status"] == "persisted"
    assert r["F2"]["status"] == "persisted"


def test_dead_end_recovers():
    r = analyze(occ(("F1", 2), ("X", 4)),
                [{"src": "F1", "dst": "X", "label": "dead_end"},
                 {"src": "X", "dst": "OUTPUT", "label": "no_influence"}])
    assert r["F1"]["status"] == "recovered"
    assert r["X"]["status"] == "recovered"


def test_unlinked_policy():
    occs = occ(("F1", 2))
    assert analyze(occs, [])["F1"]["status"] == "persisted"       # default
    assert analyze(occs, [], default_when_unlinked="recovered")[
        "F1"]["status"] == "recovered"
    assert analyze(occs, [])["_summary"]["unlinked"] == 1


def test_redundancy_does_not_propagate():
    r = analyze(occ(("F1", 2), ("F2", 5)),
                [{"src": "F1", "dst": "F2", "label": "redundancy"},
                 {"src": "F2", "dst": "OUTPUT", "label": "follow_up"}])
    assert r["F1"]["status"] == "recovered"
    assert r["F2"]["status"] == "persisted"


def test_error_shift_propagates():
    r = analyze(occ(("F1", 2), ("F2", 5)),
                [{"src": "F1", "dst": "F2", "label": "error_shift"},
                 {"src": "F2", "dst": "OUTPUT", "label": "follow_up"}])
    assert r["F1"]["status"] == "persisted"


def test_middle_sigma():
    r = analyze(occ(("F1", 1), ("F2", 3), ("F3", 5)),
                [{"src": "F1", "dst": "F2", "label": "follow_up"},
                 {"src": "F2", "dst": "F3", "label": "follow_up"},
                 {"src": "F3", "dst": "OUTPUT", "label": "follow_up"}])
    assert r["F2"]["position"] == "middle" and abs(r["F2"]["sigma"] - 0.5) < 1e-12
    assert r["F1"]["sigma"] == 1.0 and r["F3"]["sigma"] == 0.0


def test_mode_mapping():
    r = analyze(occ(("F1", 2), ("F2", 4), ("F3", 6)),
                [{"src": "F1", "dst": "F2", "label": "correction",
                  "consume_step": 3},
                 {"src": "F2", "dst": "OUTPUT", "label": "dead_end"},
                 {"src": "F3", "dst": "OUTPUT", "label": "follow_up"}])
    modes = task_mode_recovery({"F1": "B.10", "F2": "B.10", "F3": "B.14"}, r)
    assert modes["B.10"] == "fully_recovered"      # both occurrences recovered
    assert modes["B.14"] == "unrecovered"


def test_step_ordering_enforced():
    try:
        analyze(occ(("F1", 5), ("F2", 2)),
                [{"src": "F1", "dst": "F2", "label": "follow_up"}])
    except ValueError:
        pass
    else:
        raise AssertionError("backward edge accepted")


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
    raise SystemExit(fails)
