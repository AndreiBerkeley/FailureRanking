## THE TAXONOMY
{taxonomy}

## A STEP A HUMAN MARKED AS WRONG
{item}

## TASK

A human annotator read this run, marked the step above as where it went
wrong, and wrote the reason. The annotator knew the correct answer; you see
the task, the step before the marked one, the marked step, and the
annotator's reason.

Check the reason against the step text; do not take it on trust. Then decide
what it describes:

  AGENT      a wrong action, decision or omission by the agent at the marked
             step, given what it was told to do and what it had received.
             This holds even when the reason is worded as an outcome, if the
             step text shows the wrong action behind it.
  NOT_AGENT  no wrong action by the agent at this step: only a tool or
             environment problem (a crash, an error page, a failed OCR or
             transcription, a search that lacks the page), or only an
             outcome (the step did not produce useful information) that the
             step text does not trace to a wrong action.

For AGENT, give the single mode whose definition and when_to_use fit the
failure, checking when_not_to_use. Do not stretch a mode to cover a failure
it does not describe. If no mode fits, write "NONE" and say what kind of
failure it is.

Return ONLY JSON:
{"id": "...",
 "verdict": "AGENT | NOT_AGENT",
 "what_went_wrong": "one line: the agent's wrong action, or for NOT_AGENT what the problem was",
 "mode": "<a mode id from the taxonomy, or NONE; null for NOT_AGENT>",
 "none_fits": "if the mode is NONE, what kind of failure it is; otherwise null",
 "why": "one line: why this mode, NONE or NOT_AGENT"}
