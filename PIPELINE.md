# The taxonomy pipeline

How a failure-mode taxonomy is built, from an untouched benchmark to a
ready-to-use vocabulary. This is the standard procedure for every experiment;
`METHODOLOGY.md` says why failure modes are the vocabulary, this says how one
is produced.

---

## The loop

```
generation                   (draft only: no agreement pass)
  -> baseline gate           (measures the draft; diagnostic, never stops)
  -> refinement round        (judge, then refine)
  -> interannotation gate    -> passed? STOP
  -> refinement round
  -> interannotation gate    -> passed? STOP
  -> refinement round
  -> interannotation gate    -> STOP regardless
  -> promotion               (into benchmarks/<bench>/taxonomies/tax-N)
```

At most three cycles. A taxonomy that has not passed after the third gate ships
carrying its failure, recorded, rather than being iterated until it agrees with
itself.

**Refinement precedes certification.** Certifying a vocabulary that is about to
change wastes the measurement, and the gate is the more expensive step.

## The stages

### Generation
Induces a draft vocabulary from a trace corpus: domain analysis, program
structure, mechanical signal extraction, then category A, B and C generation,
cross-category deduplication, validation, and a final consistency check.
Structure is supplied rather than inferred. Nothing in this stage may invent a
code to fill a coverage quota; every code must rest on observed evidence.

**Generation does not certify.** Upstream `adamast generate` runs a full
four-annotator agreement pass on the draft; the pipeline disables it
(`--no-agreement`). It spends the expensive measurement on a vocabulary the
first refinement round is about to change, and because that pass refines as well
as measures, it made generation a hidden refine-and-measure cycle on top of the
explicit ones, giving every cycle two refinements instead of one. Generation
emits `status: "draft"`. The cycle gate is the only agreement measurement.

### Refinement round
One unit, two steps.

**Judge.** A two-pass reflection judge over the refinement corpus. Pass one
discovers failure points without the vocabulary; pass two maps them onto it,
marking `unmapped` (a real failure with no code that fits) and
`weak_taxonomy_matches` (a code stretched to fit).

**Refine.** Four independent reviewers each complete a per-code checklist over
eight checks: subject, observability, style, category, role, adequacy,
granularity, and subject-matter. Panel agreement is measured and recorded. A
consolidator resolves splits *from the evidence*, not by vote count. The
verdict is then **derived** from the checks, so a diagnosis and a decision
cannot contradict each other, and a code flagged as needing an edit must arrive
with its corrected definition. Cross-code operations follow: merge, split, add.

Five operations exist: add, edit, split, merge, retire. Retirement preserves
the code with its definition, reason and measured utilization; ids are never
reused.

### Baseline gate

One agreement measurement of the draft, before refinement touches it. Without it
the cycle kappas have no reference and the pipeline cannot say whether refinement
improved the vocabulary or merely moved it.

**Diagnostic, never a stopping rule.** Kappa measures agreement and nothing else.
A draft can agree well while missing half the failure modes, and refinement does
more than raise agreement: it fixes subject and observability errors, corrects
adequacy, and adds codes from unmapped evidence. Passing here would say the
vocabulary is coherent, not that it is complete, so the draft is refined
regardless of the number.

It runs on the certification corpus, which is safe only because the gate no
longer modifies the taxonomy. Nothing is fitted to it, and holding the corpus
constant is precisely what makes the baseline and the cycle numbers comparable.

`--no-baseline-gate` skips it.

### Interannotation gate
Four annotators independently code a sample, deliberate, and assign codes;
Fleiss kappa is measured before deliberation. Passing is the gate's own
criterion: kappa >= 0.75 and coverage >= 0.70.

The gate also produces a **codebook**: the deliberated disambiguation rules and
anchor examples that were in every annotator's context when kappa was reached. It
ships with the taxonomy, because a judge applying the codes without it is working
under easier-to-confuse conditions than the ones measured.

**The gate never modifies the taxonomy.** It measures. A round below target is a
finding about the codebook, recorded and left for the refinement panel, not a
defect the gate patches mid-exam. Because the vocabulary is held fixed, every
round measures the same instrument and their subjects pool into one estimate --
which is what the certification uses. Reporting the terminal round alone would
land on the smallest sample the run produces.

**Read kappa narrowly.** It is computed over reconciled errors, not over codes,
and a 30-trace gate yields on the order of 10 to 30 of them. On the 2026-08-29
generation runs that was enough to exercise 7 of 17 codes on livebenchmath and 9
of 22 on hotpotqa, with one code accounting for half the assignments. Kappa says
annotators who found an error agreed how to code it. It says nothing about codes
that never fired, and the promoted artifact records which ones those were.

## The corpora

Three fixed sets. N is the generation corpus size.

