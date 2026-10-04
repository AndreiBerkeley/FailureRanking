## THE TAXONOMY
{taxonomy}

## A STEP A HUMAN MARKED AS WRONG
{item}

## TASK

A human annotator read this run, marked the step above as where it went
wrong, and wrote the reason. The annotator knew the correct answer. Take the
annotator's judgement as given: the marked step holds a failure, as the
reason describes. Use the task, the step before, and the marked step's text
to understand what that failure is.

Give the failure the single mode whose definition and when_to_use fit it,
checking when_not_to_use. Do not stretch a mode to cover a failure it does
not describe. If no mode in the taxonomy fits, write "NONE" and say what
kind of failure it is.

Return ONLY JSON:
{"id": "...",
 "what_went_wrong": "one line: the failure, as the reason and the step text show it",
 "mode": "<a mode id from the taxonomy, or NONE>",
 "none_fits": "if the mode is NONE, what kind of failure it is; otherwise null",
 "why": "one line: why this mode, or why no mode fits"}
