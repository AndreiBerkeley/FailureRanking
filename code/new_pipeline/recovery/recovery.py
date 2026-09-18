"""Recovery pass: from a reader's anchored answers to a verdict per failure point.

The reader (prompts.RECOVERY) answers four questions per point with verbatim quotes. This
module renders the points for it, parses its answer, checks every quote against the part
of the trace it claims to come from, checks chronology, and computes the verdict by a
fixed rule. The reader never states a verdict.

VERDICTS
    unrecovered      the effect is in the final output, or what the point cost is absent
                     from it, or the reader could not show otherwise
    corrected        a later turn replaced the artifact and the output does not carry it
    contained        no later turn consumed the artifact and the output does not carry it
    made_irrelevant  consumed, not corrected, yet the output does not carry it -- or what
                     the point cost was supplied by another path (redundancy)
    unassessable     the reader declared the final output cannot settle it, with nothing
                     else to go on

Recovered = corrected | contained | made_irrelevant. Missing evidence never becomes
recovery: an unverifiable quote is dropped, and a point whose output answer is missing or
whose quotes were all dropped is unrecovered.
"""
from __future__ import annotations

import difflib
import json
import re

from new_pipeline.generation.render import INSTR, INPUT, OUTPUT, HARNESS, ENV

RECOVERED = ("corrected", "contained", "made_irrelevant")
FUZZY_MIN = 0.85          # share of a quote that must match contiguously to count as found
MIN_QUOTE = 12            # shorter quotes are too easy to find by accident


# --------------------------------------------------------------- rendering
def render_points(points: list) -> str:
    """The judge's points as the recovery reader sees them: turn, agent, what was wrong,
    the evidence. Codes are deliberately not shown."""
    if not points:
        return "(none)"
    out = []
    for i, p in enumerate(points):
        ev = p.get("evidence") or ""
        missing = p.get("missing")
        if ev:
            shown = ev
        elif missing:
            shown = "(an absence) " + str(missing)
        else:
            shown = "(this judge recorded no quote; locate the turn's output yourself)"
        out.append(f"{i}. turn {p.get('turn')} · agent {p.get('agent')}\n"
                   f"   what was wrong: {p.get('problem', '')}\n"
                   f"   evidence      : {shown}")
    return "\n".join(out)


def split_turn(block: str) -> dict:
    """A rendered turn block -> its instructions / input / output sections."""
    def between(a, b):
        i = block.find(a)
        if i < 0:
            return ""
        j = block.find(b, i + len(a)) if b else -1
        return block[i + len(a): j if j >= 0 else None]
    return {"instr": between(INSTR, INPUT), "input": between(INPUT, OUTPUT),
            "output": between(OUTPUT, "===== end of turn")}


def final_output(trace_text: str, turns: list) -> str:
    """The program's final output: a harness block after the last turn if there is one,
    else the last turn's output."""
    last_close = trace_text.rfind(f"===== end of turn {turns[-1]['turn']} =====")
    tail = trace_text[last_close:] if last_close >= 0 else ""
    h = tail.find(HARNESS)
    if h >= 0:
        return tail[h + len(HARNESS):]
    return split_turn(turns[-1]["block"])["output"]


# --------------------------------------------------------------- quotes
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def locate(quote: str, text: str) -> str:
    """'exact' | 'fuzzy' | 'unverified'. Fuzzy = the longest contiguous common run covers
    FUZZY_MIN of the quote (the reader dropped or altered a few characters)."""
    q, t = _norm(quote), _norm(text)
    if len(q) < MIN_QUOTE:
        return "unverified"
    if q in t:
        return "exact"
    m = difflib.SequenceMatcher(None, t, q, autojunk=False).find_longest_match(0, len(t), 0, len(q))
    return "fuzzy" if m.size >= FUZZY_MIN * len(q) else "unverified"


# --------------------------------------------------------------- parsing
def parse(raw):
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
            try:
                from new_pipeline.generation.run import salvage
                return salvage(m.group(0))
            except Exception:                                  # noqa: BLE001
                return None


def answer_ok(d, n_points):
    """Shape check only; quote checks come after. Returns a problem string or None."""
    if not isinstance(d, dict) or not isinstance(d.get("points"), list):
        return "no 'points' list"
    seen = {}
    for e in d["points"]:
        if not isinstance(e, dict) or not isinstance(e.get("index"), int):
            return "an entry lacks an integer 'index'"
        seen[e["index"]] = e
    missing = [i for i in range(n_points) if i not in seen]
    if missing:
        return f"points {missing} have no entry"
    for i, e in seen.items():
        o = e.get("output")
        if not isinstance(o, dict) or "effect_in_output" not in o:
            return f"point {i}: 'output.effect_in_output' missing"
        if o["effect_in_output"] not in (True, False, "unassessable"):
            return f"point {i}: effect_in_output must be true, false or \"unassessable\""
        if not isinstance(e.get("consumed", []), list) or not isinstance(e.get("events", []), list):
            return f"point {i}: 'consumed' and 'events' must be lists"
    return None


