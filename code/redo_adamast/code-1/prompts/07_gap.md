## THE TAXONOMY
{taxonomy}

## TRACE
{traces}

## TASK

Find the failures this taxonomy does not cover, including failures that
could happen in this trace but did not. Each mode above comes with a few
example instances, to show what it covers.

Go through the trace step by step. At every step ask two questions:

  ACTUAL    Did the agent do something wrong here? If so, give it the mode
            in the taxonomy whose definition and when_to_use fit it,
            checking when_not_to_use and the examples. Report every actual
            failure, with its mode.
  POSSIBLE  What could an agent plausibly get wrong at this step, given what
            it was told and what it received? Report it only if no mode in
            the taxonomy would cover that failure.

  Example (POSSIBLE): a step receives a long list of search results and
  picks the first one. It happens to be the right one. An agent could just
  as well have picked a wrong result without checking it. If no mode covers
  that kind of wrong action, report it.

A mode covers a failure when it is the same kind of wrong action, even if
the situation, the tool or the effect differs from its examples. Propose a
new mode only when no mode covers the failure: then name the closest mode
and say why it does not fit. If you propose more than one new mode for this
trace, make sure they are distinct from each other. Keep possible failures
realistic for this system and this kind of step; do not invent failures that
nothing in the trace makes plausible.

Return ONLY JSON:
{"trace_id": "...",
 "gaps": [{"kind": "actual | possible",
           "step": "which step: the agent and where in the trace",
           "quote": "exact span of trace text at that step",
           "what": "what went wrong (actual) or what could go wrong (possible)",
           "mode": "<the mode id that covers it, or NEW>",
           "closest": "<for NEW: the id of the closest mode>",
           "why_not": "<for NEW: why the closest mode does not fit>",
           "proposed_mode": null, or for NEW {"name": "...", "definition": "...",
                                               "when_to_use": "...", "when_not_to_use": "..."}}]}
