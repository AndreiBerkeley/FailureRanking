"""Prompts for the two-reader/decider judge.

Every prompt is complete as sent. The trace-layout block is repeated in each
reader prompt on purpose: a prompt should be readable, and auditable, on its own.

Design in judges/proposed/two-reader-decider.md.
"""

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
not a deviation, even when a later sentence names only some of the fields. The
`[[ ## name ## ]]` markers that open each output field are likewise the
harness's own output format, declared in the same instructions section and
needed to parse the output; using them, rather than a plainer layout described
elsewhere in the instructions (`reasoning: ...`, `**query**: ...`), is required,
not a deviation, and is never a failure."""

# ---------------------------------------------------------------- failure point
POINT_RULE = """## WHAT A FAILURE POINT IS

A failure point is one thing that went wrong, at one step, with the evidence for
it. It has two parts and both are required:

  the step   the turn number and agent where the mistake was made
  the evidence   the exact text that shows it

The evidence is quoted from that turn, verbatim, and it is the shortest span
that shows the mistake. Quote what is wrong, not the paragraph around it.

WHEN WHAT IS WRONG IS AN ABSENCE, evidence is still evidence: say what is
missing and where it was owed. "The instructions require a closing marker after
the answer; the output ends at `...the treaty.` with nothing after it" is
evidence. "Missing marker" is not, because nothing can be checked against it.

TWO FAILURE POINTS ARE DIFFERENT POINTS WHEN THEIR EVIDENCE IS DIFFERENT. One
turn can hold several, including several of the same kind: three unsupported
claims in one summary are three points, each with its own span. Do not merge
them into one finding, and do not split one span into several findings.

An agent is judged against its own instructions and its own input, and nothing
else. Whatever it received is input, whoever produced it and whatever is wrong
with it. A failure point is a gap between what this agent was required to do
with what it was handed and what it did."""

EVERY_TURN = """## EVERY TURN IS ANSWERED

Answer for every turn in the trace, in order. A turn where nothing went wrong
gets an empty `points` list and a one-line `checked` saying what you looked at
and against what. A turn that appears with neither points nor a `checked` line
has not been read, and the whole answer is rejected."""

# --------------------------------------------------------------- program rule
PROGRAM_RULE = """## HOW THIS PROGRAM'S OUTPUT IS SCORED

{rule}

Judge each step's work against this. A step has obtained something only when what
the output is scored on came back; material that is merely about it does not count."""


def program_block(structure) -> str:
    """The program's success rule as one prompt section, from `success_rule` in the
    benchmark's structure.json; empty when the structure declares none. It is a fact
    about how the program is scored, not an outcome, so every pass may see it: without
    it a reader judges 'what was needed' by its own reading of the task."""
    rule = ((structure or {}).get("success_rule") or "").strip()
    return PROGRAM_RULE.format(rule=rule) if rule else ""

# ------------------------------------------------------------- reader A, pass 1
READER_A_POINTS = """You are reading one execution trace of a candidate program, step by step, to
find where it went wrong.

{layout}

{point_rule}

{every_turn}

{program}

## A VOCABULARY OF KNOWN FAILURES

Below is a taxonomy of failure modes seen in this program before. Read it as a
description of what failures tend to look like here, NOT as a checklist and NOT
as the set of things that can be wrong. It is there to sharpen what you notice.

Do not assign codes now. You are looking for failure points, not naming them. A
real failure that no entry below describes is still a failure point and must be
reported; a code that matches nothing in this trace must not be made to fit.

{taxonomy}

## THE TRACE

{trace}

## ANSWER

