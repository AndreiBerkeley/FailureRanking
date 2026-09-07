#!/usr/bin/env python3
"""The measurement judge: taxonomy codes for one (task, candidate) pair.

This is NOT the judge inside the taxonomy pipeline. That one reads a refinement
corpus and feeds a refiner. This one runs after a taxonomy is frozen, over the
measurement set, and its output is the evidence a score is computed from. The
taxonomy is fixed input here; nothing downstream revises it.

OUTPUT, deliberately minimal:

    {"<code id>": <count>, ...}

Occurrence and count. No confidence, no evidence, no severity, no ordering, no
recovery. Those are later layers; the module is arranged so each is an added
stage or an added field rather than a rewrite.

SHAPE

    panel: N independent annotators, each with the taxonomy   -> vote
    open:  one reader with NO vocabulary                      -> mapped to codes
    consolidate: union of the two branches

Neither branch is told HOW to look for failures. No search procedure, no
causality reconstruction, no ordering of attention. The panel is given the
vocabulary and asked what occurred; the open reader is given nothing and asked
what went wrong.

WHY THE PANEL DOES NOT DELIBERATE BY DEFAULT

Two reasons, both about this being the scoring instrument. A threshold vote is
mechanically identical for every trace and every candidate; a deliberation's
outcome depends on which annotator speaks first, which varies. And the vote
split is the raw material for a later confidence layer: recorded for free if
annotators are independent, destroyed unrecoverably if they reconcile first.
Deliberation is available as an opt-in stage.

WHY THE OPEN BRANCH EXISTS

Not to extend the taxonomy: an unmapped problem cannot enter a per-code score,
and forcing it into the nearest code is exactly the bad assignment we are
avoiding. It is there for recall of codes we ALREADY have. A reader holding
twenty codes in mind misses things a reader holding none notices. Those map to
existing codes and enter the score cleanly. Problems that map to nothing are
recorded as unmapped and never scored.

COUNTS

The count rule is stated to the annotator because otherwise "how many times" is
a reading-style artifact rather than a measurement: one per distinct step in
which the behaviour appears. Across branches the rule is MAX, never sum -- we do
not record where a behaviour occurred, so two branches reporting the same code
cannot be shown to have found different incidents, and summing would double
count.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from statistics import median_low

MAX_TRACE_CHARS = 48000

# The gold-free rule lives in one place (pipeline/goldfree.py) so the judge and
# the taxonomy pipeline cannot drift apart on what counts as an outcome field.
from new_pipeline.goldfree import strip as strip_outcomes            # noqa: E402,F401
from new_pipeline.llm import log                        # noqa: E402


def elide(text, limit=MAX_TRACE_CHARS):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    head = int(limit * 0.6)
    return (text[:head]
            + f"\n\n[... {len(text) - limit} characters elided by the EVALUATION "
              "HARNESS, not by the agent. This is not a truncation failure. ...]\n\n"
            + text[-(limit - head):])


def render_trace(trace: dict, limit=MAX_TRACE_CHARS) -> str:
    """Flat rendering, kept for the legacy callers. The judge itself now uses
    render_turns, which delineates agent turns and never elides."""
    parts = []
    for m in trace.get("messages") or []:
        role = m.get("role", "?")
        content = m.get("content")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        parts.append(f"--- {role} ---\n{content}")
    return elide("\n\n".join(parts), limit)


def render_turns(trace: dict, agents=None, limit: int = 0):
    """Delineated turns: (text, [{"turn", "agent", "block"}]). limit=0 means
    the trace is never cut; a positive limit elides, which drops turns and was
    measured to make a reader report that the agent produced nothing."""
    from new_pipeline.generation.render import render_turns as _rt
    text, turns = _rt(trace, agents)
    if limit and len(text) > limit:
        text = elide(text, limit)
    return text, turns


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


# --------------------------------------------------------------------- prompts
COUNT_RULE = """COUNTING
Count one occurrence per distinct step of the trace in which the behaviour
appears. The same behaviour in three separate steps is 3. One step exhibiting it
is 1, however many times it is restated within that step."""

# Per-turn accounting. The reader is not told how to look; it is told that
# silence on a turn is not an answer. Measured on ten audited traces: a reader
# asked for one trace-level answer recorded findings on the first agent and
# stopped, and skipped the query-writing turns in six of ten traces.
TURN_LAYOUT = """## HOW THE TRACE IS LAID OUT

