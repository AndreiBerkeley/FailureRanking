# Generation pipeline, v2 — proposal

Not implemented. Replaces the A/B/C decomposition with a two-column,
mechanism-based framework.

**The organising commitment:** the taxonomy names *failure mechanisms*. Who
produced it, where it happened, whether it breached a contract, what downstream
agents did about it, and what it cost are **occurrence properties**, recorded per
firing and never part of a code's identity.

**A note on the prompts below.** They state principles and then ground them.
Grounding describes *situations and the judgement they receive* — never a code
name to imitate. Naming and vocabulary are the generator's job, from its own
evidence. Every grounded block ends by directing the model back to the principle,
because five examples must not become five rules.

---

## Open question, to settle when the method meets a new benchmark

METHODOLOGY.md holds the candidate's construction inadmissible: only executions
are evidence. A consequence is that a candidate which writes itself a weak
contract and obeys it flawlessly reads as clean.

This does not bite on the three current benchmarks: none creates instructions at
runtime, so every agent contract is fixed before execution (verified). A program
that *delegates* during execution would produce instructions as observable
actions, attributable to the delegating agent under the ordinary contract rule.
**Revisit when a benchmark with runtime delegation arrives.**

Settled and not to be reopened: candidates are not normalised against each other.
A long instruction carries more detail and is harder to follow; a short one is
easier to follow and specifies less. Neither is better a priori, so nothing is
adjusted for it. The shared ruler is the taxonomy, not the instructions.

---

## The rules

1. **Contract** — an agent is judged against its own contract and its own input.
2. **Column** — decided by where in the agent's execution the mistake
   happened: at the edges (general) or in the middle (domain).
3. **Mechanism, not consequence** — a code names how a failure worked, never what
   it cost.
4. **Specialisation** — a new code only when the mechanism differs.

---

## Stages

| # | stage | cost | produces |
|---|---|---|---|
| 0a | structure | supplied | agents, roles, handoffs |
| 0b | contracts | free, extracted | per agent: instructions, inputs, outputs, clauses |
| 1 | field analysis | LLM | what solving this task requires |
| 2 | **observation** | LLM | per trace: what the program did wrong, quoted |
| 3 | **abstraction** | LLM | recurring mechanisms; the framework applies here |
| 4 | applicability | LLM | per (mode, agent): can occur / attribute / specialise |
| 5 | consolidation | LLM | one canonical taxonomy, stable ids |
| 6 | rule validation | LLM | every code against the rules, derived verdicts |

**Discovery is separated from filtering, and this is the load-bearing decision.**
An earlier version applied the whole framework during generation. Every rule in it
was individually right, and the effect was to suppress candidates before they were
written down: the model emitted only what was unimpeachable. Measured across three
benchmarks, that produced about a fifth of the vocabulary a vaguer prompt had
produced — one benchmark's entire taxonomy was a single code. A mode never
proposed cannot be corrected later.

So stage 2 asks only what happened, per trace, with evidence, under almost no
rules. Stage 3 receives those observations and applies the framework to them.
Filtering something already written down is a decision that can be inspected;
filtering something never written down is invisible.

Column assignment lives in stage 3, not in generation. Splitting generation by
column bought nothing: a reader of a trace reports what is in it regardless of
which column was asked for.

---

## Shared preamble (every generation prompt)

