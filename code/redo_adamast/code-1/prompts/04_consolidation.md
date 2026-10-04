## DRAFT TAXONOMY
{modes}

## TASK

Check the draft above for two things only: duplicates and format. Do not
remove a mode for any other reason. Report only your changes: a mode you do
not mention is kept exactly as it is, and instances are carried over
automatically, so never copy them.

DUPLICATES. Merge two modes only if they are the same kind of wrong action:
every instance under one would fit the other just as well. If you can state
a difference a reader could apply, they are separate modes; write that
difference into each one's when_not_to_use. A merged mode keeps every
instance of the modes merged into it.

FORMAT. Check each mode against WHAT A GOOD FAILURE MODE IS and the FORMAT
above, and rewrite what does not comply:
  a name or definition that names a situation, a number, a task or an agent:
    rewrite it as the kind of wrong action, and keep the specifics in the
    instances;
  a missing or empty field: fill it;
  a when_not_to_use that does not name the nearest modes: name them.

Return ONLY JSON:
{"merges": [{"ids": ["<ids of the modes merged>"], "name": "...", "definition": "...",
             "when_to_use": "...", "when_not_to_use": "...", "why": "..."}],
 "rewrites": [{"id": "...", "why": "...",
               <only the fields you change, of "name", "definition", "when_to_use", "when_not_to_use">}]}