The trace is a sequence of blocks. Blocks headed
`===== ENVIRONMENT · not an agent turn =====` are the task statement, tool or
retrieval results, and other material produced by the environment. Each agent
turn is enclosed in `===== TURN k · agent: NAME =====` ... `===== end of turn k
=====` and holds `--- instructions given to this agent ---`, `--- input this
agent received ---`, and `--- output this agent produced ---`. A block headed
`===== OUTPUT WITHOUT PRECEDING INSTRUCTIONS ... =====` was assembled by the
harness and is not a turn. A turn is judged against its own instructions and
its own input; a mistake already present in a turn's input belongs to the
earlier turn that produced it. The instructions section declares the agent's
input and output fields as well as its task; producing a declared output field
(such as a `reasoning` field listed under "Your output fields") is required,
not a deviation, even when a later sentence names only some of the fields."""

ANNOTATE_TURNS_PROMPT = """You are annotating one execution trace of a candidate program.

{layout}

## TAXONOMY

{taxonomy}

## TRACE

{trace}

## TASK

Take the turns ONE AT A TIME, in order. For each turn, and for each code in the
taxonomy, decide whether the behaviour the code names occurred in THAT TURN.
Report only the codes that occurred in the turn; omit every code that did not.

{count_rule}
Within a turn, count distinct steps; a trace-level count is the sum over turns
and is computed later, not by you.

A code applies only if the turn's output contains text satisfying its
definition. Do not assign a code because the turn resembles it in spirit, and do
not stretch a code to cover a behaviour its definition does not name.

A turn in which nothing went wrong is a valid and expected result: give it an
empty "codes" object. But EVERY turn must have an entry, in turn order, and
"checked" must say in one line what you compared against what. A turn with no
codes and no "checked" line has not been read.

Return ONLY JSON:
{{"turns": [{{"turn": <int, as in the turn header>,
             "agent": "<name, as in the turn header>",
             "checked": "<what was checked>",
             "codes": {{"<code id>": <count>, ...}}}}]}}
"""

OPEN_TURNS_PROMPT = """You are reading one execution trace of a candidate program.

{layout}

## TRACE

{trace}

## TASK

Take the turns ONE AT A TIME, in order. For each turn, describe what went wrong
in it, if anything: one entry per distinct problem, describing what the agent
did. Do not propose fixes, do not rate importance, do not explain consequences.

A turn in which nothing went wrong gets an empty "problems" list, but EVERY turn
must have an entry, in turn order, and "checked" must say in one line what you
looked at. A turn with no problems and no "checked" line has not been read.

Return ONLY JSON:
{{"turns": [{{"turn": <int, as in the turn header>,
             "agent": "<name, as in the turn header>",
             "checked": "<what was looked at>",
             "problems": ["...", "..."]}}]}}
"""

ANNOTATE_PROMPT = """You are annotating one execution trace of a candidate program.

## TAXONOMY

{taxonomy}

## TRACE

{trace}

## TASK

For each code in the taxonomy, decide whether the behaviour it names occurred in
this trace. Report only the codes that occurred; omit every code that did not.

{count_rule}

A code applies only if the trace contains text satisfying its definition. Do not
assign a code because the trace resembles it in spirit, and do not stretch a code
to cover a behaviour its definition does not name.

A trace in which nothing went wrong is a valid and expected result: return an
empty object.

Return ONLY JSON: {{"codes": {{"<code id>": <count>, ...}}}}
"""

OPEN_PROMPT = """You are reading one execution trace of a candidate program.