```
A failure mode names a MECHANISM by which a candidate program fails, observable
in an execution trace.

A code names the mechanism and nothing else. Who produced it, which output it
appeared in, whether it breached that agent's contract, what later agents did
about it, and what it cost are recorded PER OCCURRENCE. None of them belongs in a
code's name or definition.


WHAT COUNTS AS A FAILURE

An agent is judged against its own contract and its own input, and nothing else.
Content it received is INPUT, whatever produced it and whatever is wrong with it.
A failure is the gap between what the contract required of this agent and what it
did with what it was handed.

  Grounding

  An agent receives, from upstream, a statement that is false. Its contract is to
  act on what it is given, not to verify it. It acts on the statement. No gap: it
  did what it was contracted to do with what it was given. Not its failure. The
  failure belongs to whoever produced the false statement.

  A different agent receives that same statement. Its contract names verification
  as its job. It returns nothing. There is a gap: its contract named work it did
  not do. Its failure.

  An agent receives material and is contracted to represent it. What it produces
  asserts something the material does not contain. Gap. Its failure.

  An agent is contracted to produce a result from what it is given. What it was
  given does not determine one. It reports that. No gap: it described the state
  of its input accurately. Not its failure.

  That same agent instead produces a result anyway. Its contract did not license
  that. Gap. Its failure — and a new one, not the upstream shortfall passed on.

  Reason from the paragraph, not from these five. An agent contracted to check a
  format, to report insufficient input, to retry, or to reconcile conflicting
  sources creates a gap by not doing so, for the same reason and by the same
  test, and not because any of them appears here.


THE TWO COLUMNS

An agent does three things in order: it takes in what it was given, it does the
work, and it produces what it hands on. The column is decided by WHERE in that
sequence the mistake happened.

  GENERAL   at the edges. In taking in what it was given -- reading the task,
            registering its constraints, parsing the supplied material -- or in
            producing what it hands on -- the form, structure, completeness and
            conformance of the output.

  DOMAIN    in the middle. The work of solving, after the input was understood
            and before the output was formed: the calculations, inferences,
            comparisons, judgements, applications of a rule or definition, and
            decisions about what to do next that constitute doing the task.

The test is positional, and you can point at the moment: at what point in this
agent's execution did it go wrong? At an edge it is general. In between it is
domain.

This is why the columns are not two kinds of thing but two places. A mistake in
how a result was written down is general however domain-specific the result is.
A mistake in judging the material is domain however ordinary the judgement
sounds.

GROUNDING FOR THE COLUMNS

  A required section is absent from what an agent emitted. It happened while
  forming the output. GENERAL.

  An agent was given a condition in its task and proceeded as though it had not
  been stated. It happened while taking the task in. GENERAL.

  An agent computed a value incorrectly on the way to its result. Between intake
  and emission. DOMAIN.

  An agent concluded it had enough to finish when it did not. That is a decision
  about what to do next, taken in the middle of the work. DOMAIN.

  An agent asserted something the material it was given does not contain. It
  formed that claim while working, not while writing it down. DOMAIN.

  An agent produced a correct result and put it where a different thing was
  meant to go. Forming the output. GENERAL.

Reason from the sequence, not from these six. The question is always the same:
at what point in this agent's own execution did the mistake occur?

The columns are not alternatives to choose between. One trace can contain both,
and often does. Record each mechanism where it belongs; neither absorbs the other.

MECHANISM, NEVER CONSEQUENCE

A code names an operation that was performed incorrectly, or a required operation
that was not performed. It never names what that cost.

  The test: can you state what operation went wrong WITHOUT naming its downstream
  effect? If yes, it can be a code. If the only thing you can say is that the
  result or the verdict came out wrong, it is a consequence.

Consequences are recorded on the occurrence, never as codes, whether or not a
mechanism was also found.

  Grounding

  "The verdict came out wrong" names no operation. Consequence.

  "A check was performed and did not surface something that was present" names an
  operation that did not do what it was for, and says nothing about what followed.
  Mechanism.

  "A criterion was applied that does not hold" is also a mechanism, and it lies
  behind many wrong verdicts — but it may only be written when the trace SHOWS
  the criterion. Inferring it backwards from a wrong verdict is consequence-coding
  with an extra step.

  An agent takes a step that does not follow, and its result is therefore wrong.
  One mechanism: the step. The wrong result is its consequence, not a second
  failure.

  Do not stretch "consequence" to swallow observable operational failures. A
  malformed output, or a required element never emitted, is codeable: the failing
  operation is locally visible and you can say what was done wrong without
  reference to what it caused.


WHEN A BREACH HAS NO VISIBLE MECHANISM

Sometimes a trace shows plainly that a contract was breached while showing
nothing about how. Do not invent a mechanism, and do not fall back on naming the
consequence. Record an UNATTRIBUTED CONTRACT BREACH: the clause, the window in
which it should have been satisfied, and the statement that no mechanism is
visible. This is kept outside the taxonomy. A taxonomy that grows a code for
every unexplained breach is a taxonomy of consequences.


NAMING AND SCOPE

No agent or role name appears in any code, in either column, including
specialised ones. The agent is recorded on the occurrence.

A code's boundaries separate it from its neighbours by what is VISIBLE, never by
intent and never by outcome. No remedy, no routing, no advice in a code's
identity.

Choose your own vocabulary. Nothing above is a naming convention and no phrase in
it is a template.


GRANULARITY

A code names something that can recur. Two ways to get this wrong:

  Too narrow — it could only fire on the material it was taken from. If applying
  it requires the same specific object, quantity, or task shape to be present, it
  is an instance wearing a code's clothes.

  Too narrow in a second way — applying it requires first deciding what KIND of
  task this is. That makes the code a detector of task shape, and whether a task
  has a given shape is a fact about the task, not about the candidate.

  Too general — it would fire on most traces regardless of what the candidate did,
  and so separates nothing.

  The test: could this fire on material you have not seen, within this same
  domain? And would it fail to fire on a trace where the candidate did the work
  properly?


EVIDENCE

Every mode rests on observed behaviour, in one of two forms.

  POSITIVE          an exact span of trace text showing the failing action.

  BOUNDED ABSENCE   for a failure that IS an absence — something required that
                    never appears — quoting the failing sentence is impossible.
                    Record instead the contract clause establishing the
                    requirement, the complete window in which it should have
                    appeared, and a statement of what is missing from it.

Every quoted span must be an exact substring of the trace. A mode you can support
in neither form is a mode you invented, and it does not belong in the taxonomy
however plausible it sounds for this architecture.


ENVIRONMENT

Not every bad outcome is a candidate failure. The test: could a
DIFFERENTLY-DESIGNED candidate, on the same task and the same infrastructure,
have avoided it? Assume every task had sufficient resources and no orchestration
fault: a failure caused by how the pipeline was RUN is not a candidate failure;
one caused by how the candidate BEHAVES is.

  Grounding

  Resource exhaustion arising from how much the candidate generated, or from
  repetition it entered, or from context it accumulated without bound — a
  different design avoids it. Candidate. Keep.

  A transport error, an unavailable service, a corpus that does not contain the
  needed document, a harness defect — no design avoids it. Environment. Exclude.

  Reason from the test, not from these.


THE CORPUS YOU ARE READING

These traces are NOT filtered by outcome and carry no outcome labels. Some
succeeded, some did not, and you are not told which. This is deliberate: a task
that ends correctly can still contain false claims, wasted work, and real
failures that were later neutralised. Do not assume a trace is clean, and do not
look for a signal of overall success — there is none to find.
```

