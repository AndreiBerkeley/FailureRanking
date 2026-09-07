# Generation pipeline, v2

The taxonomy generator, its refinement round, and its gate. Implemented in
`new_pipeline/`: stages 1–6 in `generation/`, stage 7 in `refine.py`, stage 8 in
`gate.py`, with `run.py` driving them in order. It replaces the earlier A/B/C
decomposition with a two-column, mechanism-based framework.

**This document is the prompt source.** `generation/prompts.py` reads each
stage's fenced block from this file at import, so a prompt edited here is the
prompt sent, and a heading or placeholder that goes missing stops the run at
import instead of shipping a stale prompt. Every fenced block is therefore a
complete prompt as sent, with two conventions:

- The shared preamble is prepended by the loader to every prompt except the
  three stage-2 prompts, which run without it on purpose (see stage 2).
- Text in braces, such as `{contracts}`, is a field the code fills. The
  wording inside the braces is fixed; the loader matches it literally.

The three stage-2 prompts repeat the same paragraph describing the trace
layout. That is deliberate: each prompt can be read, and audited, on its own.

**Vocabulary.** A *mechanism* is how a failure worked. A *mode* is a mechanism
as named by stage 3. A *code* is a mode that has received a stable id, from
stage 5 on; the prompts use "mode" and "code" interchangeably. An *occurrence*
is one firing of a code on one trace. An agent's *contract* is its own
instructions, split into addressable clauses. A code's *column* is general or
domain, defined in the preamble.

**The organising commitment.** The taxonomy names *failure mechanisms*. Who
produced the failure, where it happened, whether it breached a contract, what
downstream agents did about it, and what it cost are **occurrence properties**,
recorded per firing and never part of a code's identity.

**How the prompts are written.** They state a principle and then ground it.
Grounding describes *situations and the judgement they receive*, never a code
name to imitate: naming and vocabulary are the generator's job, from its own
evidence. Every grounded block ends by directing the model back to the
principle, because five examples must not become five rules.

---

## Open question, to settle when the method meets a new benchmark

`pipeline/METHODOLOGY.md` holds a candidate's construction inadmissible: only
executions are evidence. A consequence is that a candidate which writes itself
a weak contract and obeys it flawlessly reads as clean.

This does not bite on the three current benchmarks. None creates instructions
at runtime, so every agent contract is fixed before execution (verified). A
program that *delegates* during execution would produce instructions as
observable actions, attributable to the delegating agent under the ordinary
contract rule. **Revisit when a benchmark with runtime delegation arrives.**

Settled, and not to be reopened: candidates are not normalised against each
other. A long instruction carries more detail and is harder to follow; a short
one is easier to follow and specifies less. Neither is better a priori, so
nothing is adjusted for it. The shared ruler is the taxonomy, not the
instructions.

---

## The rules

1. **Contract.** An agent is judged against its own contract and its own input.
2. **Column.** Decided by where in the agent's execution the mistake happened:
   at the edges (general) or in the middle (domain).
3. **Mechanism, not consequence.** A code names how a failure worked, never
   what it cost.
4. **Specialisation.** A new code only when the mechanism differs.

---

## Stages

| # | stage | cost | produces |
|---|---|---|---|
| 0a | structure | supplied | agents, roles, handoffs |
| 0b | contracts | free, extracted | per agent: instructions, inputs, outputs, clauses |
| 1 | field analysis | LLM | what solving this task requires |
| 2 | **observation** | LLM | per trace and turn: what the agent did wrong, quoted |
| 3 | **abstraction** | LLM | recurring mechanisms; the framework applies here |
| 4 | applicability | LLM | per (mode, agent): can occur / attribute / specialise |
| 5 | consolidation | LLM | one canonical taxonomy, stable ids |
| 6 | rule validation | LLM | every code against the rules, derived verdicts |
| 7 | refinement round | judge + LLM | the draft rewritten against a second corpus |
| 8 | interannotation gate | judge | kappa and coverage on a third corpus |

Stages 1–6 produce the draft. Stage 7 runs once by default and can repeat.
Stage 8 measures the draft once (the baseline) and the result of every round.
The follow-up checks that run after the gate are described at the end.

**Discovery is separated from filtering, and this is the load-bearing
decision.** An earlier version applied the whole framework during generation.
Every rule in it was individually right, and the effect was to suppress
candidates before they were written down: the model emitted only what was
unimpeachable. Measured across three benchmarks, that produced about a fifth of
the vocabulary a vaguer prompt had produced; one benchmark's entire taxonomy was
a single code. A mode never proposed cannot be corrected later.

So stage 2 asks only what happened, per trace, with evidence, under almost no
rules. Stage 3 receives those observations and applies the framework to them.
Filtering something already written down is a decision that can be inspected;
filtering something never written down is invisible.

Column assignment lives in stage 3, not in observation. Splitting observation
by column bought nothing: a reader of a trace reports what is in it regardless
of which column was asked for.

---

## Shared preamble (every generation prompt)