# --------------------------------------------------------------- checking + verdict
def check_point(entry: dict, point: dict, turn_blocks: dict, out_text: str) -> dict:
    """Validate every quote in one entry against where it claims to come from, drop what
    fails, and record what was kept. Chronology: consumed/event turns must be after the
    point's turn and must exist."""
    pt = int(point["turn"])
    kept = {"effect": None, "consumed": [], "events": [], "output": {}, "dropped": []}

    eff = entry.get("effect") or {}
    own = turn_blocks.get(pt, {}).get("output", "")
    loc = locate(eff.get("quote", ""), own)
    if loc != "unverified":
        kept["effect"] = {**eff, "located": loc}
    elif eff.get("quote"):
        kept["dropped"].append({"field": "effect", "quote": eff.get("quote"), "reason": "not found in the point's turn output"})

    for c in entry.get("consumed") or []:
        k = c.get("turn")
        if not isinstance(k, int) or k <= pt or k not in turn_blocks:
            kept["dropped"].append({"field": "consumed", "turn": k, "reason": "turn not after the point, or not a turn"}); continue
        loc = locate(c.get("quote", ""), turn_blocks[k]["input"])
        if loc == "unverified":
            kept["dropped"].append({"field": "consumed", "turn": k, "quote": c.get("quote"), "reason": "not found in that turn's input"}); continue
        kept["consumed"].append({**c, "located": loc})

    for e in entry.get("events") or []:
        k = e.get("turn"); kind = e.get("kind")
        if kind not in ("correction", "containment"):
            kept["dropped"].append({"field": "events", "turn": k, "reason": f"unknown kind {kind!r}"}); continue
        if not isinstance(k, int) or k <= pt or k not in turn_blocks:
            kept["dropped"].append({"field": "events", "turn": k, "reason": "turn not after the point, or not a turn"}); continue
        blk = turn_blocks[k]
        loc = locate(e.get("quote", ""), blk["input"] + "\n" + blk["output"])
        if loc == "unverified":
            kept["dropped"].append({"field": "events", "turn": k, "quote": e.get("quote"), "reason": "not found in that turn"}); continue
        kept["events"].append({**e, "located": loc})

    o = entry.get("output") or {}
    ko = {"effect_in_output": o.get("effect_in_output"), "cost_supplied": o.get("cost_supplied"), "why": o.get("why")}
    if o.get("effect_in_output") is True:
        loc = locate(o.get("quote", ""), out_text)
        ko["quote_located"] = loc
        if loc == "unverified":
            # the claim "it is in the output" needs its quote; without one it stands anyway,
            # because the conservative direction is unrecovered
            kept["dropped"].append({"field": "output", "quote": o.get("quote"), "reason": "not found in the final output (claim kept: conservative)"})
    if o.get("cost_supplied") is True:
        loc = locate(o.get("cost_quote", ""), out_text)
        ko["cost_quote_located"] = loc
        if loc == "unverified":
            # the recovery claim does not count without its quote -- but dropping it is not
            # the opposite claim (that the cost is absent); the point falls back to the
            # effect_in_output answer, which needs no quote when it is "false"
            ko["cost_supplied"] = None
            kept["dropped"].append({"field": "output.cost_supplied", "quote": o.get("cost_quote"), "reason": "not found in the final output (claim dropped; falls back to effect_in_output)"})
    kept["output"] = ko
    return kept


def verdict(kept: dict) -> str:
    """The rule. For a point whose harm is something missing, `cost_supplied` decides:
    absent -> unrecovered, supplied by another path -> recovered whatever else is true.
    Otherwise `effect_in_output` decides, and the events only name the kind of recovery."""
    o = kept["output"]
    eio, cost = o.get("effect_in_output"), o.get("cost_supplied")
    if cost is False:
        return "unrecovered"
    if cost is not True:
        if eio is True:
            return "unrecovered"
        if eio == "unassessable":
            return "unassessable"
        if eio is not False:
            return "unrecovered"                   # no usable output answer: conservative
    # recovered: say how
    if any(e["kind"] == "correction" for e in kept["events"]):
        return "corrected"
    if not kept["consumed"]:
        return "contained"
    return "made_irrelevant"


def summarise(results: list) -> dict:
    """Run-level counts over judged traces."""
    from collections import Counter
    v = Counter(); located = Counter(); dropped = 0; pts = 0
    for r in results:
        if r.get("status") != "judged":
            continue
        for p in r["points"]:
            pts += 1; v[p["recovery"]] += 1; dropped += len(p["recovery_evidence"].get("dropped", []))
            e = p["recovery_evidence"].get("effect")
            located[e["located"] if e else "no effect quote"] += 1
    return {"points": pts, "verdicts": dict(v), "recovered": sum(v[k] for k in RECOVERED),
            "effect_quotes": dict(located), "dropped_claims": dropped}
