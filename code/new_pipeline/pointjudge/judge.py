#!/usr/bin/env python3
"""Two readers, two passes each, one decider.

The unit of measurement is a FAILURE POINT: a step plus the evidence that shows
the mistake. Two findings are the same point only when their evidence agrees, so
one step can carry several points, including several of the same kind.

    reader A  pass 1  reads WITH the taxonomy      -> points
              pass 2  assigns modes to its points  -> modes
    reader B  pass 1  reads WITHOUT the taxonomy   -> points
              pass 2  assigns modes to its points  -> modes
    decider           reads the full trace + both  -> validated, merged points

Pass 1 produces points only, and the list is frozen before pass 2 runs. That is
what makes an unfittable point visible: a reader naming points and modes in one
breath drops silently whatever the vocabulary does not cover, and that dropped
thing is the coverage measurement.

Both readers may answer that nothing fits, and so may the decider. The taxonomy
is a description of what failures look like here, not a checklist.

There is no discussion round. Deciding whether two spans describe the same thing
is settled once by the decider holding both lists and the trace, rather than
twice by negotiation; model readers in discussion converge by capitulation, so
the consensus a round produces is not evidence that they agreed.

Design and open questions: judges/proposed/two-reader-decider.md
"""
from __future__ import annotations

import json
import re
from collections import Counter

from new_pipeline.pointjudge import prompts

# A fitness at or above this is an assignment; below it the point is recorded as
# uncovered and never scored. Same threshold the panel judge uses, kept so the
# two instruments' coverage numbers mean the same thing.
FIT_GOOD = 80


# ------------------------------------------------------------------ rendering
def render_taxonomy(taxonomy: dict) -> str:
    lines = []
    for c in taxonomy["codes"]:
        lines.append(f"[{c['id']}] {c.get('name', '')}")
        d = c.get("description") or c.get("definition") or ""
        lines.append(f"    definition: {d}")
        if c.get("when_to_use"):
            lines.append(f"    use when: {c['when_to_use']}")
        if c.get("when_not_to_use"):
            lines.append(f"    do not use when: {c['when_not_to_use']}")
        if c.get("applies_to_role"):
            lines.append(f"    role: {c['applies_to_role']}")
        lines.append("")
    return "\n".join(lines)


def render_turns(trace: dict, agents=None):
    """Delineated agent turns. Never elided: a cut trace loses turns, and a
    reader then reports that the agent produced nothing."""
    from new_pipeline.generation.render import render_turns as _rt
    return _rt(trace, agents)


def render_points(points: list) -> str:
    """The numbered listing a reader's own points are shown back to it as, and
    the listing the decider sees for each reader."""
    if not points:
        return "(none reported)"
    out = []
    for i, p in enumerate(points):
        out.append(f"{i}. turn {p.get('turn')} · agent {p.get('agent')}\n"
                   f"   problem : {p.get('problem', '')}\n"
                   f"   evidence: {p.get('evidence', '')}")
        modes = p.get("modes")
        if modes is not None:
            if p.get("none_fits"):
                out.append(f"   modes   : none fit — {p.get('missing') or 'unstated'}")
            else:
                shown = ", ".join(f"{m['code']} ({m['fitness']})" for m in modes) or "none given"
                out.append(f"   modes   : {shown}")
    return "\n".join(out)