```
A failure mode names a MECHANISM by which a candidate program fails, observable
in an execution trace. A code is a mode that has been given a stable id; the
two words are used interchangeably below.

A code names the mechanism and nothing else. Who produced the failure, which
output it appeared in, whether it breached that agent's contract, what later
agents did about it, and what it cost are recorded PER OCCURRENCE. None of them
belongs in a code's name or definition.


WHAT COUNTS AS A FAILURE

An agent is judged against its own contract and its own input, and nothing
else. Whatever it received is INPUT, whoever produced it and whatever is wrong
with it. A failure is a gap between what the contract required of this agent
and what it did with what it was handed.

  Grounding

  An agent receives a false statement from upstream. Its contract is to act on
  what it is given, not to verify it. It acts on the statement. No gap: it did
  what it was contracted to do with what it was given. Not its failure; the
  failure belongs to whoever produced the statement.

  A different agent receives the same statement. Its contract names
  verification as its job. It returns nothing. Gap: its contract named work it
  did not do. Its failure.

  An agent is contracted to represent the material it receives. What it
  produces asserts something the material does not contain. Gap. Its failure.

  An agent is contracted to produce a result from what it is given, and what it
  is given does not determine one. It reports that. No gap: it described the
  state of its input accurately. Not its failure.

  The same agent produces a result anyway. Its contract did not license that.
  Gap. Its failure, and a new one, not the upstream shortfall passed on.

  Reason from the principle, not from these five. An agent contracted to check
  a format, to report insufficient input, to retry, or to reconcile conflicting
  sources creates a gap by not doing so, by the same test.


THE TWO COLUMNS

An agent does three things in order: it takes in what it was given, it does
the work, and it produces what it hands on. The column is decided by WHERE in
that sequence the mistake happened.

  GENERAL   at the edges. In taking in what it was given (reading the task,
            registering its constraints, parsing the supplied material) or in
            producing what it hands on (the form, structure, completeness and
            conformance of the output).

  DOMAIN    in the middle. The work of solving, after the input was understood
            and before the output was formed: the calculations, inferences,
            comparisons, judgements, applications of a rule or definition, and
            decisions about what to do next that constitute doing the task.

The test is positional, and you can point at the moment: at what point in this
agent's execution did it go wrong? At an edge it is general. In between it is
domain. The columns are two places, not two kinds of thing. A mistake in how a
result was written down is general however domain-specific the result is. A
mistake in judging the material is domain however ordinary the judgement
sounds.

  Grounding

  A required section is absent from what an agent emitted. It happened while
  forming the output. GENERAL.

  An agent was given a condition in its task and proceeded as though it had
  not been stated. It happened while taking the task in. GENERAL.

  An agent computed a value incorrectly on the way to its result. Between
  intake and emission. DOMAIN.

  An agent concluded it had enough to finish when it did not. A decision about
  what to do next, taken in the middle of the work. DOMAIN.

  An agent asserted something the material it was given does not contain. It
  formed that claim while working, not while writing it down. DOMAIN.

  An agent produced a correct result and put it where a different thing was
  meant to go. Forming the output. GENERAL.

  Reason from the sequence, not from these six. The question is always the
  same: at what point in this agent's own execution did the mistake occur?

The columns are not alternatives to choose between. One trace can contain
both, and often does. Record each mechanism where it belongs; neither absorbs
the other.


MECHANISM, NEVER CONSEQUENCE

A code names an operation that was performed incorrectly, or a required
operation that was not performed. It never names what that cost.

  The test: can you state what operation went wrong WITHOUT naming its
  downstream effect? If yes, it can be a code. If the only thing you can say
  is that the result or the verdict came out wrong, it is a consequence.

Consequences are recorded on the occurrence, never as codes, whether or not a
mechanism was also found.

  Grounding

  "The verdict came out wrong" names no operation. Consequence.

  "A check was performed and did not surface something that was present"
  names an operation that did not do what it was for, and says nothing about
  what followed. Mechanism.

  "A criterion was applied that does not hold" is also a mechanism, and it
  lies behind many wrong verdicts. It may only be written when the trace SHOWS
  the criterion. Inferring it backwards from a wrong verdict is
  consequence-coding with an extra step.

  An agent takes a step that does not follow, and its result is therefore
  wrong. One mechanism: the step. The wrong result is its consequence, not a
  second failure.

  A malformed output, or a required element never emitted, IS a mechanism:
  the failing operation is locally visible and can be stated without
  reference to what it caused. Do not stretch "consequence" to swallow
  observable operational failures.

  Reason from the test, not from these five.


WHEN A BREACH HAS NO VISIBLE MECHANISM

Sometimes a trace shows plainly that a contract was breached while showing
nothing about how. Do not invent a mechanism, and do not fall back on naming
the consequence. Record an UNATTRIBUTED CONTRACT BREACH: the clause, the window
in which it should have been satisfied, and the statement that no mechanism is
visible. This is kept outside the taxonomy. A taxonomy that grows a code for
every unexplained breach is a taxonomy of consequences.


NAMING AND SCOPE

No agent or role name appears in any code, in either column, specialised codes
included. The agent is recorded on the occurrence.

A code's boundaries separate it from its neighbours by what is VISIBLE, never
by intent and never by outcome. No remedy, no routing, no advice in a code's
identity.

Choose your own vocabulary. Nothing above is a naming convention and no phrase
in it is a template.


GRANULARITY

A code names something that can recur. Three ways to get this wrong:

  An instance    it could only fire on the material it was taken from. If
                 applying it requires the same specific object, quantity, or
                 task shape to be present, it is an instance wearing a code's
                 clothes.

  A task detector  applying it requires first deciding what KIND of task this
                 is. Whether a task has a given shape is a fact about the
                 task, not about the candidate.

  A constant     it would fire on most traces regardless of what the candidate
                 did, and so separates nothing.

  The test: could this fire on material you have not seen, within this same
  field of work? And would it fail to fire on a trace where the candidate did
  the work properly?


EVIDENCE

Every mode rests on observed behaviour, in one of two forms.

  POSITIVE          an exact span of trace text showing the failing action.

  BOUNDED ABSENCE   for a failure that IS an absence, something required that
                    never appears, there is no failing sentence to quote.
                    Record instead the contract clause establishing the
                    requirement, the complete window in which it should have
                    appeared, and a statement of what is missing from it.

Every quoted span must be an exact substring of the trace. A mode you can
support in neither form is a mode you invented, and it does not belong in the
taxonomy however plausible it sounds for this architecture.


ENVIRONMENT

Not every bad outcome is a candidate failure. The test: could a
DIFFERENTLY-DESIGNED candidate, on the same task and the same infrastructure,
have avoided it? Assume every task had sufficient resources and no
orchestration fault. A failure caused by how the pipeline was RUN is not a
candidate failure; one caused by how the candidate BEHAVES is.

  Grounding

  Resource exhaustion arising from how much the candidate generated, from
  repetition it entered, or from context it accumulated without bound. A
  different design avoids it. Candidate. Keep.

  A transport error, an unavailable service, a corpus that does not contain
  the needed document, a harness defect. No design avoids it. Environment.
  Exclude.

  Reason from the test, not from these.


THE CORPUS YOU ARE READING

These traces are NOT filtered by outcome and carry no outcome labels. Some
succeeded, some did not, and you are not told which. This is deliberate: a
task that ends correctly can still contain false claims, wasted work, and real
failures that were later neutralised. Do not assume a trace is clean, and do
not look for a signal of overall success. There is none to find.
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

`clauses` matter: bounded-absence evidence cites a clause id, so requirements
must be addressable. Splitting is mechanical (sentence or bullet), never
paraphrased.

---

## Stage 1 — field analysis

One call over a sample of traces. Its output is shown to stage 3 so that
mechanisms are named against what correct work looks like here.

```
## TRACES
{trace excerpts, outcome-blind}

