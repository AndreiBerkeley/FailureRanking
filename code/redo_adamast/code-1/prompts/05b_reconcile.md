## TRACE
{traces}

## FAILURE INSTANCES FOUND BY EACH ANNOTATOR
{findings}

## TASK

Several annotators read the trace above independently and each listed the
failure instances they found. Match the instances that describe the same
failure: the same wrong action at the same place in the trace, even if the
annotators worded it differently.

List every distinct failure once, with the annotators who found it. Keep
failures that only one annotator found; they are filtered later.

Return ONLY JSON:
{"failures": [{"found_by": ["<annotator ids, e.g. A1, A3>"],
               "quote": "exact span of trace text showing it, or null if something is missing",
               "missing": "what required thing is missing and where, or null",
               "what_went_wrong": "one line"}]}
