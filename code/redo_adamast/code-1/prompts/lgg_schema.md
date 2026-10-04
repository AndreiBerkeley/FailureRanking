## WHAT CORRECT WORK LOOKS LIKE HERE
{field_analysis}

## TASK

The description above may come in several parts, each written from
different traces of the same system. Turn it into a fixed vocabulary for
saying where an agent's action went wrong and which requirement it broke.
Do not look for failures: list what correct work requires.

  STEP KINDS    The kinds of step the work involves. Merge kinds from
                different parts when they are the same kind of step. Every
                step of a trace should belong to exactly one kind.

  REQUIREMENTS  Everything a step must do to be correct, split into single
                requirements: each says one thing that can be checked on
                its own. Split "does A and B without C" into A, B and
                "does not C". Use only what the description states or
                directly implies. A requirement that holds for several step
                kinds (for example, using only facts from the input) is
                listed once, with all its step kinds. State each as what
                correct work does, not as a failure.

  FAMILIES      Group the requirements into a few families of related
                requirements (for example grounding, completeness, format).
                Every requirement belongs to exactly one family.

Return ONLY JSON:
{"step_kinds": [{"id": "S1", "name": "a few words", "covers": "which steps of a trace belong here"}],
 "families": [{"id": "F1", "name": "a few words", "covers": "what its requirements have in common"}],
 "requirements": [{"id": "R1", "family": "F1", "step_kinds": ["S1"],
                   "requirement": "one sentence: one thing correct work does"}]}
