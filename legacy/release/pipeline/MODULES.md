# The modules

Scoring a candidate is a sequence of decisions, and each decision is a module
you can swap. This document explains every one: what it does, what it means,
and when you would choose it.

## The seven stages

| stage | question it answers | swappable |
| --- | --- | :-: |
| 1. judge findings | what did the judge see? | fixed input |
| 2. **counting** | what do we count from one failure mode on one task? | yes |
| 3. **relationships** | do we also count combinations of modes? | yes |
| 4. **trust** | how much do we believe each finding? | yes, optional |
| 5. **feedback** | how much does each pattern actually hurt this candidate? | yes, optional |
| 6. **formula** | how do one task's findings become one number? | yes |
| 7. ranking | how do candidate numbers become an order? | fixed convention |

Stages 1 and 7 are deliberately fixed so that every configuration is comparable.
Stage 7 always reads **higher score is better**, ties share their average rank,
and a candidate's score never depends on which other candidates exist.

After stage 6 there is one fixed step: each task's burden becomes a task
quality of `1 - burden`, and the candidate's score is the plain mean quality
over its tasks. Averaging rather than summing is what makes a candidate
evaluated on 30 tasks comparable to one evaluated on 300.

**Running example.** On one task the judge found three failures: `A.8` twice
and `B.6` once. We follow this task through every stage.

---

## Stage 2: counting

*What do we consider, per task, from a single failure mode?* This stage sets
the vocabulary everything downstream speaks.

### `unique`

Each distinct failure mode counts once per task, however many times it was
found. Our example produces **`A.8`, `B.6`**.

The judge sometimes records the same underlying problem several times in one
trace, so repetition is partly an artifact of the instrument rather than a fact
about the candidate. Collapsing to presence removes that artifact entirely.

*Choose it* as the default. It is the most robust option and the strongest
performer here.

### `flagged`

Distinct modes, but each marked as happening once or repeatedly. Our example
produces **`A.8|repeated`, `B.6|once`**.

A middle ground: it keeps the information that a mode recurred within a task,
which can distinguish a system that failed a step once from one that failed it
at every opportunity, while capping the damage a repetition-happy judge can do
at exactly one extra category.

*Choose it* when within-task persistence is meaningful, and especially when
combined with feedback modules, where it produces the best top-choice
selection in this data.

### `total`

Every occurrence counts. Our example produces **`A.8`, `A.8`, `B.6`**.

*Choose it* only when you trust the judge's multiplicity to reflect the
candidate rather than the judge's own behaviour. In this data it consistently
underperforms, which is evidence that the multiplicity is largely instrument
noise.

---

## Stage 3: relationships

*Do we also count combinations of modes appearing together?* Co-occurrence
carries information that individual modes do not: two problems on one task may
describe one compound breakdown, or two independent ones.

### `none`

Only the individual modes. Example: **`A.8`, `B.6`**.

*Choose it* as the default. Simple, and the strongest option on the cross-seed
target.

### `pairs`

Individual modes plus every co-occurring pair. Example: **`A.8`, `B.6`,
`A.8+B.6`**.

A recurring pair is a signature of how a candidate breaks down, not just what
it gets wrong.

*Choose it* for transfer to new tasks: pairs give the best held-out
performance in this data.

### `groups`

Individual modes plus every combination of sizes two through six. On a
three-mode task: three modes, three pairs, one triple.

*Choose it* only with a bounded formula. Combination counting grows
exponentially, and with a plain sum it produces the worst results measured
anywhere in this work.

### `groups_only`

Combinations without the individual modes. Example: **`A.8+B.6`** alone.

Isolates pure interaction structure: it asks whether *what co-occurred with
what* ranks candidates, ignoring how much failed.

### `signatures`

The task's exact set of modes as a single instance. Example: **`sig:A.8+B.6`**.

Treats a failure profile as one diagnosis rather than a list of symptoms, so
"B.6 alone" and "B.6 alongside A.8" become genuinely different observations.
Conceptually appealing, but it fragments the evidence: most task signatures are
seen only once, and it performs poorly here for that reason.

### `ordered_pairs`

Individual modes plus direction-aware pairs, ordered by first occurrence in the
trace. Example: **`A.8`, `B.6`, `A.8->B.6`** if `A.8` occurred first.

*Choose it* when the order in which failures appear plausibly matters, for
example when an early failure could cause a later one.

---

## Stage 4: trust, optional

*How much do we believe each finding?* Automated judges over-report. They flag
process imperfections that never affected anything. This stage uses the judge's
own testimony about its findings to weigh them, and it is the single most
valuable stage in this package.

Skipping this stage means every finding counts fully.

### `ol_gate_likely`

The judge rates every failure it finds for whether that failure plausibly
reached the final answer: *direct, likely, possible, unlikely, none*. This
module keeps only findings rated **direct or likely**, and drops the rest.

In plain terms: *count only the failures the judge itself believes mattered.*

In the running example, if the two `A.8` findings were rated `direct` but the
`B.6` was rated `unlikely`, only `A.8` survives.

