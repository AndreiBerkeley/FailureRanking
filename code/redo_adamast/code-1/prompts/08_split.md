## THE TAXONOMY
{taxonomy}

## THE MODE TO EXAMINE
{mode}

## ITS INSTANCES
{instances}

## TASK

Decide whether the mode above should be split into two or more modes.

Split it only if all three hold:
  1. The parts do not overlap: every instance above fits exactly one part.
  2. Every part has at least one of the instances above.
  3. The parts are different kinds of wrong action, not the same wrong
     action in different situations (see WHAT A GOOD FAILURE MODE IS).

If any of the three fails, do not split. Most modes should not be split.

Return ONLY JSON:
{"split": true | false,
 "why": "...",
 "parts": [{"name": "...", "definition": "...", "when_to_use": "...",
            "when_not_to_use": "...",
            "instance_ids": ["<ids of the instances above that belong here>"]}]}
("parts" is [] when split is false.)
