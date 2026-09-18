"""The recovery pass prompt: one call per trace, every failure point of that trace.

The reader is told what went wrong and where (the judge's points, codes hidden) and
answers four questions per point with verbatim quotes. It decides nothing: the verdict
is computed from its answers by `recovery.verdict`, and every quote is checked against
the trace before it counts.
"""
from new_pipeline.pointjudge.prompts import TURN_LAYOUT

RECOVERY = """You are reading one execution trace of a candidate program. A judge has already
read it and listed the failure points: at a given turn, the agent did something wrong,
with the evidence quoted. You are NOT asked whether those were failures — take the list
as given. You are asked what became of each one: did its effect reach the program's final
output, or did the program recover from it?

{layout}

The program's FINAL OUTPUT is the last thing in the trace: either the last agent turn's
output, or a block assembled by the harness after the last turn (for example a
concatenation of everything retrieved). Recovery is judged against that final output and
nothing else.

{program}

## WHAT RECOVERY MEANS

A failure point is RECOVERED when the final output does not carry its effect — whether a
later turn corrected it, nothing ever consumed it, or another path supplied what the
failed step was supposed to supply so the output has it anyway. A failure point is NOT
recovered when its effect is visible in the final output, or when what it cost the
program is missing from the final output. A mistake that was caught and fixed is still a
mistake; that is the judge's business, not yours. Your business is only whether the
output carries it.

## THE FOUR QUESTIONS, PER POINT

Answer them in order, for every point, with VERBATIM quotes from the trace. A quote is a
contiguous span copied exactly; never paraphrase, never stitch. Where there is nothing to
quote, say so with an empty string and explain in `why`.

1. EFFECT — what concrete artifact did the point produce: the sentence in a summary, the
   query text, the line of code, the missing element. Quote it from the point's own turn
   output. If the point is an absence, quote the output where the thing should have been
   and say what is missing.

2. CONSUMED — which later turns received that artifact as input. For each, quote the
   artifact as it appears in that later turn's INPUT section. An empty list means no
   later turn received it.

3. EVENTS — later turns that did something about it, each with a verbatim quote from that
   later turn:
     "correction"  — a later turn re-derived, replaced or fixed the artifact before it
                     reached the output;
     "containment" — a later turn received the artifact and demonstrably did not use it.
   Only turns AFTER the point's turn count. An empty list is a valid answer.

4. OUTPUT — look at the FINAL OUTPUT, and ask whether it is WORSE because of this point.
     "effect_in_output": true if the final output carries the wrong artifact or a
                         consequence of it — wrong content, a wrong answer, a wrong line —
                         and quote it there; false if it does not; "unassessable" only if
                         the final output cannot settle it. Superfluous or duplicated
                         material in the output is NOT an effect: an output that has
                         something extra is not worse for it.
     "cost_supplied":    for a point whose harm is that something NEEDED was not obtained
                         or not carried forward — a query that did not target what the
                         task still needed, a summary that dropped an entity, a case not
                         handled — answer true or false, never null: true if the final
                         output contains what that step was supposed to obtain anyway,
                         brought by another turn or path (quote it in the final output);
                         false if the final output lacks it. What was needed is read from
                         the task statement at the top of the trace (the claim's entities
                         and facts, the problem's requirements) and from how the program's
                         output is scored, stated above; never from anything outside the
                         trace. "Contains it" means contains what the output is scored on:
                         where that is a document, only that document's own title line
                         counts, and a passage elsewhere that mentions the entity, or a
                         page about its neighbours, does not supply it. null only for a
                         point whose harm is the PRESENCE of something wrong, never an
                         absence.

   For a point on a query, search, or any request the environment answers, the effect to
   judge is what that request brought back or failed to bring back, and the point is
   recovered only if the final output has what the request should have obtained.

Never invent a recovery. Missing evidence is answered as missing, and the rule that turns
your answers into a verdict treats missing evidence as no recovery.

## THE FAILURE POINTS

{points}

## THE TRACE

{trace}

## ANSWER

Return only JSON:

{{"points": [
  {{"index": 0,
    "effect":   {{"quote": "<verbatim from the point's turn output>", "what": "<a few words>"}},
    "consumed": [ {{"turn": <k>, "quote": "<verbatim from turn k's input>"}} ],
    "events":   [ {{"kind": "correction"|"containment", "turn": <k>, "quote": "<verbatim from turn k>", "why": "<one sentence>"}} ],
    "output":   {{"effect_in_output": true|false|"unassessable", "quote": "<verbatim from the final output, or empty>",
                 "cost_supplied": true|false|null, "cost_quote": "<verbatim from the final output, or empty>",
                 "why": "<one sentence>"}}
  }}
]}}

One entry per point, in the order given, every index present."""
