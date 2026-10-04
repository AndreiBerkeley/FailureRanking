## WHAT CORRECT WORK LOOKS LIKE HERE
{field_analysis}

## TRACES
{traces}

## TASK

Find every failure instance in these traces.

Take the traces one at a time, and each trace step by step, in order. A step
is any point where an agent did something: read its input, calculated,
reasoned, decided, called a tool, or produced output. For each step:

  1. Note what the agent was told to do and what it received.
  2. Check what it did. Redo it rather than reading it: recompute the
     numbers, confirm each fact is in its input, test whether each
     conclusion follows.
  3. If it is wrong, record a failure instance.

Check all three places (intake, work, output) at every step, and every step
to the end of the trace. Do not stop at the first failure: later steps can
be wrong on their own. Record small failures and failures that did not
change the final result.

Describe each instance by what went wrong. Do not name failure modes; that
is the next step.

Return ONLY JSON, one entry per trace, including traces where you found
nothing:
{"traces": [{"trace_id": "...",
             "steps_checked": <number of steps you checked>,
             "instances": [{"step": "which step: the agent and where in the trace",
                            "quote": "exact span of trace text showing it, or null if what went wrong is something missing",
                            "missing": "what required thing is missing and where it should have been, or null",
                            "what_went_wrong": "one line: what the agent did wrong",
                            "should_have": "what the step should have produced instead"}]}]}