# -------------------------------------------------------------------- parsing
def _parse(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:                                          # noqa: BLE001
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:                                      # noqa: BLE001
            return None


def _ask(call, model, prompt, check, retries=1):
    """Call, validate, re-ask naming the violation. None when it never passes."""
    for attempt in range(retries + 1):
        text = prompt if attempt == 0 else (
            prompt + f"\n\nYour previous answer was rejected: {problem}. "
            "Return the full JSON again, correcting exactly that.")
        d = _parse(call(text, model))
        problem = check(d) if d is not None else "the response was not JSON"
        if problem is None:
            return d
    return None


# ------------------------------------------------------------ pass 1: points
def _points_ok(d, expected):
    """Every turn answered, and every point carrying evidence."""
    ts = d.get("turns") if isinstance(d, dict) else None
    if not isinstance(ts, list):
        return "expected a 'turns' list"
    have = {}
    for e in ts:
        if isinstance(e, dict):
            try:
                have[int(e.get("turn"))] = e
            except (TypeError, ValueError):
                pass
    absent = [t["turn"] for t in expected if t["turn"] not in have]
    if absent:
        return f"turns {absent} have no entry; every turn needs one"
    silent, bare = [], []
    for k, e in have.items():
        pts = e.get("points") or []
        if not pts and not str(e.get("checked") or "").strip():
            silent.append(k)
        for p in pts:
            if not isinstance(p, dict) or not str(p.get("evidence") or "").strip():
                bare.append(k)
                break
    if silent:
        return f"turns {silent} have neither points nor a 'checked' line"
    if bare:
        return (f"turns {bare} report a point with no evidence; every point needs "
                "the span that shows it, or a statement of what is missing")
    return None


def _flatten(d, expected) -> tuple[list, list]:
    """(points, checked) — points carry their turn and agent, in trace order."""
    by_turn = {}
    for e in d.get("turns") or []:
        if isinstance(e, dict):
            try:
                by_turn[int(e.get("turn"))] = e
            except (TypeError, ValueError):
                pass
    points, checked = [], []
    for t in expected:
        e = by_turn.get(t["turn"], {})
        checked.append({"turn": t["turn"], "agent": t["agent"],
                        "checked": str(e.get("checked") or "").strip()})
        for p in e.get("points") or []:
            if isinstance(p, dict) and str(p.get("evidence") or "").strip():
                points.append({"turn": t["turn"], "agent": t["agent"],
                               "evidence": str(p.get("evidence")).strip(),
                               "problem": str(p.get("problem") or "").strip()})
    return points, checked


def read_points(call, model, trace_text, expected, taxonomy_text=None, program_text=""):
    """One reader's first pass. taxonomy_text=None is reader B, which reads with
    no vocabulary in view. program_text is the program's success rule (see
    prompts.program_block), the same for every pass. Returns (points, checked) or None."""
    if taxonomy_text is None:
        prompt = prompts.READER_B_POINTS.format(
            layout=prompts.TURN_LAYOUT, point_rule=prompts.POINT_RULE,
            every_turn=prompts.EVERY_TURN, program=program_text, trace=trace_text)
    else:
        prompt = prompts.READER_A_POINTS.format(
            layout=prompts.TURN_LAYOUT, point_rule=prompts.POINT_RULE,
            every_turn=prompts.EVERY_TURN, program=program_text, taxonomy=taxonomy_text, trace=trace_text)
    d = _ask(call, model, prompt, lambda x: _points_ok(x, expected))
    if d is None:
        return None
    return _flatten(d, expected)


# ------------------------------------------------------------- pass 2: modes
def _modes_ok(d, n):
    a = d.get("assignments") if isinstance(d, dict) else None
    if not isinstance(a, list):
        return "expected an 'assignments' list"
    seen = set()
    for e in a:
        if not isinstance(e, dict):
            continue
        try:
            seen.add(int(e.get("index")))
        except (TypeError, ValueError):
            pass
    absent = sorted(set(range(n)) - seen)
    if absent:
        return f"points {absent} have no assignment; every point needs one"
    return None


def assign_modes(call, model, points, taxonomy_text, valid_ids, program_text=""):
    """A reader's second pass over its own frozen point list. Returns a list
    aligned to `points`, or None. "Nothing fits" is a legal answer and is what
    the coverage measurement is made of."""
    if not points:
        return []
    prompt = prompts.ASSIGN_MODES.format(taxonomy=taxonomy_text, program=program_text,
                                         points=render_points(points))
    d = _ask(call, model, prompt, lambda x: _modes_ok(x, len(points)))
    if d is None:
        return None
    out = [{"codes": [], "none_fits": True, "missing": None} for _ in points]
    for e in d.get("assignments") or []:
        if not isinstance(e, dict):
            continue
        try:
            i = int(e.get("index"))
        except (TypeError, ValueError):
            continue
        if not 0 <= i < len(points):
            continue
        codes = []
        for c in e.get("codes") or []:
            if not isinstance(c, dict) or c.get("code") not in valid_ids:
                continue
            try:
                fit = max(0, min(100, int(c.get("fitness"))))
            except (TypeError, ValueError):
                continue
            codes.append({"code": c["code"], "fitness": fit})
        good = [c for c in codes if c["fitness"] >= FIT_GOOD]
        none_fits = bool(e.get("none_fits")) or not good
        out[i] = {"codes": codes, "none_fits": none_fits,
                  "missing": (str(e.get("missing")).strip()
                              if e.get("missing") else None)}
    return out


def with_modes(points, modes):
    """Attach a reader's assignments to its points, for the decider's listing."""
    out = []
    for p, m in zip(points, modes or []):
        q = dict(p)
        q["modes"] = m["codes"]
        q["none_fits"] = m["none_fits"]
        q["missing"] = m["missing"]
        out.append(q)
    return out


# ------------------------------------------------------------------- decider
def _decision_ok(d):
    if not isinstance(d, dict):
        return "expected a JSON object"
    if not isinstance(d.get("points"), list):
        return "expected a 'points' list, empty if the trace shows no failure"
    for p in d["points"]:
        if not isinstance(p, dict):
            return "every point must be an object"
        if not str(p.get("evidence") or "").strip():
            return "every point needs its final evidence span"
        try:
            int(p.get("turn"))
        except (TypeError, ValueError):
            return "every point needs the turn it happened at"
    return None


def decide(call, model, trace_text, a_points, b_points, taxonomy_text, valid_ids,
           turn_agents=None, program_text=""):
    """The decider. Validates each reported point against the full trace, merges
    on the evidence, settles the span, and assigns the modes. Returns
    {"points": [...], "rejected": [...]} or None."""
    prompt = prompts.DECIDE.format(
        layout=prompts.TURN_LAYOUT, point_rule=prompts.POINT_RULE, program=program_text,
        taxonomy=taxonomy_text, trace=trace_text,
        a_points=render_points(a_points), b_points=render_points(b_points))
    d = _ask(call, model, prompt, _decision_ok)
    if d is None:
        return None
    points = []
    for p in d["points"]:
        try:
            turn = int(p.get("turn"))
        except (TypeError, ValueError):
            continue
        codes = [c for c in (p.get("codes") or []) if c in valid_ids]
        none_fits = bool(p.get("none_fits")) or not codes
        points.append({
            "turn": turn,
            "agent": p.get("agent") or (turn_agents or {}).get(turn),
            "evidence": str(p.get("evidence")).strip(),
            "problem": str(p.get("problem") or "").strip(),
            "codes": [] if none_fits else codes,
            "none_fits": none_fits,
            "missing": str(p.get("missing")).strip() if p.get("missing") else None,
            "from_a": p.get("from_a") if isinstance(p.get("from_a"), int) else None,
            "from_b": p.get("from_b") if isinstance(p.get("from_b"), int) else None,
        })
    rejected = [r for r in (d.get("rejected") or []) if isinstance(r, dict)]
    return {"points": points, "rejected": rejected}


# -------------------------------------------------------------- consolidation
def counts_from_points(points) -> dict:
    """The scoring surface: {code: distinct steps at which it was found}.

    One occurrence per distinct step, the same count rule the panel judge states
    to its annotators, so a count from this judge and a count from that one mean
    the same thing. Two points on one step carrying the same code are one
    occurrence of that code at that step; the two points survive separately in
    `points`, where anything that wants them can read them."""
    seen = {}
    for p in points:
        for c in p.get("codes") or []:
            seen.setdefault(c, set()).add(p["turn"])
    return {c: len(t) for c, t in sorted(seen.items())}


def agreement(decision) -> dict:
    """What the run learned about its own reliability, for free.

    Recorded because component 6 of the measurement framework is confidence and
    coverage, and because a decider that resolves everything in one call leaves
    no other trace of having been contested."""
    pts = decision["points"]
    both = sum(1 for p in pts if p["from_a"] is not None and p["from_b"] is not None)
    only_a = sum(1 for p in pts if p["from_a"] is not None and p["from_b"] is None)
    only_b = sum(1 for p in pts if p["from_a"] is None and p["from_b"] is not None)
    neither = len(pts) - both - only_a - only_b
    return {"points": len(pts), "found_by_both": both, "only_a": only_a,
            "only_b": only_b, "decider_only": neither,
            "rejected": len(decision["rejected"]),
            "uncovered": sum(1 for p in pts if p["none_fits"])}


def mode_agreement(decision, a_modes, b_modes) -> dict:
    """For points both readers found, did they choose the same modes.

    Meaningful only because both readers assign modes under identical conditions:
    over a frozen point list, with the same taxonomy, in a separate pass."""
    same = differ = 0
    for p in decision["points"]:
        ia, ib = p["from_a"], p["from_b"]
        if ia is None or ib is None:
            continue
        if not (0 <= ia < len(a_modes)) or not (0 <= ib < len(b_modes)):
            continue
        ca = {c["code"] for c in a_modes[ia]["codes"] if c["fitness"] >= FIT_GOOD}
        cb = {c["code"] for c in b_modes[ib]["codes"] if c["fitness"] >= FIT_GOOD}
        if ca == cb:
            same += 1
        else:
            differ += 1
    return {"shared_points": same + differ, "same_modes": same, "different_modes": differ}


def coverage(a_modes, b_modes, decision) -> dict:
    """How often the vocabulary had nothing for a real failure. The reason both
    readers are allowed to decline, and the reason the decider is too."""
    def none_rate(ms):
        return sum(1 for m in (ms or []) if m["none_fits"])
    return {"reader_a_none_fits": none_rate(a_modes),
            "reader_b_none_fits": none_rate(b_modes),
            "decider_none_fits": sum(1 for p in decision["points"] if p["none_fits"]),
            "missing_described": [p["missing"] for p in decision["points"]
                                  if p["none_fits"] and p["missing"]]}
