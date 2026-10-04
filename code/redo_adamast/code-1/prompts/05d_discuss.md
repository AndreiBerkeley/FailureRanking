## THE TAXONOMY
{taxonomy}

## TRACE
{traces}

## FAILURES YOU AND THE OTHER ANNOTATORS LABELLED DIFFERENTLY
{disagreements}

## TASK

For each failure above you see your own label and reason, and the labels and
reasons of the other annotators. Look at the trace again and give your final
label. Change your label only if their reasons convince you that another mode
fits better; otherwise keep it.

Return ONLY JSON, one entry per failure:
{"labels": [{"failure_id": "...", "mode": "<mode id, or NONE>", "why": "one line"}]}