## TASK

Describe the FIELD OF WORK these tasks belong to and what solving one
requires.

"Field of work" is the subject area: what kind of problem this is. It is not
the DOMAIN column, which is a position in an agent's execution. Nothing in this
stage concerns columns.

You are not looking for failures. You are establishing what correct work looks
like here, so that a later stage can name the ways it goes wrong.

  field_of_work    what field of work this is
  task_form        what a task supplies and what it asks for
  reasoning_kinds  the kinds of reasoning solving one requires, each with a
                   sentence on what it involves in THIS field
  correctness      what makes an answer right here, and how that could be
                   checked from a trace
  subdomains       recurring varieties, if any, with a rough share of tasks

Describe the field, not the tasks you were shown. A statement that would only
be true of one task is too specific.

Return ONLY JSON:
{"field_of_work": "...",
 "task_form": "...",
 "reasoning_kinds": [{"kind": "...", "involves": "..."}],
 "correctness": "...",
 "subdomains": [{"name": "...", "share": "..."}]}
```

---

## Stage 2 — observation, in two passes

Deliberately unconstrained. **The shared preamble is NOT prepended to any
stage-2 prompt.** Its rules are for deciding what belongs in a taxonomy;
applied here they suppress observations before they exist.

**The completeness invariant.** Three general things go wrong, and any failed
run should show at least one of them: what the program took in was mishandled;
what it produced was empty or malformed; or the work itself was wrong. The first
and third are the work pass, which checks intake as its first step; the second
is the conformance pass. A run that failed and shows none of the three has not
been read carefully enough. That is a measurable check on this stage, not an
aspiration.

**Why two passes.** Run as one, conformance crowds out everything else.
Measured on one benchmark: 36 of 65 findings were a single formatting violation
reported over and over, while the reasoning errors in the same traces went
unexamined. Whether a rule was broken is visible at a glance; whether a step is
sound takes work, and a reader that has already found something wrong stops
looking. Separating them means neither can starve the other. The reader doing
the work check is not shown the contracts at all, so it has nothing to fall
back on.

**Two schemas for the work pass.** 2a returns, per turn, a count of the steps
walked and a one-line account; 2a-ledger returns the step-by-step check itself.
Measured on the 2a schema, the reader spent about 1,200 thinking tokens on a
one-turn prompt, answered in 160, and its account described what the agent did
rather than what was re-derived. A schema that asks for a count and a summary
is satisfied by a skim; one that asks for the ledger is not. The generator's
`--work-ledger` flag selects 2a-ledger; the orchestrator runs 2a unless told
otherwise. Both prompts are identical except for the OUTPUT section.

**Few traces per call.** The work pass re-derives every step, which cannot be
done at skim depth across a large batch.

### 2a — the work

```
## HOW THE TRACES ARE LAID OUT

Each trace is a sequence of blocks.

  `===== ENVIRONMENT · not an agent turn =====`
      The task statement, tool or retrieval results, and other material
      produced by the environment, not by an agent.

  `===== TURN k · agent: NAME =====` ... `===== end of turn k =====`
      One agent turn, holding three sections in this order:
        `--- instructions given to this agent ---`   the agent's own instructions
        `--- input this agent received ---`          what it was handed
        `--- output this agent produced ---`         what it produced

  `===== OUTPUT WITHOUT PRECEDING INSTRUCTIONS ... =====`
      Assembled by the harness. Not a turn.

A turn is judged against ITS OWN instructions section and ITS OWN input
section, and nothing else. Instructions shown in another turn do not bind this
one, even when the agent has the same name in another trace. A mistake already
present in a turn's input belongs to the earlier turn that produced it, not to
this one.

## TRACES
{trace excerpts, outcome-blind}

## TASK

Take the traces ONE AT A TIME. Within each trace, take the turns ONE AT A TIME,
in order, and account for EVERY turn before moving to the next trace.
Environment blocks and harness-assembled output are not turns and get no
entry.

Within each turn, walk through EVERY SUBSTANTIVE STEP the agent took in its
output, in order, and check each one before moving to the next. A substantive
step is any point where the agent did work: a calculation, a transformation, a
comparison, an inference, an application of a rule or definition, a judgement
about the material, a decision about what to do next, a choice of what to
carry forward.

THE FIRST STEP OF EVERY TURN IS INTAKE. Before anything else, check what the
agent took from its own input section. Did it read the task correctly? Did it
register every constraint and condition stated there? Did it parse the
material it was given without corrupting or dropping any of it? Did it carry
forward what its input established, or did it lose an entity, a fact, or a
finding that was in front of it? An agent that starts from a misreading is
wrong from that point on, however sound everything after it looks.

TAKE THE INPUT AS GIVEN AND JUDGE ONLY WHAT THE AGENT DID WITH IT. If the input
section was already wrong, acting on it is not this turn's mistake; it belongs
to the turn that produced it. If the input was right and this agent misread,
mishandled, ignored, or failed to carry forward part of it, that IS its
mistake, and it is exactly what this pass exists to catch.

