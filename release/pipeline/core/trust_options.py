"""Segment 4 — trust options: the judge's outcome_link testimony
(reviewed 2026-08-18).

`outcome_link` is the judge's own per-failure-point statement of whether
the claimed failure plausibly reached the final output: direct / likely /
possible / unlikely / none. It rides in the mapping extras and was
written trace-side, without gold — trust options stay gold-free.

  ol_gate_likely   weight 1 if trusted, else 0: a code is trusted on a
                   task when at least one of its records there is rated
                   direct or likely ("only count failures the judge
                   believes mattered"). The pre-framework measurement of
                   this gate: +0.851 / +0.731, the project champion.
  ol_ordinal       graded weight instead of a cut: per code, the best of
                   its records' ratings mapped direct=1.0, likely=0.75,
                   possible=0.5, unlikely=0.25, none=0.0.
                   Pre-framework: +0.782 / +0.678.

Group/signature/ordered instances take the MINIMUM of their member
codes' weights — a relationship is only as trustworthy as its least
trusted member. Records without an outcome_link field count as fully
trusted (missing testimony is not evidence of irrelevance).

Excluded by review (tested, harmful): verified-span gate,
judge-confidence gate, mapping-confidence threshold gates, hard
deletion by recovery labels.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .feedback_options import item_codes
from .segments import Registry

OUTCOME_LINK_TAG = "outcome_link"

ORDINAL = {
    "direct": 1.0,
    "likely": 0.75,
    "possible": 0.5,
    "unlikely": 0.25,
    "none": 0.0,
}


def _code_weight(
    records: Sequence[Mapping[str, Any]], code: str, mode: str
) -> float:
    """Best outcome-link weight among the code's records on this task."""

    best = None
    for record in records:
        if str(record["code"]) != code:
            continue
        link = record.get("outcome_link")
        if link is None:
            value = 1.0                     # missing testimony: fully trusted
        elif mode == "gate":
            value = 1.0 if str(link) in ("direct", "likely") else 0.0
        else:
            value = ORDINAL.get(str(link), 1.0)
        best = value if best is None else max(best, value)
    return 0.0 if best is None else best


def outcome_link_weight(
    item: Any,
    records: Sequence[Mapping[str, Any]],
    mode: str = "gate",
) -> float:
    weights = [_code_weight(records, code, mode) for code in item_codes(item)]
    return min(weights) if weights else 0.0


def install_trust_options(registry: Registry) -> None:
    registry.register(
        "trust", "ol_gate_likely", outcome_link_weight,
        requires={OUTCOME_LINK_TAG}, params={"mode": "gate"},
        description="keep only failures the judge rated direct/likely to "
                    "have reached the output",
    )
    registry.register(
        "trust", "ol_ordinal", outcome_link_weight,
        requires={OUTCOME_LINK_TAG}, params={"mode": "ordinal"},
        description="graded weight by the judge's outcome-link rating",
    )
