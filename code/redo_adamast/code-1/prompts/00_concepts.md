WHAT YOU ARE BUILDING

A failure taxonomy for one agent system: a list of every way it goes wrong,
drawn from traces of its runs. A trace records one run: for each step, what
the agent was told to do, what it received, and what it produced.

The aim is coverage: every wrong action the system takes should belong to
some failure mode on the list.

  EVIDENCE          an exact span of trace text where the agent went wrong.
  FAILURE INSTANCE  one wrong action inside that span. One span can hold
                    several instances.
  FAILURE MODE      the category of an instance: the kind of wrong action it
                    is. Each instance has exactly one mode; one mode collects
                    instances from many traces.
  TAXONOMY          the list of failure modes.

  Example: the task is "Add the numbers 1, 2, 3, 4, 5." The agent writes
  "1 - 2 + 3 + 6 = 2". One evidence span, three instances:
    subtracts 2 instead of adding it         (mode: not following the instruction)
    uses 6, not in the list; drops 4 and 5   (mode: misreading the input)
    1 - 2 + 3 + 6 is 8, not 2                (mode: arithmetic error)


A FAILURE IS THE REASON, NOT THE EFFECT

"The final answer is wrong" is an effect. A failure is the wrong action that
caused it.

  Example: asked "Is 91 prime?", the agent writes "91 is not divisible by 2,
  3 or 5, so it is prime." The wrong answer is the effect (91 = 7 x 13). The
  failure is that it stopped checking divisors after 5. (mode: incomplete
  check)

Count each failure once. The wrong answer above comes from the incomplete
check; it is not a second failure.

A failure counts even when the final result is right.

  Example: asked for the area of a 4 x 6 rectangle, the agent writes
  "4 + 6 = 10", then corrects itself to "4 x 6 = 24" and answers 24.
  "4 + 6 = 10" is still a failure instance. (mode: wrong rule applied)

Record only what the trace shows.

  Example: "Pens cost $3 and notebooks $5. Anna buys 4 pens and 2 notebooks
  and pays with $50. What is her change?" The agent writes only "Answer:
  $30." The answer is wrong ($28), but the trace does not show which step
  failed. Record no failure instance.


WHERE TO LOOK

Every step has three places where it can go wrong.

  INTAKE  reading the task, registering its constraints, taking in the
          material it was given.
          Example: task "Name three fruits that are not red." The agent
          answers "Strawberry, banana, mango." (mode: ignored a stated
          constraint)
  WORK    calculating, reasoning, comparing, judging, deciding what to do
          next.
          Example: a $120 jacket is 25% off. The agent computes $90, then
          concludes "$90 is less than $85." (mode: wrong comparison)
  OUTPUT  the form, structure and completeness of what it hands on.
          Example: told "return JSON with a field 'total'", the agent
          computes the total correctly and replies "The total is 42."
          (mode: wrong output format)


WHOSE FAILURE IS IT

When something in a trace is wrong, record it at the step that made it
wrong, not at every later step that used it. For each step ask: given what
it was told to do and what it received, did it do the right thing?

Normally a step should treat what it receives as correct. If what it
received was already wrong, the failure belongs to the earlier step that
produced it.

  Example: told "translate this text into Spanish", a step translates a
  wrong date exactly as written. The translation is right; the date was
  wrong before it arrived. Not this step's failure.

The exception is a step whose instructions tell it to check what it
receives. Missing an error there is its own failure.

  Example: told "correct any factual errors in this text", a step leaves
  "water boils at 50 C at sea level" unchanged. Its failure. (mode: missed
  error in checked input)


NOT THE SYSTEM'S FAILURE

Problems caused by the infrastructure are not failures of the agent system:
a tool that times out, a service that is down, a search index that lacks the
document. What the agent does next is still judged.

  Example: a web search returns "Error 503: service unavailable". That is
  not a failure. If the agent then writes "According to the search, the
  answer is 503", that is. (mode: treating an error message as content)


THE TRACES

The traces carry no outcome labels. Some runs succeeded and some did not,
and you are not told which. A run that ends with the right answer can still
contain failures, so read every trace with the same care.