RECOVERY DOES NOT EXCUSE A FAILURE. A mistake that a later turn caught, worked
around, or happened to compensate for is still a mistake and is still
reported.

For each step, in order:
  1. State what the step did, in a few words.
  2. CHECK IT. Re-derive it rather than reading it. Recompute the arithmetic.
     Confirm the fact is in this turn's input section. Test whether the
     conclusion follows from what precedes it. Confirm the rule, definition or
     principle invoked is stated correctly AND is the right one to invoke
     here. Verify the judgement against the material.
  3. Record "holds" or "fails". If it fails, say precisely what is wrong.

Do not skip a step because it looks routine. Do not stop at the first failure:
later steps can be independently wrong. Do not stop at the first turn: a query
or a summary late in the trace is checked with the same care as the first one,
and the last turns are where a run is most often lost. A turn that reads
fluently can still be wrong, and fluent wrong turns are the ones that matter.

You are NOT checking output formatting, required sections, or whether
instructions were followed. Ignore all of that here; it is examined
separately.

Report EVERY step that fails: several in one turn, small ones, and ones that
did not change the outcome.

## OUTPUT

Return ONLY JSON, with EXACTLY ONE entry per turn of each trace, in turn order,
whether or not anything failed.

  steps_checked  the number of substantive steps you walked in that turn.
  checked        one line saying what you re-derived. When findings is empty
                 this line is the only evidence that the turn was read rather
                 than skipped, so it names what was verified; "ok" is not an
                 answer.
  findings       one entry per failing step. A failure that is an ABSENCE (a
                 fact dropped, an entity not carried forward) has no span to
                 quote: leave quote null and say in missing what is absent and
                 where it should have appeared.

{"traces": [{"trace_id": "...",
             "turns": [{"turn": <int, as in the turn header>,
                        "agent": "<name, as in the turn header>",
                        "steps_checked": <int>,
                        "checked": "<what was re-derived in this turn>",
                        "findings": [{"what_happened": "<what the step did and why it is wrong>",
                                      "where": "<which step of this turn>",
                                      "quote": "<shortest exact span showing it>" or null,
                                      "missing": "<what is absent, and where it should have been>" or null}]}]}]}
```

### 2a-ledger — the work, with the step ledger in the output

```
## HOW THE TRACES ARE LAID OUT

Each trace is a sequence of blocks.

  `===== ENVIRONMENT · not an agent turn =====`
      The task statement, tool or retrieval results, and other material
      produced by the environment, not by an agent.

  `===== TURN k · agent: NAME =====` ... `===== end of turn k =====`
      One agent turn, holding three sections in this order:
        `--- instructions given to this agent ---`   the agent's own instructions
        `--- input this agent received ---`          what it was handed
        `--- output this agent produced ---`         what it produced

  `===== OUTPUT WITHOUT PRECEDING INSTRUCTIONS ... =====`
      Assembled by the harness. Not a turn.

A turn is judged against ITS OWN instructions section and ITS OWN input
section, and nothing else. Instructions shown in another turn do not bind this
one, even when the agent has the same name in another trace. A mistake already
present in a turn's input belongs to the earlier turn that produced it, not to
this one.

## TRACES
{trace excerpts, outcome-blind}

## TASK

Take the traces ONE AT A TIME. Within each trace, take the turns ONE AT A TIME,
in order, and account for EVERY turn before moving to the next trace.
Environment blocks and harness-assembled output are not turns and get no
entry.

Within each turn, walk through EVERY SUBSTANTIVE STEP the agent took in its
output, in order, and check each one before moving to the next. A substantive
step is any point where the agent did work: a calculation, a transformation, a
comparison, an inference, an application of a rule or definition, a judgement
about the material, a decision about what to do next, a choice of what to
carry forward.

THE FIRST STEP OF EVERY TURN IS INTAKE. Before anything else, check what the
agent took from its own input section. Did it read the task correctly? Did it
register every constraint and condition stated there? Did it parse the
material it was given without corrupting or dropping any of it? Did it carry
forward what its input established, or did it lose an entity, a fact, or a
finding that was in front of it? An agent that starts from a misreading is
wrong from that point on, however sound everything after it looks.

TAKE THE INPUT AS GIVEN AND JUDGE ONLY WHAT THE AGENT DID WITH IT. If the input
section was already wrong, acting on it is not this turn's mistake; it belongs
to the turn that produced it. If the input was right and this agent misread,
mishandled, ignored, or failed to carry forward part of it, that IS its
mistake, and it is exactly what this pass exists to catch.

RECOVERY DOES NOT EXCUSE A FAILURE. A mistake that a later turn caught, worked
around, or happened to compensate for is still a mistake and is still
reported.

For each step, in order:
  1. State what the step did, in a few words.
  2. CHECK IT. Re-derive it rather than reading it. Recompute the arithmetic.
     Confirm the fact is in this turn's input section. Test whether the
     conclusion follows from what precedes it. Confirm the rule, definition or
     principle invoked is stated correctly AND is the right one to invoke
     here. Verify the judgement against the material.
  3. Record "holds" or "fails". If it fails, say precisely what is wrong.

Do not skip a step because it looks routine. Do not stop at the first failure:
later steps can be independently wrong. Do not stop at the first turn: a query
or a summary late in the trace is checked with the same care as the first one,
and the last turns are where a run is most often lost. A turn that reads
fluently can still be wrong, and fluent wrong turns are the ones that matter.

You are NOT checking output formatting, required sections, or whether
instructions were followed. Ignore all of that here; it is examined
separately.

Report EVERY step that fails: several in one turn, small ones, and ones that
did not change the outcome.

## OUTPUT