Return ONLY JSON:
{{"turns": [{{"turn": 1, "agent": "<name>", "checked": "<one line, what you
checked against what>", "points": [{{"evidence": "<verbatim span, or a statement
of what is missing and where it was owed>", "problem": "<one sentence: what is
wrong with it>"}}]}}]}}"""

# ------------------------------------------------------------- reader B, pass 1
READER_B_POINTS = """You are reading one execution trace of a candidate program, step by step, to
find where it went wrong.

{layout}

{point_rule}

{every_turn}

{program}

You are given no vocabulary of failures on purpose. Describe what is wrong in
your own words, from the trace in front of you. Do not try to sort findings into
categories, and do not generalise: name this failure, at this step, with this
evidence.

## THE TRACE

{trace}

## ANSWER

Return ONLY JSON:
{{"turns": [{{"turn": 1, "agent": "<name>", "checked": "<one line, what you
checked against what>", "points": [{{"evidence": "<verbatim span, or a statement
of what is missing and where it was owed>", "problem": "<one sentence: what is
wrong with it>"}}]}}]}}"""

# ---------------------------------------------------------------------- pass 2
ASSIGN_MODES = """Below are failure points you identified in one execution trace, and a taxonomy
of failure modes.

For each point, name the mode or modes that describe it.

{program}

## HOW TO DECIDE

Read the point's evidence, then the definitions. A mode fits when its definition
names what happened at that point. Judge the mechanism, not the wording: two
descriptions of the same mistake are the same mode.

Give each assignment a fitness from 0 to 100:

  90-100  the definition names exactly what happened here
  70-89   the definition covers it, with detail it does not mention
  40-69   related, and broader or narrower than what happened
  0-39    the nearest thing available, and not a description of this point

A point can carry more than one mode when it genuinely exhibits more than one
mechanism. It usually carries one.

## NONE OF THEM MAY FIT, AND THAT IS AN ANSWER

If no mode describes a point, set `"none_fits": true` and leave `codes` empty.
Do not reach for the closest available label. A point nothing describes is the
most informative thing you can report: it says the vocabulary is missing
something, and it is recorded rather than scored. Forcing it into a code
destroys that and corrupts the count.

Say what is missing in `missing`: one sentence naming the mechanism no mode
covers.

## THE TAXONOMY

{taxonomy}

## THE FAILURE POINTS

{points}

## ANSWER

Return ONLY JSON, one entry per point, same indices:
{{"assignments": [{{"index": 0, "none_fits": false, "codes": [{{"code": "<id>",
"fitness": <0-100>}}], "missing": null}}]}}"""

# -------------------------------------------------------------------- the decider
DECIDE = """Two readers independently read one execution trace and reported where it went
wrong. Reader A had a taxonomy of known failure modes in view while reading;
reader B did not. Each then assigned modes to their own points. They did not
speak to each other and neither has seen the other's findings.

Your job is to settle what the trace actually shows.

{layout}

{point_rule}

{program}

## WHAT YOU DO, IN ORDER

1. VALIDATE. For each reported point, check it against the trace. Reject it if
   the evidence does not show a failure: if the behaviour was required by the
   agent's own instructions, if the mistake was already present in what this
   agent was handed, if the quoted text does not say what the reader says it
   says, or if nothing was actually wrong. Record every rejection and why.

2. MERGE. Decide which of A's points and B's points are the same point. They are
   the same when their evidence points at the same mistake at the same step,
   even if the two readers quoted different spans of it or described it
   differently. They are DIFFERENT points when the evidence is different, and
   one turn may keep several points, including several of the same kind. Do not
   merge two mistakes because they share a mode, and do not split one mistake
   because the readers worded it differently.

3. SETTLE THE EVIDENCE. For each surviving point, give the final span: the
   shortest verbatim quote from that turn that shows the mistake, or, for an
   absence, the statement of what is missing and where it was owed. You may take
   either reader's span or write a better one from the trace.

4. ASSIGN THE MODES. Give each surviving point its mode or modes. The readers'
   assignments are opinions, not instructions: adopt one, take both, or assign
   something neither chose. If no mode in the taxonomy describes the point, set
   `"none_fits": true`, leave `codes` empty, and say in `missing` what mechanism
   is uncovered. Do not force a point into the nearest label.

A point only one reader found is not weaker for that. Reader A saw the
vocabulary before looking and will tend to find what it names; reader B did not
and will tend to find what it does not. Judge the evidence.

## THE TAXONOMY

{taxonomy}

## THE TRACE

{trace}

## READER A REPORTED

{a_points}

## READER B REPORTED

{b_points}

## ANSWER

Return ONLY JSON:
{{"points": [{{"turn": <int>, "agent": "<name>", "evidence": "<the final span>",
"problem": "<one sentence>", "none_fits": false, "codes": ["<id>"],
"missing": null, "from_a": <index or null>, "from_b": <index or null>}}],
"rejected": [{{"reader": "A", "index": 0, "why": "<one sentence>"}}]}}"""