| corpus | size | used by | fresh relative to |
|---|---|---|---|
| generation | **N** | generation and its built-in gate | - |
| refinement | **N/2** | every refinement round, re-judged each cycle | generation |
| gate | **60** | every interannotation round, identical each cycle | generation and refinement |

**Fresh traces required: N/2 + 60.**
**Judging cost: up to 3 x N/2 judged traces** (the refinement corpus is
re-judged once per cycle). Capture is roughly 25x cheaper than judging, so the
rule is capture wide, judge narrow: run all candidates over many tasks, then
sample down for the expensive step.

Two properties are deliberate:

- **The refinement corpus is re-judged every cycle.** That is what shows
  whether an edit worked: if a code was stretched four times and still is, the
  correction failed.
- **The gate corpus is identical every cycle.** The gate never modifies the
  taxonomy, so there is no fitting, and holding it constant makes kappa
  comparable across cycles instead of three unrelated numbers.

### Sizing rules

The gate consumes a **fixed 30 traces** whatever the pool: 5 calibration plus 5
rounds of 5. A larger pool only widens its stratified choice. Generation shows
the model 20 traces per stage; N buys signal statistics over the whole corpus
and diversity for those draws.

Trace count is not the binding constraint, **task diversity** is: 60 tasks at 2
traces each beat 8 tasks at 12 traces each on the same judging budget. State
budgets in tasks:

- refinement corpus: at least twice the generation task count, two traces per
  task, one failing and one passing where both exist
- gate corpus: at least 30 distinct tasks, so the gate's 30-trace sample never
  draws the same task twice

### Promotion

A finished run leaves `taxonomy_final.json` in a scratch run directory. Promotion
copies it into `benchmarks/<bench>/taxonomies/tax-N` as a citable artifact with a
README and a `provenance.json`:

```
python -m taxonomy.promote --run <run_dir> [--dry-run]
```

N is the next free number and an existing artifact is never overwritten. The
artifact records the cycle-by-cycle kappa, whether the gate was passed, and the
exact task ids each corpus consumed. Those tasks are spent: a later measurement
run that reuses them is no longer reading a vocabulary built on disjoint
evidence.

An uncertified taxonomy is promoted like any other, with the failure stated in
its README. Results computed with it inherit that failure and must repeat it.

## What is deliberately not in the pipeline

**No support measurement, and no removal by support.** A code that did not fire
on one corpus has not been shown not to occur, and the finished taxonomy is
applied to a different task set than any corpus used to build it. Removing a
code for thin evidence would delete the judge's ability to report a behaviour
that appears later. Codes leave the active taxonomy only through refinement,
and only for a defect in the code itself: it describes the environment rather
than the candidate, it is unobservable, or it duplicates another code.

**No coverage quotas anywhere.** Neither generation nor the final checker may
create a code to fill a gap in a category, role, or subdomain. Gaps are logged
and never filled.

## Standing assumptions

**The loop has no feedback path yet.** The refiner receives the *judge's*
findings on the refinement corpus. It never receives the gate's. So when a gate
fails because annotators cannot separate two codes, the next cycle refines on
unrelated evidence and re-gates hoping for improvement. That is three
independent attempts with a stopping rule, not an iteration.

Closing it is not simply a matter of passing the summary along. The gate corpus
is the certification set, so routing its disagreement into refinement would fit
the taxonomy to the very traces that certify it -- the same error as certifying
on generation traces. The clean form measures disagreement on a corpus we are
allowed to fit to, which means either a dedicated diagnostic half of the gate
corpus (at least 30 further tasks, since the gate needs 30 distinct ones and must
not draw a task twice) or an agreement pass over the refinement corpus. Both cost
one extra agreement run; neither fits inside a 100-task pool. Recorded here so
the next capture can size for it.

**Interpretive judgments are unstable.** Measured on this pipeline: four
identical calls at temperature 0 disagreed on 5 of 19 and 5 of 21 codes, almost
entirely on the `adequacy` check, with two codes splitting 2-2. Structural
checks were stable. Every single-call judgment is one draw from a distribution,
which is why refinement is paneled. The same treatment has not yet been applied
to judging, where each trace is still read once.

**The environment test.** Whether a failure belongs in the taxonomy is not
decided by whether it sounds like infrastructure. The test is: could a
differently-designed candidate, on the same task and the same infrastructure,
have avoided it? Token-limit exhaustion from verbose generation, timeouts from
looping, and context overflow from unbounded accumulation are candidate
behaviour and stay. API errors, network failures, a retriever whose corpus
lacks a document, and framework template bugs are environment and go. A
candidate that hits limits more often than its siblings is exhibiting a real
quality difference and the taxonomy must be able to say so.