Return ONLY JSON, with EXACTLY ONE entry per turn of each trace, in turn order,
whether or not anything failed.

  steps     the LEDGER: one entry per substantive step, in order, with what
            the step did, what you did to check it, and the verdict. The ledger
            IS the work. A verdict of "fails" must be backed by a finding for
            that step. A verdict of "holds" says what was compared against
            what; "looks correct" is not a check. A turn whose ledger has one
            or two entries has not been walked.
  findings  one entry per failing step. A failure that is an ABSENCE (a fact
            dropped, an entity not carried forward) has no span to quote:
            leave quote null and say in missing what is absent and where it
            should have appeared.

{"traces": [{"trace_id": "...",
             "turns": [{"turn": <int, as in the turn header>,
                        "agent": "<name, as in the turn header>",
                        "steps": [{"step": "<what the step did, a few words>",
                                   "check": "<what you re-derived or compared, concretely>",
                                   "verdict": "holds" | "fails"}],
                        "findings": [{"what_happened": "<what the step did and why it is wrong>",
                                      "where": "<which step of this turn>",
                                      "quote": "<shortest exact span showing it>" or null,
                                      "missing": "<what is absent, and where it should have been>" or null}]}]}]}
```

### 2b — conformance

```
## HOW THE TRACES ARE LAID OUT

Each trace is a sequence of blocks.

  `===== ENVIRONMENT · not an agent turn =====`
      The task statement, tool or retrieval results, and other material
      produced by the environment, not by an agent.

  `===== TURN k · agent: NAME =====` ... `===== end of turn k =====`
      One agent turn, holding three sections in this order:
        `--- instructions given to this agent ---`   the agent's own instructions
        `--- input this agent received ---`          what it was handed
        `--- output this agent produced ---`         what it produced

  `===== OUTPUT WITHOUT PRECEDING INSTRUCTIONS ... =====`
      Assembled by the harness. Not a turn.

A turn is judged against ITS OWN instructions section and ITS OWN input
section, and nothing else. Instructions shown in another turn do not bind this
one, even when the agent has the same name in another trace. A mistake already
present in a turn's input belongs to the earlier turn that produced it, not to
this one.

## WHAT EACH AGENT WAS ASKED TO DO
{contracts}

The requirements above are the same text as the instructions sections inside
the turns, split into numbered clauses so that a violation can cite one. Every
trace in this batch belongs to the same candidate program, so the requirements
apply to every trace here. A clause listed under agent NAME binds only the
turns whose header names NAME.

## TRACES
{trace excerpts, outcome-blind}

## TASK

Take the traces ONE AT A TIME. Within each trace, take the turns ONE AT A TIME,
in order, and account for EVERY turn. For each turn, compare its output
section against the clauses for that turn's agent, clause by clause, and
report every place the output does not meet them.

Check the whole output, to its last line. A required closing marker, a
required list header, a required field: these are absences at the END of an
output, and a reader that stopped once the content looked complete misses
them.

You are NOT judging whether the reasoning is correct or the answer is right.
Ignore all of that here; it is examined separately.

Report a violation whether it is large or small, and whether or not it seems
to have mattered. A violation that a later turn worked around, or that the
final output happened to survive, is still a violation and is still reported.
Repetition across traces is expected and useful.

Quote the SHORTEST span that shows the violation. When what is wrong is that
something required is MISSING, there is nothing to quote: say what was
required, citing the clause, and where in the output it should have appeared.

## OUTPUT

Return ONLY JSON, with EXACTLY ONE entry per turn of each trace, in turn order,
whether or not anything was violated. `checked` names the clauses you compared
the output against; when findings is empty it is the evidence that the turn
was checked rather than skipped.

{"traces": [{"trace_id": "...",
             "turns": [{"turn": <int, as in the turn header>,
                        "agent": "<name, as in the turn header>",
                        "checked": "<which clauses were compared>",
                        "findings": [{"what_happened": "<what the output does, and which clause it fails>",
                                      "where": "<which part of this turn's output>",
                                      "quote": "<exact text>" or null,
                                      "missing": "<what was required, citing the clause, and where>" or null}]}]}]}
```

---

## Stage 3 — abstraction

The framework applies here, to observations that already exist. The
observations are the stage-2 findings of both passes, each stamped with the
pass that found it (`kind`), the agent, and the turn.

```
## OBSERVATIONS
{observations}

## THE FIELD OF WORK
{domain_analysis}

## WHAT THE PROGRAM WAS ASKED TO DO
{contracts}

## TASK

The observations above are individual incidents. Name the recurring
MECHANISMS behind them.

Each observation carries three labels that say how it was found, not what it
is:

  kind    "work" or "conformance": the pass that reported it. THE KIND IS NOT
          THE COLUMN and is not copied into one. The passes divide the labour
          of looking; the columns divide where in an agent's execution the
          mistake happened; the two do not line up. The work pass checks
          intake as its first step, and an intake mistake is GENERAL.
  agent   where in the program it was seen. Evidence about where a mechanism
          lives, not a name for it. A mechanism is named by the operation that
          went wrong; whether it is specific to one agent is decided later,
          from the incidents, not assumed from the label.
  turn    likewise.

Decide every column yourself, from the positional test, on the evidence of the
incident.

Work from the observations, not from what you expect to find. Group incidents
that share a mechanism. An incident that shares a mechanism with nothing else
is still a mechanism if it could recur, and is named.

For each mechanism, assign its column by the positional test: at what point in
the agent's own execution did this go wrong, taking in, doing the work, or
handing on? Carry forward the incidents it covers, so that its evidence traces
back to what was seen.

Account for every observation. Any you do not place goes in "unplaced" with a
reason. Do not drop one silently.

The preamble governs what you WRITE, not what you were GIVEN. The observations
are raw material and may be messy, mis-scoped, or phrased as consequences.
Find the mechanism behind them; do not discard them for how they were
reported.

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

One call over the modes, the contracts, and a sample of traces. It decides,
per (mode, agent), whether the mechanism can occur there at all and whether it
is the same mechanism.