---

## Stage 0b — contract schema

Extracted mechanically from the system messages, which are the instructions
verbatim. One record per agent:

```
{ "agent": "<component name>",
  "instructions": "<the system message, verbatim>",
  "declared_inputs":  ["<field>", ...],
  "declared_outputs": ["<field>", ...],
  "clauses": [ {"id": "c1", "text": "<a single requirement, verbatim>"}, ... ],
  "upstream":   ["<agent>", ...],
  "downstream": ["<agent>", ...] }
```

`clauses` matter: bounded-absence evidence cites a clause id, so requirements must
be addressable. Splitting is mechanical (sentence or bullet), never paraphrased.

---

## Stage 1 — field analysis

```
## TRACES
{trace excerpts, outcome-blind}

## TASK

Describe the FIELD OF WORK these tasks belong to and what solving one requires.

("Field of work" here is the subject area — what kind of problem this is. It is
not the same word as the DOMAIN column, which is a position in an agent's
execution. Nothing in this stage concerns columns.)

You are not looking for failures. You are establishing what correct work looks
like here, so that a later stage can name the ways it goes wrong.

  field_of_work   what field of work this is
  task_form       what a task supplies and what it asks for
  reasoning_kinds the kinds of reasoning solving one requires, with a sentence on
                  what each involves in THIS field
  correctness     what makes an answer right here, and how that could be checked
                  from a trace
  subdomains      recurring varieties, if any, with rough frequency

Describe the field, not the problems you were shown. A statement that would only
be true of one task is too specific.

Return ONLY JSON.
```

---

## Stage 2 — observation, in two passes

Deliberately unconstrained. **The shared preamble is NOT prepended to either
pass.** Its rules are for deciding what belongs in a taxonomy; applied here they
suppress observations before they exist.

**The completeness invariant.** Three general things go wrong, and any failed run
should show at least one of them: what the program took in was mishandled; what
it produced was empty or malformed; or the work itself was wrong. The first and
third are the work pass — intake is the first step it checks — and the second is
the conformance pass. A run that failed and shows none of the three has not been
read carefully enough, and that is a measurable check on this stage rather than
an aspiration.

**Why two passes.** Run as one, conformance crowds out everything else. Measured
on one benchmark: 36 of 65 findings were a single formatting violation reported
over and over, while the actual reasoning errors in the same traces went
unexamined. Whether a rule was broken is visible at a glance; whether a step is
sound takes work, and a reader that has already found something wrong stops
looking. Separating them means neither can starve the other, and the reader doing
the work check is not shown the contracts at all, so it has nothing to fall back
on.

### 2a — the work

Few traces per call. This pass re-derives every step, which cannot be done at
skim depth across a large batch.

```
## HOW THE TRACES ARE LAID OUT

Each trace is a sequence of blocks. Blocks headed
`===== ENVIRONMENT · not an agent turn =====` are the task statement, tool or
retrieval results, and other material produced by the environment, not by an
agent. Each agent turn is enclosed in `===== TURN k · agent: NAME =====` ...
`===== end of turn k =====` and holds three sections, in this order:
  `--- instructions given to this agent ---`   that agent's own instructions
  `--- input this agent received ---`          what it was handed
  `--- output this agent produced ---`         what it produced
A block headed `===== OUTPUT WITHOUT PRECEDING INSTRUCTIONS ... =====` was
assembled by the harness and is not a turn.

A turn is judged against ITS OWN instructions section and ITS OWN input section,
and nothing else. Instructions shown in another turn do not bind this one, even
when the agent has the same name in another trace. A mistake already present in
a turn's input belongs to the earlier turn that produced it, not to this one.

## TRACES
{trace excerpts, outcome-blind}

## TASK

Take the traces ONE AT A TIME. Within each trace, take the TURNS ONE AT A TIME,
IN ORDER, and give an account of EVERY turn before moving to the next trace.
Environment blocks and harness-assembled output are not turns and get no entry.

For each turn, WALK THROUGH EVERY SUBSTANTIVE STEP THE AGENT TOOK IN ITS OUTPUT,
IN ORDER, AND CHECK EACH ONE BEFORE MOVING TO THE NEXT. A substantive step is any
point where the agent did work: a calculation, a transformation, a comparison,
an inference, an application of a rule or definition, a judgement about the
material, a decision about what to do next, a choice of what to carry forward.

THE FIRST STEP OF EVERY TURN IS INTAKE. Before anything else, check what this
agent understood from its own input section. Did it read the task correctly?
Did it register every constraint and condition stated there? Did it parse the
material it was given without corrupting or dropping any of it? Did it carry
forward what its input established, or did it drop an entity, a fact, or a
finding that was in front of it? An agent that starts from a misreading is wrong
from that point on, however sound everything after it looks.

ASSUME WHAT IT RECEIVED IS CORRECT, AND JUDGE ONLY WHAT IT DID WITH IT. If the
material in the input section was already wrong, acting on it is not this turn's
mistake — it belongs to the turn that produced it. But if the input was correct
and this agent misread, mishandled, ignored, or failed to carry forward part of
it, that IS its mistake, and it is exactly the kind this pass exists to catch.

RECOVERY DOES NOT EXCUSE A FAILURE. A mistake that a later turn caught, worked
around, or happened to compensate for is still a mistake and is still reported.

For each step, in order:
  1. State what the step did, in a few words.
  2. CHECK IT. Re-derive it yourself rather than reading it. Recompute the
     arithmetic. Confirm the fact is in this turn's input section. Test whether
     the conclusion follows from what precedes it. Confirm the rule, definition
     or principle invoked is stated correctly AND is the right one to invoke
     here. Verify the judgement against the material.
  3. Record "holds" or "fails". If it fails, say precisely what is wrong.

Do not skip a step because it looks routine. Do not stop at the first failure:
later steps can be independently wrong. Do not stop at the first turn: a query
or a summary late in the trace is checked with the same care as the first one,
and the LAST turns are where a run is most often lost. A turn that reads
fluently can still be wrong, and fluent wrong turns are the ones that matter.

You are NOT checking output formatting, required sections, or whether
instructions were followed. Ignore all of that here — it is examined separately.

Report EVERY step that fails, including several in one turn, including small
ones, and including ones that did not change the outcome.

Return ONLY JSON. There must be EXACTLY ONE entry per turn of each trace, in
turn order, whether or not anything failed. `steps_checked` is the number of
substantive steps you walked in that turn. `checked` says in one line what you
re-derived; when `findings` is empty it is the evidence that the turn was read
rather than skipped, so it must name what was verified, not say "ok":
{"traces": [{"trace_id": "...",
             "turns": [{"turn": <int, as in the turn header>,
                        "agent": "<name, as in the turn header>",
                        "steps_checked": <int>,
                        "checked": "<what was re-derived in this turn>",
                        "findings": [{"what_happened": "<what the step did and why it is wrong>",
                                      "where": "<which step of this turn>",
                                      "quote": "<shortest exact span showing it>" or null,
                                      "missing": null}]}]}]}
```