Note the ratings are made by the judge while reading the trace, without ever
seeing the answer key, so this remains gold-free.

*Choose it* almost always. On its own, added to the simplest possible scoring
method, it produces the best-performing configuration in this package.

### `ol_ordinal`

The same testimony as a graded weight instead of a cut: direct counts 1.0,
likely 0.75, possible 0.5, unlikely 0.25, none 0.

*Choose it* when combining with a feedback module. The hard gate deletes
evidence that feedback modules need in order to estimate anything; the graded
weight keeps it alive at reduced volume. This distinction produces the best
top-choice configuration in this data.

For combinations, the weight is the minimum over member modes: a pair is only
as trustworthy as its least trusted member.

---

## Stage 5: feedback, optional

*How much does each pattern actually hurt this candidate?* Every stage so far
treats all failure modes as equally bad. This stage learns that they are not,
by asking a single question: **when this pattern appears, does this candidate
survive it anyway?**

Skipping this stage means every pattern is equally harmful.

The estimates are always **per candidate**. A pattern that is fatal for one
system may be routine for another, and pooling across candidates to learn
global mode weights was tried and fails badly. This locality is the design's
central constraint.

### The gold section

Survival means **the task succeeded anyway**. These modules read evaluated
outcomes on the evidence tasks, which makes the configuration a *scenario 1*
run, recorded as `scenario_1: true` in the output. The held-out tasks are never
read.

- **`gold_linear`** — influence falls uniformly with the survival rate:
  `1 - survivals/appearances`. A pattern surviving half the time is charged
  half as much.
- **`gold_convex`** — influence falls with the square:
  `1 - (survivals/appearances)²`. One survival out of ten barely reduces the
  charge, while each further survival removes more than the last. Use when you
  want isolated survivals treated as luck rather than evidence.
- **`gold_shrunk`** — the survival rate is pulled toward the candidate's own
  base success rate in proportion to how thin the evidence is. A pattern seen
  twice barely moves from the prior; one seen thirty times keeps its measured
  rate. Use when small-sample flattery is a concern.
- **`gold_fused`** — combines with the judge's consequence ratings: on a failed
  task, a pattern rated *direct* takes nearly full blame while a co-present
  pattern rated *unlikely* takes almost none, instead of both being blamed
  equally. Answers "when this pattern *consequentially* appears, does the
  candidate still succeed?"

### The recovery section

Survival means **the failure was recovered within the trace**: the records for
that pattern carry a recovered or made-irrelevant label. This is the gold-free
mirror of the gold section, using only what the trace shows.

- **`recovery_linear`**, **`recovery_convex`** — the same two shapes applied to
  the recovered share instead of the success share.

*Choose the recovery section* when no outcomes are available at all. In this
data it is roughly neutral: it neither helps nor hurts, which is itself a
finding about the recovery labels available here.

---

## Stage 6: formula

*How do one task's findings become one number?* Several findings on one task
may describe overlapping damage. This is the only stage allowed to decide how
overlap is handled, and the choice matters more the richer stage 3 is.

Each option receives the task's instances with their trust weights and feedback
influences already applied.

### `uncapped_sum`

Add everything up, no ceiling. A three-mode task costs three units.

Assumes no overlap at all: every finding is separate damage. Simple, and the
best performer here when paired with `relationships: none`, where there is
little overlap to mishandle.

*Caution:* with `relationships: groups` this bills one underlying problem once
per subset that contains it, and produces the worst results in this work. The
richer the relationship structure, the more overlap control the formula must
supply.

### `capped_sum`

Additive, but a task can never cost more than "fully failed". Keeps scores
inside 0 to 1 and prevents one catastrophic task from outweighing many clean
ones.

### `noisy_or`

Treats findings as independent chances to break the task. The first costs a
lot, the second adds less, the third less still, saturating below the maximum.
The natural choice when several genuinely distinct problems are present.

### `max`

Only the strongest finding counts; the rest are treated as symptoms of it.
Assumes complete overlap.

*Choose it* with feedback modules, where instances carry meaningfully different
influences and "the worst known problem on this task" is a sharp summary. It
produces the best top-choice selection in this data.

### `pie_signed`

Inclusion and exclusion: individual modes add, pairs subtract, triples add, and
so on, so shared damage cancels instead of being counted twice. The principled
answer to overlap when the full combination structure is present.

*Caution:* it requires the complete series to behave. Truncated at pairs it
becomes a bound rather than a value and can invert orderings, which is what
happens in this data. It is included as a documented negative result.

### A note on flat evidence

With no trust and no feedback, every instance has the same value, and the four
bounded formulas collapse to the same thing: "did anything fail on this task".
They separate only once stages 4 or 5 give instances different weights. This is
expected, and it is why the formula choice matters most in richer
configurations.

---

## Attribution, an optional read-out

Given any formula, a task's burden can be split across the individual failure
modes by Shapley value, the standard rule for dividing a jointly produced total
fairly. Its defining property here is that the shares always sum exactly to the
score, so a per-mode profile can never claim more or less burden than the score
contains.

This is an explanation layer, not a scoring choice: it decomposes a finished
score and can never change one.
