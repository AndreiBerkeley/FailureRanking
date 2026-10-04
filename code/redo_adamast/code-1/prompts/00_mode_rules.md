WHAT A GOOD FAILURE MODE IS

  General    It names a kind of wrong action, not a situation. Specific
             numbers, words, tasks and agents belong in its instances, not
             in the mode.
               Good: "arithmetic error"
               Bad:  "wrong total when adding prices"
  Recurring  It could apply to traces of this system you have not seen.
  Distinct   Every instance fits exactly one mode. If two modes could both
             describe the same instance, state the boundary between them,
             or merge them.
  Grounded   It rests on evidence in the traces: at least one instance
             found there (origin "observed"). Only the gap step may also add
             a mode that rests on a point where the failure could occur but
             did not (origin "anticipated").

No agent or role names in a mode; the agent is recorded on the instance.
A mode that occurs in most traces is still a mode; do not drop it for being
common.


FORMAT

Each failure mode has:

  id               a short stable id: FM-01, FM-02, ...
  name             a few words
  definition       one or two sentences: what the wrong action is
  when_to_use      what an instance must show to belong here
  when_not_to_use  the nearest other modes, and how to tell them apart
  origin           "observed" or "anticipated"
  instances        every instance it covers: instance id, trace id, the
                   quoted evidence span (or what is missing), and one line
                   saying what went wrong
  possible_at      anticipated modes only: where in a trace the failure
                   could occur (trace id, quote) and what could go wrong;
                   otherwise []

  Example:
  {"id": "FM-03",
   "name": "arithmetic error",
   "definition": "A calculation produces a wrong value from the values it was given.",
   "when_to_use": "The trace shows the calculation and its result, and the result is wrong for those values.",
   "when_not_to_use": "The values themselves were misread (misreading the input). A correct calculation was used where a different one was needed (wrong rule applied).",
   "origin": "observed",
   "instances": [{"instance_id": "I7", "trace_id": "t12",
                  "quote": "1 - 2 + 3 + 6 = 2", "missing": null,
                  "what_went_wrong": "1 - 2 + 3 + 6 is 8, not 2"}],
   "possible_at": []}
