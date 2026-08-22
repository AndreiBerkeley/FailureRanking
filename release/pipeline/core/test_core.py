#!/usr/bin/env python3
"""Framework tests with an isolated registry and dummy options.
Run: python3 -m core.test_core   (from the repository root)"""

from __future__ import annotations

import tempfile
from pathlib import Path

from core.bench import (
    average_ranks,
    build_targets,
    compare,
    grade,
    kendall_tau_b,
    spearman_rho,
)
from core.grid import (
    Configuration,
    Dataset,
    enumerate_configurations,
    mask_ok,
    resolve,
    run_configuration,
    run_grid,
)
from core.segments import AXES, DEFAULT, RANKING_CONVENTION, Registry


# ---------------------------------------------------------------- fixtures
def make_registry() -> Registry:
    reg = Registry()
    reg.register(
        "counting", "modes",
        lambda records: sorted({r["code"] for r in records}),
    )
    reg.register(
        "relationships", "none",
        lambda base, records: list(base),
    )
    reg.register(
        "trust", "halve",
        lambda item, records: 0.5,
    )
    reg.register(
        "feedback", "needs_gold",
        lambda item, ctx: 1.0 if ctx["outcomes"] is None else 0.25,
        requires={"training_gold"},
    )
    reg.register(
        "formula", "sum",
        lambda entries, ctx=None: sum(e["value"] for e in entries),
    )
    return reg


def make_dataset(with_gold: bool = False) -> Dataset:
    evidence = {
        0: {"t1": [{"code": "A"}, {"code": "B"}], "t2": []},
        1: {"t1": [{"code": "A"}], "t2": [{"code": "A"}]},
    }
    outcomes = {0: {"t1": 0.0, "t2": 1.0}, 1: {"t1": 1.0, "t2": 1.0}}
    return Dataset(
        evidence=evidence,
        fingerprint="test-fp",
        outcomes=outcomes if with_gold else None,
    )


BASE_CONFIG = {"counting": "modes", "relationships": "none", "formula": "sum"}


# ------------------------------------------------------------------ tests
def test_default_registry_is_empty():
    assert DEFAULT.is_empty()
    assert list(enumerate_configurations(DEFAULT)) == []


def test_registry_rejects_unknown_axis_and_duplicates():
    reg = make_registry()
    try:
        reg.register("ranking", "x", lambda: None)
        raise AssertionError("unknown axis accepted")
    except ValueError:
        pass
    try:
        reg.register("counting", "modes", lambda records: [])
        raise AssertionError("duplicate accepted")
    except ValueError:
        pass


def test_configuration_requires_mandatory_axes():
    try:
        Configuration.from_mapping({"counting": "modes"})
        raise AssertionError("missing mandatory axes accepted")
    except ValueError:
        pass


def test_pipeline_composition_and_optional_defaults():
    reg = make_registry()
    config = Configuration.from_mapping(BASE_CONFIG)
    result = run_configuration(reg, config, make_dataset())
    assert result["status"] == "ok"
    assert result["scenario_1"] is False
    assert result["ranking"] == RANKING_CONVENTION
    # quality = 1 - burden per task, mean over tasks (higher is better).
    # candidate 0: t1 burden 2 -> quality -1; t2 burden 0 -> quality 1; mean 0
    assert result["scores"][0] == 0.0
    assert result["scores"][1] == 0.0


def test_trust_weight_applies():
    reg = make_registry()
    config = Configuration.from_mapping({**BASE_CONFIG, "trust": "halve"})
    result = run_configuration(reg, config, make_dataset())
    # candidate 0: t1 burden 1.0 -> quality 0; t2 -> 1; mean 0.5
    assert result["scores"][0] == 0.5


def test_mask_skips_gold_requirement_without_gold():
    reg = make_registry()
    config = Configuration.from_mapping({**BASE_CONFIG, "feedback": "needs_gold"})
    resolved = resolve(reg, config)
    ok, reason = mask_ok(resolved, make_dataset(with_gold=False))
    assert not ok and "training_gold" in reason
    result = run_configuration(reg, config, make_dataset(with_gold=False))
    assert result["status"] == "skipped"


def test_gold_marks_scenario_1_and_applies():
    reg = make_registry()
    config = Configuration.from_mapping({**BASE_CONFIG, "feedback": "needs_gold"})
    result = run_configuration(reg, config, make_dataset(with_gold=True))
    assert result["status"] == "ok"
    assert result["scenario_1"] is True
    # candidate 0: t1 burden 2*0.25=0.5 -> quality 0.5; t2 -> 1.0; mean 0.75
    assert result["scores"][0] == 0.75


def test_enumeration_counts_optional_skips():
    reg = make_registry()
    configs = list(enumerate_configurations(reg))
    # 1 counting x 1 relationships x (1+1) trust x (1+1) feedback x 1 formula
    assert len(configs) == 4


def test_grid_runs_and_caches():
    reg = make_registry()
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        first = run_grid(reg, make_dataset(with_gold=True), cache_dir=cache)
        ok_first = [r for r in first if r["status"] == "ok"]
        assert len(ok_first) == 4
        assert len(list(cache.glob("*.json"))) == 4
        second = run_grid(reg, make_dataset(with_gold=True), cache_dir=cache)
        ok_second = [r for r in second if r["status"] == "ok"]
        assert len(ok_second) == len(ok_first)
        for before, after in zip(ok_first, ok_second):
            assert sorted(before["scores"].values()) == sorted(
                after["scores"].values()
            )


def test_bench_metrics_known_values():
    assert kendall_tau_b([1, 2, 3], [1, 2, 3]) == 1.0
    assert kendall_tau_b([1, 2, 3], [3, 2, 1]) == -1.0
    assert spearman_rho([1, 2, 3], [1, 2, 3]) == 1.0
    assert average_ranks([10, 20, 30]) == [3.0, 2.0, 1.0]
    scores = {0: 0.8, 1: 0.2}
    target = {0: 0.9, 1: 0.1}
    metrics = compare(scores, target)
    assert metrics["kendall_tau_b"] == 1.0
    assert metrics["tie_aware_top1_hit"] == 1.0


def test_grade_attaches_evaluation():
    gold = {
        0: {"s": {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}, "d": {0: 1.0}},
        1: {"s": {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}, "d": {0: 0.0}},
    }
    targets = build_targets(gold, shared_tasks=["s"], disjoint_tasks=["d"])
    results = [
        {"status": "ok", "scores": {0: 0.9, 1: 0.1}, "config": {}},
        {"status": "skipped", "reason": "x", "config": {}},
    ]
    graded = grade(results, targets)
    assert graded[0]["evaluation"]["cross_seed"]["kendall_tau_b"] == 1.0
    assert "evaluation" not in graded[1]


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
