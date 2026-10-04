## WHAT CORRECT WORK LOOKS LIKE HERE
{field_analysis}

## VOCABULARY

Step kinds, requirement families and requirements of this system:
{vocabulary}

Guide words: how an action departed from a requirement.
{guide_words}

## FAILURE INSTANCES
{instances}

## TASK

Each record above is one failure instance found in a trace of this system.
Describe each one with the vocabulary, in three slots:

  step_kind    the kind of step where the wrong action happened
  requirement  the one requirement the wrong action broke. If it broke
               several, the one it broke most directly: the requirement the
               step was meeting when it went wrong, not a later consequence
  guide_word   how the action departed from that requirement; the one that
               fits best

Describe the wrong action, not its effect on the final result. Use only ids
and guide words from the vocabulary above.

  No requirement fits  give "NONE", write the requirement it broke in
                       "requirement_text" (one sentence, as what correct
                       work does), and give in "family" the family it
                       belongs to, or "NONE".
  No step kind fits    give "NONE".
  Not a failure        if the record shows no wrong action by the agent
                       (only an effect, a tool or environment problem, or
                       correct behaviour), set "not_a_failure" to true and
                       still fill the slots as well as you can.

Return ONLY JSON, one entry per record, in the order given:
{"slots": [{"id": "X1", "step_kind": "S1", "requirement": "R1", "family": null,
            "requirement_text": null, "guide_word": "NO", "not_a_failure": false}]}
("family" and "requirement_text" are null unless "requirement" is "NONE".)