### 2a-ledger — the work, with the step ledger in the output

Same pass as 2a. The difference is the schema: the step-by-step check is
returned, not only counted. Measured on the 2a schema: the reader spent about
1,200 thinking tokens on a one-turn prompt and answered in 160, and the
`checked` lines described what the agent did rather than what was re-derived.
A schema that only asks for a count and a summary is satisfied by a skim; one
that asks for the ledger is not.

```
## HOW THE TRACES ARE LAID OUT

Each trace is a sequence of blocks. Blocks headed
`===== ENVIRONMENT · not an agent turn =====` are the task statement, tool or
retrieval results, and other material produced by the environment, not by an
agent. Each agent turn is enclosed in `===== TURN k · agent: NAME =====` ...
`===== end of turn k =====` and holds three sections, in this order:
  `--- instructions given to this agent ---`   that agent's own instructions
  `--- input this agent received ---`          what it was handed
  `--- output this agent produced ---`         what it produced
A block headed `===== OUTPUT WITHOUT PRECEDING INSTRUCTIONS ... =====` was
assembled by the harness and is not a turn.

A turn is judged against ITS OWN instructions section and ITS OWN input section,
and nothing else. Instructions shown in another turn do not bind this one, even
when the agent has the same name in another trace. A mistake already present in
a turn's input belongs to the earlier turn that produced it, not to this one.

## TRACES
{trace excerpts, outcome-blind}

## TASK

Take the traces ONE AT A TIME. Within each trace, take the TURNS ONE AT A TIME,
IN ORDER, and give an account of EVERY turn before moving to the next trace.
Environment blocks and harness-assembled output are not turns and get no entry.

For each turn, WALK THROUGH EVERY SUBSTANTIVE STEP THE AGENT TOOK IN ITS OUTPUT,
IN ORDER, AND CHECK EACH ONE BEFORE MOVING TO THE NEXT. A substantive step is any
point where the agent did work: a calculation, a transformation, a comparison,
an inference, an application of a rule or definition, a judgement about the
material, a decision about what to do next, a choice of what to carry forward.

THE FIRST STEP OF EVERY TURN IS INTAKE. Before anything else, check what this
agent understood from its own input section. Did it read the task correctly?
Did it register every constraint and condition stated there? Did it parse the
material it was given without corrupting or dropping any of it? Did it carry
forward what its input established, or did it drop an entity, a fact, or a
finding that was in front of it? An agent that starts from a misreading is wrong
from that point on, however sound everything after it looks.

ASSUME WHAT IT RECEIVED IS CORRECT, AND JUDGE ONLY WHAT IT DID WITH IT. If the
material in the input section was already wrong, acting on it is not this turn's
mistake — it belongs to the turn that produced it. But if the input was correct
and this agent misread, mishandled, ignored, or failed to carry forward part of
it, that IS its mistake, and it is exactly the kind this pass exists to catch.

RECOVERY DOES NOT EXCUSE A FAILURE. A mistake that a later turn caught, worked
around, or happened to compensate for is still a mistake and is still reported.

For each step, in order:
  1. State what the step did, in a few words.
  2. CHECK IT. Re-derive it yourself rather than reading it. Recompute the
     arithmetic. Confirm the fact is in this turn's input section. Test whether
     the conclusion follows from what precedes it. Confirm the rule, definition
     or principle invoked is stated correctly AND is the right one to invoke
     here. Verify the judgement against the material.
  3. Record "holds" or "fails". If it fails, say precisely what is wrong.

Do not skip a step because it looks routine. Do not stop at the first failure:
later steps can be independently wrong. Do not stop at the first turn: a query
or a summary late in the trace is checked with the same care as the first one,
and the LAST turns are where a run is most often lost. A turn that reads
fluently can still be wrong, and fluent wrong turns are the ones that matter.

You are NOT checking output formatting, required sections, or whether
instructions were followed. Ignore all of that here — it is examined separately.

Report EVERY step that fails, including several in one turn, including small
ones, and including ones that did not change the outcome.

Return ONLY JSON. There must be EXACTLY ONE entry per turn of each trace, in
turn order. Each turn carries a `steps` LEDGER: one entry per substantive step,
in order, with what the step did, what you did to check it, and the verdict.
The ledger IS the work. A verdict of "fails" must be backed by a finding for
that step; a verdict of "holds" must say what was compared against what, not
"looks correct". A turn whose ledger is one or two entries has not been walked.
{"traces": [{"trace_id": "...",
             "turns": [{"turn": <int, as in the turn header>,
                        "agent": "<name, as in the turn header>",
                        "steps": [{"step": "<what the step did, a few words>",
                                   "check": "<what you re-derived or compared, concretely>",
                                   "verdict": "holds" | "fails"}],
                        "findings": [{"what_happened": "<what the step did and why it is wrong>",
                                      "where": "<which step of this turn>",
                                      "quote": "<shortest exact span showing it>" or null,
                                      "missing": null}]}]}]}
```

