#!/usr/bin/env python3
"""End-to-end tests for the portable mapping and the one-command pipeline.
Run: python3 -m core.test_run   (from the repository root)"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core.mapping import (
    load_mapping,
    mapping_to_dataset,
    save_mapping,
    validate_mapping,
)
from core.run import build_ranking, run_pipeline

TOY = {
    "schema_version": 1,
    "benchmark": "toy",
    "candidates": {
        "alpha": {
            "t1": [{"code": "X"}, {"code": "Y", "note": "extra kept"}],
            "t2": [],
        },
        "beta": {
            "t1": [{"code": "X"}],
            "t2": [{"code": "X"}, {"code": "Y"}, {"code": "Z"}],
        },
    },
}


def test_validate_rejects_bad_mappings():
    for broken in (
        {"schema_version": 2, "candidates": {"a": {"t": []}}},
        {"schema_version": 1, "candidates": {}},
        {"schema_version": 1, "candidates": {"a": {"t": [{"note": "no code"}]}}},
    ):
        try:
            validate_mapping(broken)
            raise AssertionError(f"accepted: {broken}")
        except ValueError:
            pass


def test_mapping_round_trip_and_dataset():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "m.json"
        save_mapping(TOY, path)
        loaded = load_mapping(path)
    assert loaded == TOY
    dataset = mapping_to_dataset(loaded)
    assert dataset.outcomes is None
    assert set(dataset.evidence) == {"alpha", "beta"}
    # extras carried through untouched
    assert dataset.evidence["alpha"]["t1"][1]["note"] == "extra kept"


def test_pipeline_end_to_end_default_config():
    output = run_pipeline(TOY)
    assert output["scenario_1"] is False
    assert output["ranking_convention"]["direction"] == "higher_is_better"
    # default path = unique modes, flat unit, uncapped sum; quality = 1 - k_t
    # alpha: t1 k=2 -> -1, t2 k=0 -> 1  => mean 0.0
    # beta:  t1 k=1 ->  0, t2 k=3 -> -2 => mean -1.0
    assert output["scores"]["alpha"] == 0.0
    assert output["scores"]["beta"] == -1.0
    assert output["ranking"][0]["candidate"] == "alpha"
    assert output["ranking"][0]["rank"] == 1.0


def test_ranking_ties_share_average_rank():
    rows = build_ranking({"a": 0.5, "b": 0.5, "c": 0.1})
    assert rows[0]["rank"] == 1.5 and rows[1]["rank"] == 1.5
    assert rows[2]["candidate"] == "c" and rows[2]["rank"] == 3.0


def test_unknown_config_option_fails_clearly():
    from core.grid import Configuration

    config = Configuration.from_mapping(
        {"counting": "nope", "relationships": "none",
         "formula": "uncapped_sum"}
    )
    try:
        run_pipeline(TOY, configuration=config)
        raise AssertionError("unknown option accepted")
    except KeyError as exc:
        assert "nope" in str(exc)


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
