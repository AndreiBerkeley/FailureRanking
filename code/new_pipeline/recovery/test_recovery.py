"""Deterministic core of the recovery pass: quote location, chronology, the verdict rule.

    python3 -m pytest new_pipeline/recovery/test_recovery.py -q
"""
from new_pipeline.recovery import recovery as R

TURN = {1: {"instr": "", "input": "claim: X", "output": "the summary says Randy is a songwriter"},
        2: {"instr": "", "input": "summary_1: the summary says Randy is a songwriter", "output": "query: Randy Fuller songwriter"},
        3: {"instr": "", "input": "context: nothing", "output": "final summary without Randy"}}
OUT = "FINAL OUTPUT: Randy Fuller (musician) | Randall Randy Fuller is an American rock singer, songwriter"
P1 = {"turn": 1, "agent": "summarize1", "evidence": "the summary says Randy is a songwriter", "problem": "unlicensed"}


def entry(effect_q="the summary says Randy is a songwriter", consumed=(), events=(), eio=False, quote="", cost=None, cost_q=""):
    return {"index": 0, "effect": {"quote": effect_q, "what": "x"},
            "consumed": list(consumed), "events": list(events),
            "output": {"effect_in_output": eio, "quote": quote, "cost_supplied": cost, "cost_quote": cost_q, "why": "w"}}


def test_locate_exact_fuzzy_unverified():
    assert R.locate("Randy is a songwriter", TURN[1]["output"]) == "exact"
    assert R.locate("the summary  says Randy is a  songwriter", TURN[1]["output"]) == "exact"     # whitespace
    assert R.locate("the summary says Randy is a songwritr", TURN[1]["output"]) == "fuzzy"      # one char off
    assert R.locate("something entirely different here", TURN[1]["output"]) == "unverified"
    assert R.locate("short", "short") == "unverified"                                          # below MIN_QUOTE


def test_effect_in_output_is_unrecovered():
    k = R.check_point(entry(eio=True, quote="Randy Fuller is an American rock singer"), P1, TURN, OUT)
    assert R.verdict(k) == "unrecovered"


def test_effect_absent_no_consumer_is_contained():
    k = R.check_point(entry(eio=False), P1, TURN, OUT)
    assert k["consumed"] == [] and R.verdict(k) == "contained"


def test_effect_absent_consumed_no_correction_is_made_irrelevant():
    k = R.check_point(entry(consumed=[{"turn": 2, "quote": "the summary says Randy is a songwriter"}], eio=False), P1, TURN, OUT)
    assert len(k["consumed"]) == 1 and R.verdict(k) == "made_irrelevant"


def test_correction_event_is_corrected():
    ev = [{"kind": "correction", "turn": 3, "quote": "final summary without Randy", "why": "re-derived"}]
    k = R.check_point(entry(consumed=[{"turn": 2, "quote": "the summary says Randy is a songwriter"}], events=ev, eio=False), P1, TURN, OUT)
    assert R.verdict(k) == "corrected"


def test_chronology_drops_events_before_or_at_the_point():
    ev = [{"kind": "correction", "turn": 1, "quote": "the summary says Randy is a songwriter", "why": "same turn"}]
    k = R.check_point(entry(events=ev, eio=False), P1, TURN, OUT)
    assert k["events"] == [] and any(d["field"] == "events" for d in k["dropped"])
    assert R.verdict(k) == "contained"          # recovered by the output test, but not 'corrected'


def test_unverifiable_quote_is_dropped_not_trusted():
    ev = [{"kind": "correction", "turn": 3, "quote": "this text is nowhere in the trace at all", "why": ""}]
    k = R.check_point(entry(events=ev, eio=False), P1, TURN, OUT)
    assert k["events"] == [] and R.verdict(k) == "contained"


def test_cost_missing_beats_everything():
    k = R.check_point(entry(eio=False, cost=False), P1, TURN, OUT)
    assert R.verdict(k) == "unrecovered"


def test_cost_supplied_with_quote_is_recovered_even_if_effect_visible():
    k = R.check_point(entry(eio=True, quote="Randy Fuller is an American rock singer", cost=True,
                            cost_q="Randall Randy Fuller is an American rock singer, songwriter"), P1, TURN, OUT)
    assert k["output"]["cost_supplied"] is True and R.verdict(k) == "contained"


def test_cost_supplied_without_verifiable_quote_falls_back_to_effect():
    k = R.check_point(entry(eio=False, cost=True, cost_q="not in the output anywhere, honestly"), P1, TURN, OUT)
    assert k["output"]["cost_supplied"] is None and R.verdict(k) == "contained"      # effect absent -> still recovered
    k = R.check_point(entry(eio=True, quote="Randy Fuller is an American rock singer", cost=True, cost_q="nowhere in the output at all"), P1, TURN, OUT)
    assert R.verdict(k) == "unrecovered"                                              # effect present, no valid cost claim


def test_unassessable_only_when_nothing_else():
    assert R.verdict(R.check_point(entry(eio="unassessable"), P1, TURN, OUT)) == "unassessable"
    assert R.verdict(R.check_point(entry(eio="unassessable", cost=False), P1, TURN, OUT)) == "unrecovered"


def test_answer_shape():
    assert R.answer_ok({"points": [entry()]}, 1) is None
    assert "no entry" in R.answer_ok({"points": []}, 1)
    bad = entry(); bad["output"]["effect_in_output"] = "maybe"
    assert "true, false" in R.answer_ok({"points": [bad]}, 1)