## TRACE

{trace}

## TASK

Describe what went wrong in this trace, if anything.

Report one entry per distinct problem, describing what the program did. Do not
propose fixes, do not rate importance, do not explain consequences.

If nothing went wrong, return an empty list.

Return ONLY JSON: {{"problems": ["...", "..."]}}
"""

MAP_PROMPT = """Below are problems observed in one execution trace, and a taxonomy of
failure modes.

## TAXONOMY

{taxonomy}

## PROBLEMS

{problems}

## TASK

For each problem, assign every taxonomy code whose definition it satisfies, and
rate how well each one fits.

ONE FAILURE POINT CAN BE THE SOURCE OF SEVERAL FAILURE MODES. A single thing
that went wrong may satisfy more than one definition at once, or may be a
compound act that different codes each name a part of. Look for all of them:
stopping at the first code that fits leaves the rest of what happened
unrecorded, and that loss is invisible afterwards.

Assign what is actually there, and nothing beyond it. Do not add a second code
because a problem looks like it ought to have one, and do not lengthen the list
to appear thorough -- a padded assignment is as wrong as a missed one, and
harder to notice. A problem that exhibits exactly one mode gets exactly one
code, and that is the ordinary case.

ALWAYS ASSIGN AT LEAST ONE CODE. Do not decline, and do not answer "none". Even
when nothing fits well, name the closest code available. The FITNESS SCORE, not
a refusal, is how a poor fit gets reported.

FITNESS, 0 to 100:

  80-100  the definition names what happened. Someone reading the definition and
          the trace side by side would agree without argument.
  50-79   the code covers the behaviour imprecisely: it names something broader,
          or narrower, or an adjacent act that overlaps this one.
  20-49   this is the closest code available and it still does not describe what
          happened. Assigning it is a stretch.
   0-19   nothing in the taxonomy is close. The vocabulary has no word for this
          behaviour.

Rate honestly and independently for each code. A low score is not a failure on
your part -- it IS the finding, and it is what this step exists to measure. The
taxonomy is being judged by these scores, so inflating them hides the gaps that
the scores are here to expose.

Say in one phrase why each code fits as well or as poorly as you rated it.

Return ONLY JSON:
{{"mappings": [{{"problem": <index>,
                "codes": [{{"code": "<code id>", "fitness": <0-100>,
                           "why": "<one phrase>"}}]}}]}}
"""


# ---------------------------------------------------------------------- stages
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


def _clean_counts(d, valid_ids):
    """Keep only real code ids with positive integer counts."""
    out = {}
    for k, v in (d or {}).items():
        if k not in valid_ids:
            continue
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n > 0:
            out[k] = n
    return out


def annotate(call, model, trace_text, taxonomy_text, valid_ids):
    """One independent annotator. Returns {code: count} or None on failure."""
    raw = call(ANNOTATE_PROMPT.format(taxonomy=taxonomy_text, trace=trace_text,
                                      count_rule=COUNT_RULE), model)
    d = _parse(raw)
    if d is None:
        return None
    return _clean_counts(d.get("codes"), valid_ids)


ANNOTATE_BATCH_PROMPT = """You are annotating execution traces of candidate programs. Each trace
begins with a line `### trace <trace_id>`.

{layout}

## TAXONOMY

{taxonomy}

## TRACES

{traces}

## TASK

Take the traces ONE AT A TIME, in order. Within each trace, take the turns ONE
AT A TIME, in order. For each turn, and for each code in the taxonomy, decide
whether the behaviour the code names occurred in THAT TURN. Report only the
codes that occurred in the turn; omit every code that did not.

{count_rule}
Within a turn, count distinct steps; trace-level counts are computed later.

A code applies only if the turn's output contains text satisfying its
definition. Do not assign a code because the turn resembles it in spirit, and do
not stretch a code to cover a behaviour its definition does not name.