```
## THE MODES
{all modes}

## THE AGENTS AND THEIR CONTRACTS
{contracts}

## TRACES
{trace excerpts, outcome-blind}

## TASK

For every (mode, agent) pair, answer two questions in order.

1. CAN this agent exhibit this mechanism at all? Answer from its CONTRACT. An
   agent never asked to do a thing cannot fail at doing it. This question may
   be answered from the contract alone.

2. If it can: does this agent fail by a DIFFERENT mechanism than the mode
   describes, or by the SAME mechanism in a different place?

THE DEFAULT IS ATTRIBUTE, NOT SPECIALISE. The same mechanism in a different
output is the same failure and stays one code; the occurrence records which
agent. Only a different mechanism earns its own code, and appearing somewhere
else is not a difference in mechanism.

  Grounding

  Two agents each assert something their own inputs do not contain. Same
  mechanism, two places. One code, two attributions. ATTRIBUTE.

  One agent's contract is to preserve what it is given, and it drops part of
  it. Another's is to move the work forward, and what it produces does not.
  Different mechanisms, not one mechanism in two places. SPECIALISE.

  Reason from the question, not from these two: is the OPERATION that went
  wrong the same?

SPECIALISE REQUIRES EVIDENCE. You may answer can_occur from the contract; you
may not answer "specialise" from the contract. A specialised code needs an
observed instance, in a permitted evidence form, showing the different
mechanism. If you believe a distinction exists but cannot evidence it from the
traces, answer "flag": it is recorded for later evidence collection, not
turned into a code.

A specialised code is agent-free like every other, and held to the same
granularity and evidence checks.

Return ONLY JSON. `specialised_code` is filled only when the verdict is
"specialise", and is null otherwise:
{"applicability": [{"mode": "<mode name>", "agent": "<agent name>",
                    "can_occur": true|false,
                    "verdict": "attribute"|"specialise"|"flag",
                    "why": "...",
                    "specialised_code": {"name": "...", "column": "general"|"domain",
                                         "definition": "...", "when_to_use": "...",
                                         "when_not_to_use": "...",
                                         "evidence": [{"trace_id": "...", "quote": "..." or null,
                                                       "missing": "..." or null}]} or null}]}
```

---

## Stage 5 — consolidation

One call over the stage-3 modes and the stage-4 specialised codes together.

```
## ALL CODES
{all modes and specialised codes}

## TASK

Produce ONE canonical taxonomy: the finished set of codes, each with a stable
id, and a record of what became of every input code. The output is the
taxonomy, not a list of operations.

MERGE codes that name the same mechanism. Look in particular for one mechanism
split across agents or outputs: codes that differ only in where the failure
occurred are one code.

MERGE ONLY TRUE DUPLICATES. Two tests, and both must pass:
  would the SAME correction to the program fix every incident under both
  codes? and
  could a reader, seeing the trace text alone, be unable to tell which of the
  two it is?
If you can state a boundary between two codes that a reader could apply, they
are NEIGHBOURS, not duplicates. Write the boundary into when_not_to_use and
keep both.

Sharing a category is not sharing a mechanism. Several codes may all concern
output structure, or all concern the handling of evidence, and still be
distinct mechanisms: emitting the wrong KIND of thing is not the same failure
as emitting the right kind badly formatted, however similar the categories
sound. Merging across that line produces a code broad enough to fire on almost
anything, which separates nothing and is worse than the duplication it
removed.

SPLIT a code that covers two mechanisms.

CHECK COLUMNS. Two codes that need a when_not_to_use to separate them are
neighbours, and neighbours usually belong in the same column, but not always:
two mechanisms can have similar visible boundaries while operating on
different things. Where a boundary crosses columns, decide from the mechanism
and say why. Do not move a code to satisfy the heuristic.

IDS ARE STABLE AND NEVER REUSED. A merged code takes a new id and records its
sources; a retired id is never reassigned; a surviving code keeps its id.

Every code carries its evidence forward: the incidents of the modes it came
from, so that nothing in the taxonomy rests on less than what was observed.

Return ONLY JSON:
{"taxonomy": [{"id": "...", "column": "general"|"domain", "name": "...",
               "definition": "...", "when_to_use": "...", "when_not_to_use": "...",
               "evidence": [{"trace_id": "...", "quote": "..." or null, "missing": "..." or null}]}],
 "provenance": [{"from": ["<input code>", ...], "to": "<id>",
                 "operation": "keep|merge|split|retire", "why": "..."}]}
```

---

## Stage 6 — rule validation

Every field is required, so a skipped check is a missing field rather than an
invisible omission. Verdicts are DERIVED from the checks, never asserted.

The code appends three sections after this prompt: `## THE TAXONOMY` (the
stage-5 output), `## WHAT EACH CODE CAME FROM` (its provenance), and `## THE
MODES BEFORE CONSOLIDATION` (the stage-3 modes). Validation judges each code in
isolation, and a merged code that is far too broad reads as clean on its own;
the defect exists only relative to what it replaced, which is why the
provenance and the unconsolidated modes are shown.

