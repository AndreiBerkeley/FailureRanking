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
does not describe. If no mode in the taxonomy fits, propose a new mode for it
under "new_modes" (see WHAT A GOOD FAILURE MODE IS) and give the instance
that mode's id: NEW-1, NEW-2, ... If you propose more than one, make sure
they are distinct from each other: instances of the same kind of wrong
action share one new mode. New modes are added to the taxonomy after this
trace.

Some things look wrong at first and are not: the instructions allow them,
the input justifies them, or redoing the step shows it was right. List each
one you considered and rejected under "rejected", with the reason.

Return ONLY JSON:
{"trace_id": "...",
 "instances": [{"message": <index of the assistant message that holds the wrong action, or where the missing thing was owed>,
                "quote": "exact span of trace text showing it, or null if what went wrong is something missing",
                "missing": "what required thing is missing and where it should have been, or null",
                "what_went_wrong": "one line: what the agent did wrong",
                "mode": "<a mode id from the taxonomy, or NEW-k>"}],
 "new_modes": [{"id": "NEW-1", "name": "...", "definition": "...",
                "when_to_use": "...", "when_not_to_use": "..."}],
 "rejected": [{"message": <index of the message>,
               "quote": "exact span of trace text you considered",
               "why": "one line: why it is not a failure"}]}