### 2b — conformance

```
## HOW THE TRACES ARE LAID OUT

Each trace is a sequence of blocks. Blocks headed
`===== ENVIRONMENT · not an agent turn =====` are the task statement, tool or
retrieval results, and other material produced by the environment, not by an
agent. Each agent turn is enclosed in `===== TURN k · agent: NAME =====` ...
`===== end of turn k =====` and holds three sections, in this order:
  `--- instructions given to this agent ---`   that agent's own instructions
  `--- input this agent received ---`          what it was handed
  `--- output this agent produced ---`         what it produced
A block headed `===== OUTPUT WITHOUT PRECEDING INSTRUCTIONS ... =====` was
assembled by the harness and is not a turn.

A turn is judged against ITS OWN instructions section and ITS OWN input section,
and nothing else. Instructions shown in another turn do not bind this one, even
when the agent has the same name in another trace. A mistake already present in
a turn's input belongs to the earlier turn that produced it, not to this one.

## WHAT EACH AGENT WAS ASKED TO DO
{contracts}

The requirements above are the same text as the instructions sections inside
the turns, split into numbered clauses so a violation can cite one. Every trace
in this batch belongs to the same candidate program, so they apply to every
trace here. A clause listed under agent NAME binds only turns whose header names
NAME.

## TRACES
{trace excerpts, outcome-blind}

## TASK

Go through the traces ONE AT A TIME. Within each trace, go through the TURNS ONE
AT A TIME, IN ORDER, and give an account of EVERY turn. For each turn, compare
its output section against the requirements for that turn's agent, clause by
clause, and report every place the output does not meet them.

Check the whole output, to its last line. A required closing marker, a required
list header, a required field, is an absence at the END of an output, and is
missed by a reader that stopped reading once the content looked complete.

You are NOT judging whether the reasoning is correct or the answer is right.
Ignore all of that here; it is examined separately.

Report a violation whether it is large or small, and whether or not it seems to
have mattered. A violation that a later turn worked around, or that the final
output happened to survive, is still a violation and is still reported.
Repetition across traces is expected and useful.

Quote the SHORTEST span that shows it. If what is wrong is that something
required is MISSING, you cannot quote it — say what was required, citing the
clause, and where in the output it should have appeared.

Return ONLY JSON. There must be EXACTLY ONE entry per turn of each trace, in
turn order, whether or not anything was violated. `checked` names the clauses
you compared the output against; when `findings` is empty it is the evidence
that the turn was checked rather than skipped:
{"traces": [{"trace_id": "...",
             "turns": [{"turn": <int, as in the turn header>,
                        "agent": "<name, as in the turn header>",
                        "checked": "<which clauses were compared>",
                        "findings": [{"what_happened": "...",
                                      "where": "<which part of this turn's output>",
                                      "quote": "<exact text>" or null,
                                      "missing": "<what was required, citing the clause, and where>" or null}]}]}]}
```

---

## Stage 3 — abstraction

The framework applies here, to observations that already exist.

