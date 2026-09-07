"""Segment 5 — feedback: two sections, gold and recovery (2026-08-18).

Both sections answer the same candidate-local question — "when this
pattern appears, does this candidate survive it?" — and differ only in
what counts as survival:

  gold section       survival = the task nevertheless succeeded
                     (training outcomes; requires gold, marks scenario 1)
  recovery section   survival = the pattern's failure records were
                     recovered (recovery labels carried in the mapping
                     extras; gold-free — the scenario-2 mirror)

Each section offers influence shapes — how survival discounts the
pattern's influence:

  linear   influence = 1 - survival_share          (uniform discount)
  convex   influence = 1 - survival_share ** 2     (one survival in ten
           is worth almost nothing; each further survival removes more —
           the validated Top-1 shape, gamma = 2 provisional)

Registered: gold_linear, gold_convex, recovery_linear, recovery_convex.
The shape family is open (harsher powers, shrinkage) pending review.

Candidate-locality is a section-wide invariant: pooled/global variants
failed structurally and are not registered. Support gate: instances seen
on fewer than tau = max(ceil(0.05 N), 3) of the candidate's tasks fall
back to the candidate's base failure rate (gold section) or full
influence 1.0 (recovery section, which has no outcome prior). Item-level
backoff is the documented refinement over the v1 trial's task-level
backoff; gold_convex reproduces v1's Top-1 property, not its exact bits.

Containment is derived from the instance id conventions, independent of
the counting/relationships choices:

  "A.6" contains the code · "A.6|once" exactly once · "A.6|repeated"
  two-plus · "A.6+C.2" all members · "sig:..." exact set ·
  "B.6->A.8" both present, B.6 first.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping, Sequence

from .grid import GOLD_TAG
from .segments import Registry

RECOVERY_TAG = "recovery_labels"
RECOVERED_STATUSES = {"fully_recovered", "made_irrelevant"}


def _first_index(records: Sequence[Mapping[str, Any]], code: str) -> int | None:
    for index, record in enumerate(records):
        if str(record["code"]) == code:
            return index
    return None


def item_codes(item: Any) -> list[str]:
    label = str(item)
    if label.startswith("sig:"):
        return label[4:].split("+")
    if "->" in label:
        return label.split("->", 1)
    if "|" in label:
        return [label.split("|", 1)[0]]
    return label.split("+")


def task_contains(records: Sequence[Mapping[str, Any]], item: Any) -> bool:
    label = str(item)
    counts = Counter(str(r["code"]) for r in records)
    if label.startswith("sig:"):
        return sorted(counts) == sorted(label[4:].split("+"))
    if "->" in label:
        earlier, later = label.split("->", 1)
        a, b = _first_index(records, earlier), _first_index(records, later)
        return a is not None and b is not None and a < b
    if "|" in label:
        code, flag = label.split("|", 1)
        if flag == "repeated":
            return counts.get(code, 0) >= 2
        return counts.get(code, 0) == 1
    if "+" in label:
        return all(counts.get(code, 0) >= 1 for code in label.split("+"))
    return counts.get(label, 0) >= 1


def task_recovered(records: Sequence[Mapping[str, Any]], item: Any) -> bool:
    """Survival in the recovery sense: every record of the item's member
    codes on this task carries a recovered-class label."""

    member = set(item_codes(item))
    relevant = [r for r in records if str(r["code"]) in member]
    if not relevant:
        return False
    return all(
        str(r.get("recovery_status", "")) in RECOVERED_STATUSES for r in relevant
    )


class SurvivalDiscount:
    """Candidate-local discount engine shared by both sections."""

    def __init__(self, signal: str) -> None:
        if signal not in ("gold", "recovery"):
            raise ValueError(f"unknown signal {signal!r}")
        self.signal = signal

    def prepare(
        self,
        candidate_context: Mapping[str, Any],
        gamma: float = 2.0,
        tau: int | None = None,
    ) -> dict[str, Any]:
        tasks = candidate_context["tasks"]
        if self.signal == "gold":
            outcomes = candidate_context["outcomes"]
            if outcomes is None:
                raise ValueError("gold section requires training outcomes")
            scored = [
                (tasks[task], float(outcomes[task]))
                for task in tasks
                if task in outcomes
            ]
            successes = sum(outcome for _, outcome in scored)
            backoff = 1.0 - successes / len(scored) if scored else 1.0
        else:
            scored = [(records, None) for records in tasks.values()]
            backoff = 1.0
        n_tasks = len(scored)
        return {
            "scored": scored,
            "tau": tau if tau is not None else max(math.ceil(0.05 * n_tasks), 3),
            "backoff": backoff,
            "memo": {},
        }

    def __call__(
        self,
        item: Any,
        candidate_context: Mapping[str, Any],
        gamma: float = 2.0,
        tau: int | None = None,
    ) -> float:
        state = candidate_context["feedback_state"]
        key = str(item)
        if key in state["memo"]:
            return state["memo"][key]
        appearances = survivals = 0
        for records, outcome in state["scored"]:
            if not task_contains(records, item):
                continue
            appearances += 1
            if self.signal == "gold":
                survivals += outcome
            elif task_recovered(records, item):
                survivals += 1
        if appearances < state["tau"]:
            influence = state["backoff"]
        else:
            influence = 1.0 - (survivals / appearances) ** gamma
        state["memo"][key] = influence
        return influence


class ShrunkGold:
    """Gold section, shrinkage shape (2026-08-19): survival rates are
    pulled toward the candidate's base success rate in proportion to
    their uncertainty — thin evidence shrinks hard, solid evidence
    barely moves. Replaces the hard tau gate entirely: no support
    threshold, no cliff, and small-sample flattery (the candidate-4
    import) is damped at the estimator level.

        shrunk = (survivals + K * base_rate) / (appearances + K)
        influence = 1 - shrunk ** gamma

    K (prior pseudo-observations) provisional at 4; gamma provisional
    at 1 (the winning linear shape)."""

    def prepare(self, candidate_context, gamma=1.0, prior_strength=4.0):
        tasks = candidate_context["tasks"]
        outcomes = candidate_context["outcomes"]
        if outcomes is None:
            raise ValueError("gold section requires training outcomes")
        scored = [
            (tasks[task], float(outcomes[task]))
            for task in tasks if task in outcomes
        ]
        base = sum(o for _, o in scored) / len(scored) if scored else 0.0
        return {"scored": scored, "base": base, "memo": {}}

    def __call__(self, item, candidate_context, gamma=1.0, prior_strength=4.0):
        state = candidate_context["feedback_state"]
        key = str(item)
        if key in state["memo"]:
            return state["memo"][key]
        appearances = survivals = 0.0
        for records, outcome in state["scored"]:
            if task_contains(records, item):
                appearances += 1
                survivals += outcome
        shrunk = (survivals + prior_strength * state["base"]) / (
            appearances + prior_strength
        )
        influence = 1.0 - shrunk ** gamma
        state["memo"][key] = influence
        return influence


class FusedGold:
    """Gold section, fused shape (2026-08-19): outcome_link decides who
    takes the blame. On a FAILED task, an appearance counts as harmful
    evidence only in proportion to its outcome-link weight (the judge's
    culprit testimony); on a SUCCEEDED task, an appearance is full
    survival evidence regardless (the outcome already proved
    harmlessness).

        survival = survivals / (survivals + blamed_appearances)
        influence = 1 - survival ** gamma

    Support gate and backoff as in the plain gold shapes. Requires both
    training gold and outcome_link."""

    def prepare(self, candidate_context, gamma=1.0, tau=None):
        tasks = candidate_context["tasks"]
        outcomes = candidate_context["outcomes"]
        if outcomes is None:
            raise ValueError("gold section requires training outcomes")
        scored = [
            (tasks[task], float(outcomes[task]))
            for task in tasks if task in outcomes
        ]
        n_tasks = len(scored)
        base_failure = 1.0 - (
            sum(o for _, o in scored) / n_tasks if n_tasks else 0.0
        )
        return {
            "scored": scored,
            "tau": tau if tau is not None else max(math.ceil(0.05 * n_tasks), 3),
            "backoff": base_failure,
            "memo": {},
        }

    def __call__(self, item, candidate_context, gamma=1.0, tau=None):
        from .trust_options import outcome_link_weight

        state = candidate_context["feedback_state"]
        key = str(item)
        if key in state["memo"]:
            return state["memo"][key]
        raw_appearances = 0
        survivals = blamed = 0.0
        for records, outcome in state["scored"]:
            if not task_contains(records, item):
                continue
            raw_appearances += 1
            if outcome >= 1.0:
                survivals += 1.0
            else:
                blamed += outcome_link_weight(item, records, mode="ordinal")
        if raw_appearances < state["tau"]:
            influence = state["backoff"]
        else:
            denominator = survivals + blamed
            survival_rate = survivals / denominator if denominator else 1.0
            influence = 1.0 - survival_rate ** gamma
        state["memo"][key] = influence
        return influence


def install_feedback_options(registry: Registry) -> None:
    gold = SurvivalDiscount("gold")
    recovery = SurvivalDiscount("recovery")
    registry.register(
        "feedback", "gold_linear", gold,
        requires={GOLD_TAG}, params={"gamma": 1.0, "tau": None},
        description="gold section, uniform discount 1 - s/n",
    )
    registry.register(
        "feedback", "gold_convex", gold,
        requires={GOLD_TAG}, params={"gamma": 2.0, "tau": None},
        description="gold section, convex discount 1-(s/n)^2 (the Top-1 shape)",
    )
    registry.register(
        "feedback", "gold_shrunk", ShrunkGold(),
        requires={GOLD_TAG}, params={"gamma": 1.0, "prior_strength": 4.0},
        description="gold section, shrinkage toward the candidate base rate "
                    "(no support cliff; damps small-sample flattery)",
    )
    registry.register(
        "feedback", "gold_fused", FusedGold(),
        requires={GOLD_TAG, "outcome_link"}, params={"gamma": 1.0, "tau": None},
        description="gold section fused with outcome_link: blame on failed "
                    "tasks goes to the judge-identified culprits",
    )
    registry.register(
        "feedback", "recovery_linear", recovery,
        requires={RECOVERY_TAG}, params={"gamma": 1.0, "tau": None},
        description="recovery section, uniform discount by recovered share",
    )
    registry.register(
        "feedback", "recovery_convex", recovery,
        requires={RECOVERY_TAG}, params={"gamma": 2.0, "tau": None},
        description="recovery section, convex discount (scenario-2 mirror)",
    )
