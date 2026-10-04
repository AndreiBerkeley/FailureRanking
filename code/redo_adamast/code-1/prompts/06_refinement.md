## THE TAXONOMY
{taxonomy}

## HOW CONSISTENTLY IT WAS APPLIED
{agreement}

## DISAGREEMENTS
{disagreements}

## INSTANCES NO MODE FITTED
{unfitted}

## TASK

Several annotators labelled the same failures with this taxonomy and then
discussed their disagreements. Above are how often they agreed on each mode,
the failures they still disagreed on after discussion, and the failures for
which no mode fitted. Improve the taxonomy so that it is applied
consistently and covers every failure.

  LOW AGREEMENT  A mode the annotators applied inconsistently usually has an
                 unclear definition or boundary. Rewrite its definition,
                 when_to_use and when_not_to_use so the disagreements above
                 would be settled.
  CONFUSED PAIR  Two modes the annotators used for the same instance: if
                 they are the same kind of wrong action, merge them; if not,
                 sharpen the boundary between them.
  NO MODE FITS   Group the unfitted instances by kind of wrong action. Where
                 an existing mode should have covered them, widen its
                 definition and give it their instance ids. Otherwise add a
                 new mode, with their instance ids.

Do not remove a mode unless it is merged into another. Report only your
changes: a mode you do not mention is kept exactly as it is, and instances
are carried over automatically (a merged mode keeps the instances of all its
modes), so never copy them.

Return ONLY JSON:
{"rewrites": [{"id": "...", "change": "rewritten | widened", "why": "...",
               "instance_ids": ["<unfitted instance ids it now covers>"],
               <only the fields you change, of "name", "definition", "when_to_use", "when_not_to_use">}],
 "merges": [{"ids": ["<ids of the modes merged>"], "name": "...", "definition": "...",
             "when_to_use": "...", "when_not_to_use": "...", "why": "..."}],
 "added": [{"name": "...", "definition": "...", "when_to_use": "...", "when_not_to_use": "...",
            "instance_ids": ["<unfitted instance ids it covers>"], "why": "..."}]}
