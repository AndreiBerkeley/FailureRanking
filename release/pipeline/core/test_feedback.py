#!/usr/bin/env python3
"""Tests for the gold success-discount feedback option.
Run: python3 -m core.test_feedback"""

from __future__ import annotations

from core.feedback_options import SurvivalDiscount, task_contains, task_recovered
from core.grid import Configuration, Dataset, run_configuration
from core.run import build_registry, run_pipeline
from core.test_run import TOY


def recs(*codes):
    return [{"code": c} for c in codes]


# ------------------------------------------------------------- containment
def test_containment_conventions():
    records = recs("A.6", "C.2", "A.6")
    assert task_contains(records, "A.6")
    assert task_contains(records, "A.6|repeated")
    assert not task_contains(records, "A.6|once")
    assert task_contains(records, "C.2|once")
    assert task_contains(records, "A.6+C.2")
    assert not task_contains(records, "A.6+B.1")
    assert task_contains(records, "sig:A.6+C.2")
    assert not task_contains(records, "sig:A.6")
    assert task_contains(records, "A.6->C.2")
    assert not task_contains(records, "C.2->A.6")


# ---------------------------------------------------------------- discount
def make_context(pairs):
    """pairs: list of (codes, outcome). 20 tasks for a tau of 3."""

    tasks = {f"t{i:02d}": recs(*codes) for i, (codes, _) in enumerate(pairs)}
    outcomes = {f"t{i:02d}": out for i, (_, out) in enumerate(pairs)}
    return {"tasks": tasks, "outcomes": outcomes}


def test_discount_formula_and_convexity():
    option = SurvivalDiscount("gold")
    # X on 10 tasks, 1 success; padding tasks keep N=20 (tau=3 by rule)
    pairs = [(["X"], 1.0)] + [(["X"], 0.0)] * 9 + [([], 1.0)] * 10
    ctx = make_context(pairs)
    ctx["feedback_state"] = option.prepare(ctx)
    assert ctx["feedback_state"]["tau"] == 3          # max(ceil(0.05*20), 3)
    influence = option("X", ctx)
    assert abs(influence - (1 - 0.1 ** 2)) < 1e-12    # 0.99: barely dented


def test_support_gate_backoff_to_base_rate():
    option = SurvivalDiscount("gold")
    # Y appears on only 2 tasks (< tau=3): backoff = base failure rate
    pairs = [(["Y"], 0.0)] * 2 + [([], 1.0)] * 18
    ctx = make_context(pairs)
    ctx["feedback_state"] = option.prepare(ctx)
    assert abs(option("Y", ctx) - (1.0 - 18 / 20)) < 1e-12


def test_all_failures_full_influence():
    option = SurvivalDiscount("gold")
    pairs = [(["Z"], 0.0)] * 5 + [([], 1.0)] * 15
    ctx = make_context(pairs)
    ctx["feedback_state"] = option.prepare(ctx)
    assert option("Z", ctx) == 1.0


# ------------------------------------------------------------- end to end
TOY_GOLD = {"alpha": {"t1": 1.0, "t2": 1.0}, "beta": {"t1": 0.0, "t2": 0.0}}


def test_pipeline_scenario_1_marked_and_applied():
    output = run_pipeline(
        TOY,
        configuration=Configuration.from_mapping(
            {"counting": "unique", "relationships": "none",
             "feedback": "gold_convex", "formula": "max"}
        ),
        training_outcomes=TOY_GOLD,
    )
    assert output["scenario_1"] is True
    # alpha survives everything -> all influences backoff to base failure 0
    assert output["scores"]["alpha"] == 1.0
    # beta fails everything -> backoff = base failure 1.0 on both tasks
    assert output["scores"]["beta"] == 0.0


def test_mask_blocks_without_gold():
    registry = build_registry()
    config = Configuration.from_mapping(
        {"counting": "unique", "relationships": "none",
         "feedback": "gold_convex", "formula": "max"}
    )
    from core.mapping import mapping_to_dataset

    result = run_configuration(registry, config, mapping_to_dataset(TOY))
    assert result["status"] == "skipped"
    assert "training_gold" in result["reason"]