```
## TASK

The taxonomy, its provenance, and the modes it was consolidated from follow
this task. For every code, answer ALL of the following.

  column         "general" | "domain"
  column_ok      "yes" | "no"    filed where its mechanism belongs, by the
                                 positional test
  is_mechanism   "yes" | "no"    can you state the operation that went wrong
                                 WITHOUT naming its downstream effect? If the
                                 only thing sayable is that the result came
                                 out wrong, this is a consequence
  contract_ok    "yes" | "no"    describes a failure against the agent's OWN
                                 contract and input; nothing inherited,
                                 upstream, propagated or downstream
  agent_free     "yes" | "no"    no agent or role name, in either column,
                                 specialised codes included
  granularity    "ok" | "one_instance" | "task_shape" | "too_general"
  merged_from    [ids] | null    taken from the provenance you are given
  merge_ok       "yes" | "no" | "n/a"
                                 for a merged code only: would ONE correction
                                 to the program fix every incident it
                                 absorbed? If a boundary could be stated
                                 between the codes that were merged, the merge
                                 was wrong, and "n/a" is not an answer for a
                                 merged code
  observable     "yes" | "no"    a judge could point at trace text or at a
                                 bounded absence
  evidence_ok    "yes" | "no"    permitted form, and every span an exact
                                 substring of its trace

There is NO verdict field. The verdict is DERIVED:
  observable = no, or evidence_ok = no   -> RETIRE
  is_mechanism = no                      -> REWRITE as a mechanism, or RETIRE
                                            if it is only the consequence of
                                            another code
  contract_ok = no                       -> REWRITE against the agent's own
                                            input
  column_ok = no                         -> MOVE column
  agent_free = no                        -> RENAME without the agent
  granularity != ok                      -> REWRITE at the right level
  merge_ok = no                          -> SPLIT back into the codes it
                                            absorbed, restoring their ids
  otherwise                              -> KEEP

Whenever a check is not ok, supply the corrected fields. Marking a code too
narrow without supplying a wider definition is an incomplete answer.

THEN EMIT THE CORRECTED TAXONOMY, not only the verdicts. Apply every
correction you derived, and look once more at the result:

  A rename can create a duplicate. If two codes differed only by the agent or
  the output field named in them, removing that name makes them the same
  code. Merge them, under the merge test above.
  A code retired for being only the consequence of another leaves its
  incidents behind. Attach them to the code that explains them.

Return ONLY JSON:
{"checks": [{"id": "...", "column": "...", "column_ok": "...", "is_mechanism": "...",
             "contract_ok": "...", "agent_free": "...", "granularity": "...",
             "merged_from": [...] or null, "merge_ok": "...", "observable": "...",
             "evidence_ok": "..."}],
 "taxonomy": [{"id": "...", "column": "...", "name": "...", "definition": "...",
               "when_to_use": "...", "when_not_to_use": "...",
               "evidence": [{"trace_id": "...", "quote": "..." or null, "missing": "..." or null}]}],
 "corrections": [{"id": "...", "verdict": "KEEP|RETIRE|REWRITE|MOVE|RENAME|SPLIT|MERGE",
                  "why": "...", "into": "<id, or ids, the code became>" or null}]}
```

---

## Stage 7 — refinement round

Generation says what the traces showed. A refinement round asks whether the
vocabulary is *written right*, using evidence generation could not have had:
the measurement judge's reading of a second, task-disjoint corpus under the
draft taxonomy. Three calls, none of which sees the gate corpus.

**The evidence base.** For every code, straight from the judge's records on the
refinement corpus and never from outcomes:

- how many traces it fired on, out of how many were judged;
- how many traces the panel disagreed on (some readers assigned it, others did
  not);
- the problems the open reader, which holds no taxonomy, described that were
  then mapped to this code at a good fit;
- the problems mapped to it at a poor fit, which the mapper had to *stretch*
  the code to cover;

and, for the taxonomy as a whole, the problems no code fitted at all.

**The three calls.** 7a is answered independently by each reviewer on a panel
(default four), all seeing the same prompt. 7b merges the panel into one
checklist and is skipped when the panel has one reviewer. 7c decides what can
only be decided by seeing codes together: merges, splits, and additions. The
per-code verdict is derived from the checklist by the code, not asserted by
the model, so a check and a verdict can never contradict each other.

### 7a — reviewer checklist

```
## WHAT EACH AGENT WAS ASKED TO DO
{contracts}

## THE TAXONOMY, CODE BY CODE
{the taxonomy, code by code}

## THE EVIDENCE BASE
{evidence base}

## TASK: complete the checklist for EVERY code

Return one entry per code. Every field is required, and "code" holds the
code's exact id. A missing entry or a missing field is an error.

  subject      "candidate" | "environment"
               Could a DIFFERENTLY-DESIGNED candidate, on the same task and
               the same infrastructure, have avoided it? Verbose generation
               that hits a token limit: yes, candidate. A retriever whose
               corpus lacks the document, an API error, a rate limit: no,
               environment.
  observable   "yes" | "no"
               A reader could QUOTE trace text showing it, or point at a
               bounded absence.
  mechanism    "ok" | "consequence" | "remedy"
               The code names HOW the failure worked. "consequence" if it
               names what the failure cost; "remedy" if it names what should
               have been done instead.
  contract     "ok" | "none"
               The code names a breach of something an agent was asked to do,
               a clause of its contract or a requirement of the task. "none"
               if it is tied to no instruction.
  column       "ok" | "general" | "domain"
               "ok" if the column is right; otherwise the column it belongs
               in. General: the mistake is at the edges of the agent's
               execution, in how it read its input or shaped its output.
               Domain: in the middle, in the work the agent does for this
               program.
  adequacy     "matches" | "too_narrow" | "too_broad" | "covers_two"
               Judge from the stretched problems and the panel disagreement.
               A code readers keep stretching to fit is too narrow. One they
               apply to unlike problems is too broad, or covers two
               mechanisms.
  overlap      "none" | "<code id>"
               Another code that names the SAME mechanism.
  reason       One sentence citing the evidence you used.

There is NO verdict field. The verdict is DERIVED from the checks:
  subject = environment, or observable = no    -> retire
  adequacy = covers_two                        -> split (the parts are decided
                                                  in a later call)
  any other check off its clean value          -> edit
      (clean values: subject candidate, observable yes, mechanism ok,
       contract ok, column ok, adequacy matches)
  otherwise                                    -> keep
overlap on its own changes nothing here; it feeds the merge decision in a
later call.

THEREFORE, whenever any check is off its clean value, you MUST also supply the
corrected fields "name", "definition", "when_to_use" and "when_not_to_use".
The "column" field above is both the check and the correction: it carries the
right column whenever the current one is wrong.

A code is edited, never retired, for thin evidence. A code that did not fire
on this corpus has not been shown not to occur.

Return ONLY JSON:
{"checks": [{"code": "<exact id>", "subject": "...", "observable": "...",
             "mechanism": "...", "contract": "...", "column": "...",
             "adequacy": "...", "overlap": "...", "reason": "...",
             "name": "...", "definition": "...",
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

Several reviewers independently completed the per-code checklist, all seeing
the same evidence. Where they agree, keep the agreed value. Where they split,
decide FROM THE EVIDENCE they cite, never by counting votes: a lone reviewer
who quotes the trace outranks three who do not.

For every code return the final checklist entry, with the same fields and the
same rules as the reviewers followed, including the corrected fields wherever
any check is off its clean value.

Return ONLY JSON:
{"checks": [{"code": "<exact id>", "subject": "...", "observable": "...",
             "mechanism": "...", "contract": "...", "column": "...",
             "adequacy": "...", "overlap": "...", "reason": "...",
             "name": "...", "definition": "...",
             "when_to_use": "...", "when_not_to_use": "..."}]}
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

MERGE codes that name the same mechanism. Start from the overlap fields. The
merged definition must cover everything its sources covered, and its column is
the one the merged mechanism belongs in. Apply the two duplicate tests: the
same correction to the program would fix every incident under both, and a
reader seeing the trace text alone could not tell which of the two it is. If
a boundary can be stated, keep both.

SPLIT every code whose checklist says covers_two. Each part names one
mechanism. A part inherits the parent's column unless the split falls exactly
on the column boundary, in which case say so.

ADD a code only where the unfitted problems show a candidate behaviour that
RECURS across traces. One occurrence is not a pattern. An environment failure
is never a code. A new code obeys the same four rules as every other, and
cites the traces that show it.

Return ONLY JSON, with empty lists where there is nothing to do:
{"merge": [{"codes": ["<id>", "<id>"], "column": "general"|"domain",
            "name": "...", "definition": "...", "when_to_use": "...",
            "when_not_to_use": "...", "reason": "..."}],
 "split": [{"code": "<id>", "reason": "...",
            "into": [{"name": "...", "definition": "...", "when_to_use": "...",
                      "when_not_to_use": "...", "column": "general"|"domain"}]}],
 "add":   [{"column": "general"|"domain", "name": "...", "definition": "...",
            "when_to_use": "...", "when_not_to_use": "...",
            "evidence_trace_ids": ["<trace id>", ...], "reason": "..."}]}
```

