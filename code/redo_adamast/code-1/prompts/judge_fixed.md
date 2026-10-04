## THE TAXONOMY
{taxonomy}

## TRACE
{traces}

## TASK

Find every failure instance in the trace above, and give each one the
failure mode it belongs to.

Go through the trace step by step, in order, to the end. At each step, check
all three places (intake, work, output). Redo the step rather than reading
it: recompute the numbers, confirm each fact is in the agent's input, test
whether each conclusion follows. Record a failure instance wherever the step
is wrong, including small failures and failures that did not change the
final result.

Then give each instance the single mode whose definition and when_to_use fit
it, checking when_not_to_use. Do not stretch a mode to cover an instance it
does not describe. If no mode in the taxonomy fits, write "NONE" and say what
kind of failure it is; do not leave the instance out.

Some things look wrong at first and are not: the instructions allow them,
the input justifies them, or redoing the step shows it was right. List each
one you considered and rejected under "rejected", with the reason.

Return ONLY JSON:
{"trace_id": "...",
 "instances": [{"message": <index of the assistant message that holds the wrong action, or where the missing thing was owed>,
                "quote": "exact span of trace text showing it, or null if what went wrong is something missing",
                "missing": "what required thing is missing and where it should have been, or null",
                "what_went_wrong": "one line: what the agent did wrong",
                "mode": "<a mode id from the taxonomy, or NONE>",
                "none_fits": "if the mode is NONE, what kind of failure it is; otherwise null"}],
 "rejected": [{"message": <index of the message>,
               "quote": "exact span of trace text you considered",
               "why": "one line: why it is not a failure"}]}
