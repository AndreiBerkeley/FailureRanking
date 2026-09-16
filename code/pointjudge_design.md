# Proposed: two readers, two passes each, one decider

**Status: implemented, never run, not frozen.** The code is
`new_pipeline/pointjudge/`, with its own README covering use and output. Nothing
in `judges/` archives it yet, because it has produced no mapping. Two decisions
in it are still open, marked below; both are parameters rather than blockers, and
the defaults chosen are stated where they arise. It becomes `judge-4` when it has
judged something and Andrei has settled the open points.

## Why replace judge-3

judge-3 records a code on a turn. That is the whole finding. It cannot say where
in the turn the behaviour was, cannot separate two failures on one turn, and
cannot be re-checked without re-reading the turn. Its open branch supplies the
majority of firings and places 700 of them on no turn at all, and it enters the
counts at full weight without passing the panel's vote.

The proposal changes the unit of measurement, not the ambition. It measures
**failure points**, and for each one it knows the step, the evidence, and the
modes.

## The object

A **failure point** is a step plus an evidence excerpt from that step.

Two findings are the same point only if their evidence agrees. This is the
operative rule and it has teeth: one step can hold several distinct failure
points, including several of the same kind, whenever the evidence diverges.
Sameness is settled by looking at the spans, not by the codes assigned.

An **absence** is evidenced by saying what is missing. Evidence is evidence: a
required part that never appears is quoted by naming it and pointing at where it
was owed.

## The passes

Two readers, A and B, each reading the whole trace step by step, each in two
passes.

| | pass 1 | pass 2 |
|---|---|---|
| A | reads **with** the taxonomy, identifies failure points | assigns modes to its own points |
| B | reads with **no taxonomy**, identifies failure points | assigns modes to its own points |

Pass 1 produces points only, no modes, and the point list is frozen before pass 2
begins. That freezing is what makes an unfittable point visible: a reader that
named points and modes in one breath would silently drop anything the vocabulary
does not cover.

Both readers may answer **"none fits"** in pass 2. The taxonomy is information
about what failures look like, not a checklist, so this holds for A as much as
for B. A point that nothing fits is a gap in the vocabulary, located at a step,
with evidence attached.

The only asymmetry is that A saw the vocabulary before looking and B did not.
Everything else is identical, so any difference in what they find is attributable
to that, and both mode opinions are formed under the same conditions.

## The decider

One call. It reads the **full trace**, both point lists with their excerpts, and
both mode assignments. It:

1. validates each point, rejecting what is not a failure;
2. decides which of A's and B's points are the same point, on the evidence;
3. settles the final evidence excerpt for each surviving point;
4. assigns the final mode or modes, plural where the point warrants it.

**No discussion round between A and B.** Deciding whether two spans describe the
same thing is not a matter of opinion, and one reader holding both lists and the
trace settles it once instead of twice by negotiation. Model readers in
discussion converge by capitulation, so the consensus a round produces is not
evidence that they agreed, and the reliability numbers would have to be read off
the pre-discussion lists anyway. The decider already supplies the second opinion
on any point only one reader found, because it validates against the full trace.

*This is a recommendation Andrei has not yet accepted or rejected.*

## What the record then contains, at no extra cost

- agreement between A and B on **points**, before anything merges them;
- agreement on **modes**, for the points they share;
- B's rate of points **nothing fits**, and A's;
- for every surviving point: step, evidence excerpt, modes, and which reader
  found it.

The first three are the reliability and coverage component the framework asks
for. None needs an extra call.

## Cost

Five calls per trace: A twice, B twice, the decider once. judge-3 uses at most
four. So roughly 25% more than the pass now running, before counting that the
decider reads the full trace.

## Open decisions

1. **What B sees in pass 2.** Its own points with excerpts plus the taxonomy, or
   the full trace as well. The excerpt alone may not carry enough context to
   choose a mode; including the trace makes the call longer and dearer.
2. **Whether the no-discussion recommendation stands.** If singleton points turn
   out to be a large share of the total, a cross-check is worth adding: each
   reader is shown the other's spans and says confirm or reject, with no
   requirement to converge. The share is measurable from the first run at no
   extra cost, so this can be decided on evidence rather than in advance.

## What it does not change

Independent readers, no deliberation before the decider, temperature 0, gold
stripped at the boundary, failure recorded as failure rather than as silence,
traces never elided, and the harness's field markers never counted as a failure.