**Applying the operations.** The code applies the checklist verdicts first
(retire, then edit), then the merges, splits and additions. Every surviving and
new code receives a fresh id in the round's own namespace (`R1_001`, `R1_002`,
...) with a provenance entry naming the code or codes it came from and the
operation, so that a result computed under the refined taxonomy can never be
silently compared with one computed under the draft. Retired codes are kept,
with their definition and the reason, outside the active list. Ids are never
reused.

---

## Stage 8 — interannotation gate, before freezing

Rule validation says the taxonomy is well written. Refinement says it is
written right for the evidence. Neither says that independent readers can
*use* it alike. The gate measures that, on a corpus disjoint from generation
and from refinement, and never shown to the refiner.

The measurement judge reads the gate corpus with N independent readers
(default four), each holding the taxonomy, plus the open reader, which holds
none. There is no deliberation anywhere. From what the readers wrote down:

- **kappa.** Fleiss' kappa over subjects = (trace, code) pairs, each rated
  present or absent by every reader. Reported per code, and pooled over the
  codes at least one reader ever assigned. A code nobody assigned reads as
  perfect agreement on absence, so it is reported separately and not counted.
- **coverage.** The share of the open reader's problems that some code fits
  well, by the judge's own fitness verdict.

A taxonomy passes at pooled kappa ≥ 0.75 and coverage ≥ 0.70; both thresholds
are settable. The draft is measured once before any refinement (the baseline
gate) so that a round's numbers have a reference. A taxonomy that fails gets
another round if rounds remain; the default is one round, and the result ships
carrying its gate numbers either way.

What the gate answers, and what it does not:

- how many failure points have no code: coverage;
- how often readers disagree, and on which codes: the per-code kappa;
- which codes collapse into each other: the overlap field of the refinement
  checklist, not the gate;
- whether every code can be applied without seeing the outcome: enforced by
  construction, since the judge never receives one;
- whether some candidates' failures are systematically easier to detect than
  others: not measured here, and open.

---

## After the gate: the follow-up checks

Three checks in `generation/` run on the final taxonomy, on traces it was not
built from. Their prompts live in the code, not here.

- **Gap test** (`gaps.py`). Fresh traces are observed with the stage-2 passes,
  without the taxonomy in view, and each finding is then mapped to a code or
  to "none". An unmapped finding must show which codes were ruled out and why;
  backed by that reasoning it is a candidate addition, without it it is a
  mapper that did not look.
- **Granularity** (`granularity.py`). A code that takes a large share of all
  findings may be doing too much, and a fitness score cannot see that. The
  model proposes a split from the findings; the split is accepted only when its
  parts occur *independently* across traces. Parts that always co-occur are one
  mechanism described several ways.
- **Applying the splits** (`apply_splits.py`). Accepted splits are written into
  the taxonomy with new ids and provenance, in the same append-only manner as a
  refinement round.

---

## The occurrence record

So much has moved out of the code that the occurrence schema is part of the
design:

```
{ "code": "<stable id>",
  "agent": "<who exhibited the mechanism>",
  "breached_contract": true|false,
  "response": "propagated" | "detected" | "corrected" | "bypassed"
              | "amplified" | "contained" | null,
  "evidence": {...} }
```

`response` keeps propagation visible without counting it as failure. The
contract rule says an agent that faithfully consumed an upstream error did not
fail; it does not say that what the agent did is uninteresting. Detection,
correction and containment are the recovery evidence FailureRank needs, and
they are lost if only the origin is recorded.