```
## OBSERVATIONS
{observations}

## THE FIELD OF WORK
{domain_analysis}

## WHAT THE PROGRAM WAS ASKED TO DO
{contracts}

## TASK

The observations above are individual incidents. Name the recurring MECHANISMS
behind them.

Each observation carries a "kind": "work" or "conformance", recording which pass
found it, and an "agent" and "turn" recording where in the program it was seen.
THE KIND IS NOT THE COLUMN AND MUST NOT BE COPIED INTO ONE. The agent is
evidence about where a mechanism lives, not a name for it: a mechanism is named
by the operation that went wrong, and whether it is specific to one agent is
decided later, from the incidents, not assumed from the label. The passes
divide the labour of looking; the columns divide where in an agent's execution a
mistake happened, and they do not line up. In particular the work pass checks
intake as its first step, and an intake mistake is GENERAL, not domain. Decide
every column yourself, from the positional test, on the evidence of the incident.

Work from the observations, not from what you expect to find. Group incidents
sharing a mechanism. An incident sharing a mechanism with nothing else is still a
mechanism if it could recur, and should be named.

For each mechanism assign its column by the positional test: at what point in the
agent's own execution did this go wrong — taking in, doing the work, or handing
on? Carry forward the incidents it covers, so its evidence traces back to what
was actually seen.

Account for every observation. Any you do not place goes in "unplaced" with a
reason. Do not silently drop one.

Everything in the preamble applies to what you WRITE. It does not apply to what
you were GIVEN: the observations are raw material and are allowed to be messy,
mis-scoped, or phrased as consequences. Your job is to find the mechanism behind
them, not to discard them for how they were reported.

You choose the vocabulary.

Return ONLY JSON:
{"modes": [{"name": "...", "column": "general"|"domain",
            "definition": "...", "when_to_use": "...", "when_not_to_use": "...",
            "incidents": [{"trace_id": "...", "quote": "..." or null,
                           "missing": "..." or null}]}],
 "unplaced": [{"observation": "...", "why": "..."}]}
```

---

## Stage 4 — applicability

```
## THE MODES
{all modes}

## THE AGENTS AND THEIR CONTRACTS
{contracts}

## TRACES
{trace excerpts, outcome-blind}

## TASK

For every (mode, agent) pair, answer in order.

1. CAN this agent exhibit this mechanism at all? Answer from its CONTRACT. An
   agent never asked to do a thing cannot fail at doing it. This question may be
   answered from the contract alone.

2. If it can: does this agent fail by a DIFFERENT MECHANISM than the mode
   describes, or by the SAME mechanism in a different place?

THE DEFAULT IS ATTRIBUTE, NOT SPECIALISE. The same mechanism in a different
output is the same failure and stays one code; the occurrence records which agent.
Only a different mechanism earns its own code, and appearing somewhere else is not
a difference in mechanism.

  Grounding

  Two agents each assert something their own inputs do not contain. Same
  mechanism, two places. One code, two attributions. ATTRIBUTE.

  One agent's contract is to preserve what it is given, and it drops part of it.
  Another's is to move the work forward, and what it produces does not. These are
  different mechanisms, not one mechanism in two places. SPECIALISE.

SPECIALISE REQUIRES EVIDENCE. You may answer can_occur from the contract; you may
not answer "specialise" from the contract. A specialised code needs an observed
instance, in a permitted evidence form, showing the different mechanism. If you
believe a distinction exists but cannot evidence it, answer "flag" — it is
recorded for later evidence collection, not turned into a code.

A specialised code is agent-free like every other, and held to the same
granularity and evidence checks.

Return ONLY JSON:
{"applicability": [{"mode":..., "agent":..., "can_occur": true|false,
                    "verdict": "attribute"|"specialise"|"flag", "why":...,
                    "specialised_code": {...with evidence...}}]}
```

---

## Stage 5 — consolidation

```
## ALL CODES
{all modes and specialised codes}

## TASK

Produce ONE canonical taxonomy: the finished set of codes, each with a stable id,
and a record of what became of every input code. Not a list of operations.

MERGE codes naming the same mechanism. Look specifically for one mechanism split
across agents or outputs — codes differing only in where they occurred are one
code.

MERGE ONLY TRUE DUPLICATES. Two tests, and both must pass:
  would the SAME correction to the program fix every incident under both codes?
  and could a reader, seeing the trace text alone, be unable to tell which of the
  two it is?
If you can state a boundary between two codes that a reader could apply, they are
NEIGHBOURS, not duplicates. Write the boundary into when_not_to_use and keep both.

Sharing a category is not sharing a mechanism. Several codes may all concern
output structure, or all concern the handling of evidence, and still be distinct
mechanisms — emitting the wrong KIND of thing is not the same failure as emitting
the right kind badly formatted, however similar their categories sound. Merging
across that line produces a code broad enough to fire on almost anything, which
separates nothing and is worse than the duplication it removed.

SPLIT a code covering two mechanisms.

CHECK COLUMNS. Two codes needing a when_not_to_use to separate them are
neighbours, and neighbours usually belong in the same column — but not always:
two mechanisms can have similar visible boundaries while operating on different
things. Where a boundary crosses columns, decide from the mechanism and say why.
Do not move a code to satisfy the heuristic.

IDS ARE STABLE AND NEVER REUSED. A merged code takes a new id and records its
sources; a retired id is never reassigned; a surviving code keeps its id.

Return ONLY JSON:
{"taxonomy": [{"id":..., "column":..., "name":..., "definition":...,
               "when_to_use":..., "when_not_to_use":..., "evidence": {...}}],
 "provenance": [{"from": [...], "to": ..., "operation": "keep|merge|split|retire",
                 "why": ...}]}
```

---

## Stage 6 — rule validation

Every field required, so a skipped check is a missing field rather than an
invisible omission. Verdicts are DERIVED, never asserted.

