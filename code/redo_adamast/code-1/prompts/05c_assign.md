## THE TAXONOMY
{taxonomy}

## TRACE
{traces}

## FAILURES TO CLASSIFY
{failures}

## TASK

Each failure above was found in this trace by several annotators working
independently. Assign each one the single failure mode whose definition and when_to_use fit
it, checking when_not_to_use. If no mode fits, write "NONE". Do not stretch a
mode to cover a failure it does not describe.

Return ONLY JSON, one entry per failure:
{"labels": [{"failure_id": "...", "mode": "<mode id, or NONE>", "why": "one line"}]}
