## THE TAXONOMY
{taxonomy}

## TRACE
{traces}

## CANDIDATE FAILURES
{failures}

## TASK

Each candidate above was recorded by one annotator who read this trace
without seeing the taxonomy. Some may not be failures.

For each candidate:

  1. Decide whether it is a failure instance as defined above. Find the step
     in the trace and redo it rather than reading the annotator's line:
     recompute the numbers, confirm each fact is in the agent's input, test
     whether each conclusion follows. It is not a failure if the
     instructions allow it, the input justifies it, or redoing the step shows
     it was right.
  2. If it is a failure, give it the single failure mode whose definition and
     when_to_use fit it, checking when_not_to_use. Do not stretch a mode to
     cover a failure it does not describe. If no mode fits, write "NONE" and
     say what kind of failure it is.

While checking, you may see failures in the trace that no candidate
describes. List each one under "missed", with its evidence and its mode in
the same way. Leave "missed" empty if you saw none.

Return ONLY JSON, one entry per candidate:
{"verdicts": [{"failure_id": "...",
               "is_failure": true | false,
               "why": "one line: why it is or is not a failure",
               "mode": "<mode id, or NONE; null if it is not a failure>",
               "none_fits": "if the mode is NONE, what kind of failure it is; otherwise null"}],
 "missed": [{"quote": "exact span of trace text showing it, or null if what went wrong is something missing",
             "missing": "what required thing is missing and where it should have been, or null",
             "what_went_wrong": "one line: what the agent did wrong",
             "mode": "<mode id, or NONE>",
             "none_fits": "if the mode is NONE, what kind of failure it is; otherwise null"}]}
