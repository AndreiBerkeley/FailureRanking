## VOCABULARY
{vocabulary}

Guide words:
{guide_words}

## THE MODES
{modes}

## TASK

Each mode above was built from failure instances. Its slots are what all of
its instances share; a slot given as "any" differs between them. Write the
fields name, definition, when_to_use and when_not_to_use of the FORMAT
above for each mode.

  name, definition  Say exactly what the slots say, no narrower and no
                    wider: the step kind when one is given, the requirement
                    or family broken, and how it was broken (the guide
                    word). Do not narrow a slot given as "any". Name a kind
                    of wrong action, as WHAT A GOOD FAILURE MODE IS says.
  when_to_use       what an instance must show to belong here, in terms of
                    the slots
  when_not_to_use   name each mode listed under "nearest" and the slot on
                    which it differs from this one. For each mode listed
                    under "takes_precedence", say that an instance that fits
                    it goes there instead.

The example instances only make the wording concrete; do not narrow the
mode to them. Keep the ids as given.

Return ONLY JSON:
{"modes": [{"id": "...", "name": "...", "definition": "...", "when_to_use": "...", "when_not_to_use": "..."}]}