A turn in which nothing went wrong is a valid and expected result: give it an
empty "codes" object. But EVERY trace and EVERY turn must have an entry, in
order, and "checked" must say in one line what you compared against what. A
turn with no codes and no "checked" line has not been read.

Return ONLY JSON:
{{"traces": [{{"trace_id": "<as in the header>",
              "turns": [{{"turn": <int, as in the turn header>,
                         "agent": "<name, as in the turn header>",
                         "checked": "<what was checked>",
                         "codes": {{"<code id>": <count>, ...}}}}]}}]}}
"""

OPEN_BATCH_PROMPT = """You are reading execution traces of candidate programs. Each trace begins
with a line `### trace <trace_id>`.

{layout}

## TRACES

{traces}

## TASK

Take the traces ONE AT A TIME, in order. Within each trace, take the turns ONE
AT A TIME, in order. For each turn, describe what went wrong in it, if anything:
one entry per distinct problem, describing what the agent did. Do not propose
fixes, do not rate importance, do not explain consequences.

A turn in which nothing went wrong gets an empty "problems" list, but EVERY
trace and EVERY turn must have an entry, in order, and "checked" must say in one
line what you looked at. A turn with no problems and no "checked" line has not
been read.

Return ONLY JSON:
{{"traces": [{{"trace_id": "<as in the header>",
              "turns": [{{"turn": <int, as in the turn header>,
                         "agent": "<name, as in the turn header>",
                         "checked": "<what was looked at>",
                         "problems": ["...", "..."]}}]}}]}}