```
For every code, answer all of:

  column         "general" | "domain"
  column_ok      "yes" | "no"    (filed where its mechanism belongs)
  is_mechanism   "yes" | "no"    (can you state the operation that went wrong
                                  WITHOUT naming its downstream effect? if the
                                  only thing sayable is that the result came out
                                  wrong, this is a consequence)
  contract_ok    "yes" | "no"    (describes failure against the agent's OWN
                                  contract and input; no inherited, upstream,
                                  propagated or downstream content)
  agent_free     "yes" | "no"    (every code, both columns, specialised included)
  granularity    "ok" | "one_instance" | "task_shape" | "too_general"
  merged_from    [ids] | null   (taken from the provenance you are given)
  merge_ok       "yes" | "no" | "n/a"
                                 (for a merged code only: would ONE correction to
                                  the program fix every incident it absorbed? if a
                                  boundary could be stated between the codes that
                                  were merged, the merge was wrong and "n/a" is
                                  not an answer)
  observable     "yes" | "no"    (a judge could point at trace text or at a
                                  bounded absence)
  evidence_ok    "yes" | "no"    (permitted form; every span verified an exact
                                  substring)

There is NO verdict field. The verdict is DERIVED:
  observable=no, or evidence_ok=no   -> RETIRE
  is_mechanism=no                    -> REWRITE as a mechanism, or RETIRE if it
                                        is only the consequence of another code
  contract_ok=no                     -> REWRITE against own inputs
  column_ok=no                       -> MOVE column
  agent_free=no                      -> RENAME without the agent
  granularity != ok                  -> REWRITE at the right level
  merge_ok=no                        -> SPLIT back into the codes it absorbed,
                                        restoring their ids
  otherwise                          -> KEEP

Whenever a check is not ok, supply the corrected fields. Marking a code too narrow
without supplying a wider definition is an incomplete answer.

THEN EMIT THE CORRECTED TAXONOMY, not a list of verdicts. Apply every correction
you just derived, and after applying them look once more at the result:

  A rename can create a duplicate. If two codes only differed by the agent or the
  output field named in them, removing that name makes them the same code — merge
  them, under the merge test above.
  A code retired for being only the consequence of another leaves its incidents
  behind. Attach them to the code that explains them.

Return ONLY JSON:
{"checks": [{"id": ..., <every check field above> ...}],
 "taxonomy": [{"id": ..., "column": ..., "name": ..., "definition": ...,
               "when_to_use": ..., "when_not_to_use": ..., "evidence": {...}}],
 "corrections": [{"id": ..., "verdict": "KEEP|RETIRE|REWRITE|MOVE|RENAME|SPLIT|MERGE",
                  "why": ..., "into": ... }]}
```

---

## Stage 7 — refinement round

Generation says what the traces showed. A refinement round asks whether the
vocabulary is *written right*, using evidence generation could not have: the
judge's reading of a second, task-disjoint corpus. Three calls, none of which
sees the gate corpus.

The evidence base per code comes straight from the judge's records on the
refinement corpus: how often the code fired; how often the readers disagreed
about it (some reported it on a trace, others did not); problems the open
reader filed under it and how well it fitted them; and problems no code fitted
at all. Nothing is inferred from outcomes.

### 7a — reviewer checklist

Run once per reviewer, independently, at the panel temperature. Every reviewer
sees the same prompt.

```
## WHAT EACH AGENT WAS ASKED TO DO
{contracts}

## THE TAXONOMY, CODE BY CODE
{the taxonomy, code by code}

## THE EVIDENCE BASE
{evidence base}

## TASK: complete the checklist for EVERY code

Return one entry per code. Every field is required, including "code", which
must hold the code's exact id. A missing entry or field is an error.

  subject      "candidate" | "environment"
               Could a DIFFERENTLY-DESIGNED candidate, on the same task and the
               same infrastructure, have avoided it? Verbose generation that
               hits a token limit: yes, candidate. A retriever whose corpus
               lacks the document, an API error, a rate limit: no, environment.
  observable   "yes" | "no"        could a reader QUOTE trace text showing it
  mechanism    "ok" | "consequence" | "remedy"
               the code names HOW the failure worked; not what it cost, not
               what should have been done instead
  contract     "ok" | "none"       the code names a breach of something an agent
               was asked to do (a clause of its contract, or the task's
               requirement); "none" if it is not tied to any instruction
  column       "ok" | "general" | "domain"
               "ok" if the column is right; otherwise the column it belongs in.
               General: the mistake is at the edges of the agent's execution,
               in how it read its input or shaped its output. Domain: in the
               middle, in the work the agent does for this program.
  adequacy     "matches" | "too_narrow" | "too_broad" | "covers_two"
               Judge by the STRETCHED evidence and the reader disagreement: a
               code readers keep stretching to fit is too narrow; one they
               apply to unlike problems is too broad or covers two mechanisms.
  overlap      "none" | "<code id>"  another code that names the SAME mechanism
  reason       one sentence, citing the evidence you used

There is NO verdict field. The verdict is DERIVED from the checks, so a check
and a verdict can never contradict each other:
  subject environment or observable no          -> retire
  adequacy covers_two                            -> split
  anything else not ok / matches / candidate / yes / none -> edit
  otherwise                                      -> keep
THEREFORE: whenever any check is not ok, you MUST also supply the corrected
fields: "name", "definition", "when_to_use", "when_not_to_use", "column".
A code is edited, never deleted for thin evidence: a code that did not fire
on this corpus has not been shown not to occur.

Return ONLY JSON: {"checks":[{"code": "...", "subject": "...", "observable": "...",
"mechanism": "...", "contract": "...", "column": "...", "adequacy": "...",
"overlap": "...", "reason": "...", "name": "...", "definition": "...",
"when_to_use": "...", "when_not_to_use": "..."}]}
```

