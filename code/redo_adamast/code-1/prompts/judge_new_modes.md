## NEW FAILURE MODES
{modes}

## TASK

The modes above were proposed separately, each while judging a different
trace, for failure instances that no mode in the taxonomy fitted. They are
added to the taxonomy together, so they must be distinct from each other.

Where two or more are the same kind of wrong action (every instance under
one would fit the other just as well), merge them. Where they differ, keep
them apart; if the difference is not clear from their text, write it into
each one's when_not_to_use. Report only your changes: a mode you do not
mention is kept exactly as it is, and instances are carried over
automatically, so never copy them.

Return ONLY JSON:
{"merges": [{"ids": ["<ids of the modes merged>"], "name": "...", "definition": "...",
             "when_to_use": "...", "when_not_to_use": "...", "why": "..."}],
 "rewrites": [{"id": "...", "why": "...",
               <only the fields you change, of "name", "definition", "when_to_use", "when_not_to_use">}]}