"""


def _batch_ok(d, expected):
    """expected: {trace_id: [{"turn", "agent"}]}. Every trace and every turn
    must appear; a turn with nothing reported needs a 'checked' line."""
    ts = d.get("traces") if isinstance(d, dict) else None
    if not isinstance(ts, list):
        return "expected a 'traces' list"
    got = {str(x.get("trace_id")): x for x in ts if isinstance(x, dict)}
    absent = [t for t in expected if t not in got]
    if absent:
        return f"traces {absent[:3]} have no entry; every trace must appear"
    problems = []
    for tid, turns in expected.items():
        bad = _turns_ok(got[tid], turns)
        if bad:
            problems.append(f"{tid}: {bad}")
    return "; ".join(problems[:4]) if problems else None


def _ask_batch(call, model, prompt, expected):
    raw = call(prompt, model)
    d = _parse(raw)
    problem = _batch_ok(d, expected) if d is not None else "unparseable response"
    if problem is None:
        return d
    log(f"  [!] batch response rejected: {problem[:180]}; re-asking")
    raw = call(prompt + f"\n\nYour previous answer was rejected: {problem}. "
               "Return the full JSON again with every trace and every turn accounted for.", model)
    d = _parse(raw)
    if d is None:
        log("  [!] re-ask also unparseable; batch fails")
        return None
    second = _batch_ok(d, expected)
    if second:
        log(f"  [!] re-ask still rejected: {second[:180]}; batch fails")
        return None
    return d


def annotate_batch(call, model, batch_text, taxonomy_text, valid_ids, expected):
    """One annotator over a batch. Returns {trace_id: (per_turn, counts)} or None."""
    prompt = ANNOTATE_BATCH_PROMPT.format(layout=TURN_LAYOUT, taxonomy=taxonomy_text,
                                          traces=batch_text, count_rule=COUNT_RULE)
    d = _ask_batch(call, model, prompt, expected)
    if d is None:
        return None
    out = {}
    for x in d["traces"]:
        if not isinstance(x, dict):
            continue
        tid = str(x.get("trace_id"))
        per_turn, total = [], Counter()
        for e in (x.get("turns") or []):
            if not isinstance(e, dict):
                continue
            codes = _clean_counts(e.get("codes"), valid_ids)
            per_turn.append({"turn": e.get("turn"), "agent": e.get("agent"),
                             "checked": e.get("checked"), "codes": codes})
            total.update(codes)
        out[tid] = (per_turn, dict(total))
    return out


def open_batch(call, model, batch_text, expected):
    """Open reader over a batch. Returns [{"trace_id","turn","agent","problem"}] or None."""
    prompt = OPEN_BATCH_PROMPT.format(layout=TURN_LAYOUT, traces=batch_text)
    d = _ask_batch(call, model, prompt, expected)
    if d is None:
        return None
    out = []
    for x in d["traces"]:
        if not isinstance(x, dict):
            continue
        tid = str(x.get("trace_id"))
        for e in (x.get("turns") or []):
            if not isinstance(e, dict):
                continue
            for pr in (e.get("problems") or []):
                if str(pr).strip():
                    out.append({"trace_id": tid, "turn": e.get("turn"),
                                "agent": e.get("agent"), "problem": str(pr)})
    return out


def _turns_ok(d, expected):
    """Every expected turn present, each with codes/problems or a 'checked' line."""
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
    silent = [k for k, e in have.items()
              if not (e.get("codes") or e.get("problems"))
              and not str(e.get("checked") or "").strip()]
    if silent:
        return f"turns {silent} have neither findings nor a 'checked' line"
    return None


def _ask_turns(call, model, prompt, expected):
    """Call, validate the per-turn account, re-ask once naming the violation."""
    raw = call(prompt, model)
    d = _parse(raw)
    problem = _turns_ok(d, expected) if d is not None else "unparseable response"
    if problem is None:
        return d
    raw = call(prompt + f"\n\nYour previous answer was rejected: {problem}. "
               "Return the full JSON again with every turn accounted for.", model)
    d = _parse(raw)
    if d is None or _turns_ok(d, expected):
        return None
    return d


def annotate_turns(call, model, trace_text, taxonomy_text, valid_ids, expected):
    """One independent annotator, accounting per turn.
    Returns (per_turn, trace_counts) or None. per_turn is
    [{"turn", "agent", "checked", "codes": {code: count}}] in turn order;
    trace_counts sums the per-turn counts."""
    prompt = ANNOTATE_TURNS_PROMPT.format(layout=TURN_LAYOUT, taxonomy=taxonomy_text,
                                          trace=trace_text, count_rule=COUNT_RULE)
    d = _ask_turns(call, model, prompt, expected)
    if d is None:
        return None
    per_turn, total = [], Counter()
    for e in d["turns"]:
        if not isinstance(e, dict):
            continue
        codes = _clean_counts(e.get("codes"), valid_ids)
        per_turn.append({"turn": e.get("turn"), "agent": e.get("agent"),
                         "checked": e.get("checked"), "codes": codes})
        total.update(codes)
    return per_turn, dict(total)


def open_pass_turns(call, model, trace_text, expected):
    """Vocabulary-free reader, accounting per turn. Returns
    [{"problem", "turn", "agent"}] or None."""
    prompt = OPEN_TURNS_PROMPT.format(layout=TURN_LAYOUT, trace=trace_text)
    d = _ask_turns(call, model, prompt, expected)
    if d is None:
        return None
    out = []
    for e in d["turns"]:
        if not isinstance(e, dict):
            continue
        for pr in (e.get("problems") or []):
            if str(pr).strip():
                out.append({"problem": str(pr), "turn": e.get("turn"),
                            "agent": e.get("agent")})
    return out


def open_pass(call, model, trace_text):
    """Vocabulary-free reader. Returns [problem, ...] or None on failure."""
    raw = call(OPEN_PROMPT.format(trace=trace_text), model)
    d = _parse(raw)
    if d is None:
        return None
    probs = d.get("problems")
    if not isinstance(probs, list):
        return None
    return [str(p) for p in probs if str(p).strip()]


# What a fitness score means, in one place, so the judge and every analysis
# downstream read the same thresholds.
FIT_GOOD = 80      # the definition names what happened
FIT_LOOSE = 50     # covers it imprecisely -- broader, narrower, or adjacent
FIT_STRETCH = 20   # closest available and still not a description
                   # below FIT_STRETCH: the vocabulary has no word for this


def map_open(call, model, problems, taxonomy_text, valid_ids):
    """Map open findings onto codes, graded rather than accepted or refused.

    Two things this fixes. A problem can satisfy more than one definition, and
    forcing a single choice discarded that. And a binary map/unmapped hid the
    case that matters most: a code stretched to fit looks exactly like a code
    that fits. Requiring a fitness score makes the stretch visible, and removes
    the incentive created by making refusal expensive -- there is nothing to
    gain now by avoiding "none", because "none" no longer exists.

    Returns (counts, details). `counts` holds only assignments at FIT_GOOD or
    better, so a scoring path built on it is not fed stretches. `details` keeps
    every assignment with its score, which is where taxonomy gaps are read.
    """
    if not problems:
        return {}, []
    listing = "\n".join(f"{i}. {p}" for i, p in enumerate(problems))
    raw = call(MAP_PROMPT.format(taxonomy=taxonomy_text, problems=listing), model)
    d = _parse(raw)
    # The model sometimes returns the mappings list bare rather than under
    # "mappings"; accept it. Anything else that is not an object is a failure,
    # returned as None rather than raised, so the caller records the batch as
    # failed and the run goes on.
    if isinstance(d, list):
        d = {"mappings": d}
    if not isinstance(d, dict):
        return None

    counts, details, seen = Counter(), [], set()
    for m in (d.get("mappings") or []):
        try:
            idx = int(m.get("problem"))
        except (TypeError, ValueError):
            continue
        if not 0 <= idx < len(problems) or idx in seen:
            continue
        seen.add(idx)
        assigned = []
        for c in (m.get("codes") or []):
            if not isinstance(c, dict):
                continue
            code = str(c.get("code", "")).strip()
            if code not in valid_ids:
                continue
            try:
                fit = max(0, min(100, int(c.get("fitness"))))
            except (TypeError, ValueError):
                continue
            assigned.append({"code": code, "fitness": fit,
                             "why": str(c.get("why") or "")})
            if fit >= FIT_GOOD:
                counts[code] += 1
        best = max((x["fitness"] for x in assigned), default=None)
        details.append({
            # index, not text, is the join key: identical finding text occurs
            # across traces, and joining by text attributed 26 of 379 records
            # to the wrong trace.
            "index": idx,
            "problem": problems[idx], "codes": assigned, "best_fitness": best,
            # a finding whose best code is a stretch is a vocabulary gap wearing
            # a code's name; recorded as such rather than counted as covered
            "verdict": ("covered" if best is not None and best >= FIT_GOOD else
                        "loose" if best is not None and best >= FIT_LOOSE else
                        "stretch" if best is not None and best >= FIT_STRETCH else
                        "uncovered"),
        })
    # a problem the model never answered for is uncovered, not absent
    for i, p in enumerate(problems):
        if i not in seen:
            details.append({"index": i, "problem": p, "codes": [],
                            "best_fitness": None, "verdict": "unanswered"})
    return dict(counts), details


def consolidate(panel, open_counts, threshold, agg=median_low):
    """Union of the two branches. Panel by vote, open by max.

    Count aggregation is over the annotators who REPORTED the code: the vote has
    already decided the behaviour occurred, so folding in zeros from annotators
    who missed it would argue against a decision already made.

    Across branches the rule is max, never sum. Without localization two branches
    reporting one code cannot be shown to have found different incidents.
    """
    votes, counts = Counter(), defaultdict(list)
    for p in panel:
        for code, n in p.items():
            votes[code] += 1
            counts[code].append(n)

    final = {c: int(agg(sorted(counts[c]))) for c, v in votes.items() if v >= threshold}
    for code, n in (open_counts or {}).items():
        final[code] = max(final.get(code, 0), int(n))
    return final, dict(votes)