# ------------------------------------------------------- recovery section
def rrecs(*pairs):
    return [{"code": c, "recovery_status": s} for c, s in pairs]


def test_task_recovered_predicate():
    records = rrecs(("A", "fully_recovered"), ("A", "unrecovered"), ("B", "made_irrelevant"))
    assert not task_recovered(records, "A")        # one occurrence unrecovered
    assert task_recovered(records, "B")
    assert not task_recovered(records, "A+B")      # A drags the pair down
    assert not task_recovered(records, "C")        # absent -> not recovered


def test_recovery_discount_gold_free():
    option = SurvivalDiscount("recovery")
    tasks = {f"t{i}": rrecs(("X", "fully_recovered")) for i in range(3)}
    tasks.update({f"u{i}": rrecs(("X", "unrecovered")) for i in range(3)})
    tasks.update({f"v{i}": [] for i in range(14)})
    ctx = {"tasks": tasks, "outcomes": None}
    ctx["feedback_state"] = option.prepare(ctx)
    # X on 6 tasks, 3 recovered -> influence = 1 - 0.5^2 = 0.75
    assert abs(option("X", ctx) - 0.75) < 1e-12
    # unsupported item -> recovery backoff is full influence
    assert option("Z", ctx) == 1.0


# --------------------------------------------- shrinkage and fused shapes
def test_shrunk_gold_pulls_thin_evidence_to_prior():
    from core.feedback_options import ShrunkGold
    option = ShrunkGold()
    # base rate 0.5 over 20 tasks; X on 2 tasks, both survived
    pairs = [(["X"], 1.0)] * 2 + [([], 1.0)] * 8 + [([], 0.0)] * 10
    ctx = make_context(pairs)
    ctx["feedback_state"] = option.prepare(ctx)
    # shrunk = (2 + 4*0.5) / (2 + 4) = 4/6; influence = 1 - 4/6 = 1/3
    assert abs(option("X", ctx) - (1 - 4/6)) < 1e-12
    # well-supported all-fail pattern barely shrinks: (0+2)/(10+4) = 1/7
    pairs2 = [(["Y"], 0.0)] * 10 + [([], 1.0)] * 10
    ctx2 = make_context(pairs2)
    ctx2["feedback_state"] = option.prepare(ctx2)
    assert abs(option("Y", ctx2) - (1 - 2/14)) < 1e-12


def test_fused_gold_blames_by_outcome_link():
    from core.feedback_options import FusedGold
    option = FusedGold()
    # X appears on 4 failed tasks rated unlikely (w=0.25) and 2 succeeded
    tasks, outcomes = {}, {}
    for i in range(4):
        tasks[f"f{i}"] = [{"code": "X", "outcome_link": "unlikely"}]
        outcomes[f"f{i}"] = 0.0
    for i in range(2):
        tasks[f"s{i}"] = [{"code": "X"}]
        outcomes[f"s{i}"] = 1.0
    for i in range(14):
        tasks[f"p{i}"] = []
        outcomes[f"p{i}"] = 1.0
    ctx = {"tasks": tasks, "outcomes": outcomes}
    ctx["feedback_state"] = option.prepare(ctx)
    # survivals 2, blamed 4*0.25=1 -> survival 2/3 -> influence 1/3
    assert abs(option("X", ctx) - (1 - 2/3)) < 1e-12
    # same appearances rated direct -> blamed 4 -> survival 1/3 -> 2/3
    for i in range(4):
        tasks[f"f{i}"] = [{"code": "X", "outcome_link": "direct"}]
    ctx2 = {"tasks": tasks, "outcomes": outcomes}
    ctx2["feedback_state"] = option.prepare(ctx2)
    assert abs(option("X", ctx2) - (1 - 1/3)) < 1e-12


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