### 7b — consolidation

Run once, at temperature 0, only when the panel has more than one reviewer.

```
## THE TAXONOMY, CODE BY CODE
{the taxonomy, code by code}

## PANEL CHECKLISTS
{panel checklists}

## TASK: consolidate the panel

Several reviewers independently completed the per-code checklist above, seeing
the same evidence. Where they agree, keep the agreed value. Where they split,
decide FROM THE EVIDENCE they cite, never by counting votes: a lone reviewer
who quotes the trace outranks three who do not. For every code return the
final checklist entry, same fields and same rules as the reviewers, including
corrected fields wherever any check is not ok.

Return ONLY JSON: {"checks":[{...}]}
```

### 7c — operations

Run once, at temperature 0, after the checklist is final.

```
## WHAT EACH AGENT WAS ASKED TO DO
{contracts}

## THE TAXONOMY, CODE BY CODE
{the taxonomy, code by code}

## THE CONSOLIDATED CHECKLIST
{consolidated checklist}

## PROBLEMS NO CODE FITTED
{unmapped problems}

## TASK: cross-code operations

The checklist has already decided, code by code, what is retired and what is
edited. Decide only what requires seeing codes TOGETHER, or failures no code
covers.

- MERGE codes that name the same mechanism (use the overlap fields). The merged
  definition must cover everything its sources covered. The column is the one
  the merged mechanism belongs in.
- SPLIT any code whose checklist says covers_two. Each part names one
  mechanism; parts inherit the column unless the split is exactly along the
  column boundary.
- ADD only where the unfitted problems show a candidate behaviour that RECURS
  across traces. One occurrence is not a pattern. An environment failure is
  never a code. A new code obeys the same four rules as every other.

Return ONLY JSON:
{"merge":[{"codes":["<id>","<id>"],"column":"general|domain","name":"...","definition":"...","when_to_use":"...","when_not_to_use":"...","reason":"..."}],
 "split":[{"code":"<id>","reason":"...","into":[{"name":"...","definition":"...","when_to_use":"...","when_not_to_use":"...","column":"general|domain"}]}],
 "add":[{"column":"general|domain","name":"...","definition":"...","when_to_use":"...","when_not_to_use":"...","evidence_trace_ids":["..."],"reason":"..."}]}
```

After the operations are applied every surviving and new code receives a fresh
id in the round's own namespace (`R1_001`, `R1_002`, ...), with a provenance
entry saying which code or codes it came from and by which operation, so that a
result computed under the refined taxonomy can never be silently compared with
one computed under the draft. Retired codes are kept, with their definition and
the reason, outside the active list; ids are never reused.

---

## Stage 8 — interannotation gate, before freezing

Structural validation says the taxonomy is well written. Refinement says it is
written right for the evidence. Neither says independent readers can *use* it
alike. The gate measures that, on a corpus disjoint from generation and from
refinement, and never shown to the refiner.

The measurement judge reads the gate corpus with N independent readers
(default four), each holding the taxonomy, plus the open reader holding none.
No deliberation anywhere. From what they wrote down:

- **kappa**: Fleiss' kappa over subjects = (trace, code) pairs, each rated
  present or absent by every reader; reported per code and pooled over the
  codes at least one reader ever assigned. A code nobody assigned reads as
  perfect agreement on absence and is reported separately, not counted.
- **coverage**: the share of the open reader's problems that some code fits
  well, by the judge's own fitness verdict.

A taxonomy passes at pooled kappa ≥ 0.75 and coverage ≥ 0.70; both are
settable. The draft is measured once before any refinement (the baseline gate),
so the round's numbers have a reference. A taxonomy that fails gets another
refinement round if rounds remain; the default is one round, and the result
ships carrying its gate numbers either way.

The questions the earlier draft of this stage listed are answered as follows:
how many failure points have no code is coverage; how often readers disagree
and on which codes is the per-code kappa; which codes collapse together is the
overlap field of the checklist; whether some candidates' failures are
systematically easier to detect than others is *not* measured here and remains
open; whether every code can be applied without seeing the outcome is enforced
by construction, since the judge never receives one.

---

## The occurrence record

So much has moved out of the code that the occurrence schema is part of the design:

```
{ "code": "<stable id>",
  "agent": "<who exhibited the mechanism>",
  "breached_contract": true|false,
  "response": "propagated" | "detected" | "corrected" | "bypassed"
              | "amplified" | "contained" | null,
  "evidence": {...} }
```

`response` keeps propagation visible without counting it as failure. The contract
rule says an agent that faithfully consumed an upstream error did not fail; it
does not say what that agent did is uninteresting. Detection, correction and
containment are the recovery evidence FailureRank needs, and they are lost if only
the origin is recorded.
