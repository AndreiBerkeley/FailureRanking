# FailureRank: Candidate Performance and Reliability from Limited Evidence

> **Status:** The research framing behind this package, updated 2026-08-10.
> It states the objective, the measurement inventory and the boundaries of the
> claim. What was actually built and measured is in `experiments/RESULTS.md`;
> the scoring machinery it describes is documented in `pipeline/MODULES.md`.
> This document is reproduced from the project's working repository, with only
> its cross-references adapted to this package.

## 1. Objective

FailureRank studies how to rank candidate agent systems from a limited set
of evaluated tasks and traces. The ranking should say something useful about
both the quality of a candidate's outputs and its ability to maintain that
quality across repeated executions and broader task samples.

The contribution is not a new taxonomy, judge, or recovery analyzer. Those
are replaceable instruments. The contribution is:

1. deciding what evidence must be measured;
2. characterizing how that evidence can be unreliable or unstable; and
3. defining how the measurements should be combined into a candidate score
   or ranking.

## 2. Core Distinctions

- **Performance and certification** concern the quality of the candidate's
  output on a task.
- **Reliability** concerns the candidate's ability to maintain output quality
  when the same task is run across different seeds.
- **Generalization** concerns whether measurements from a limited observed
  task set remain informative on a broader unseen task set.
- **Failure evidence** is explanatory evidence. Failure modes are not direct
  definitions of performance or reliability; their value depends on how they
  relate to output quality and repeated success.

## 3. Measurement Inventory

These are intentionally high-level measurements. Their exact definitions,
estimators, and aggregation rules will be developed one at a time.

### Observed evidence

1. **Output quality** — The overall quality of the candidate's final output
   according to the task's requirements.
2. **Failure-mode distribution** — The unique failure modes observed and how
   they are distributed across the available tasks and executions.
3. **Failure-mode relationships** — How failure modes co-occur, interact, or
   form dependency chains.
4. **Recovery** — Whether and how the candidate corrects failures or prevents
   them from affecting the final output.
5. **Failure-outcome relationship** — How failure-mode distributions,
   relationships, and recovery correspond to output quality and cross-seed
   reliability.
6. **Measurement confidence and coverage** — How well each measurement is
   supported by the available evidence, including uncertain or unassessable
   cases.

### Target quantity

- **Cross-seed reliability** — The candidate's ability to maintain output
  quality across different seeds on the same tasks. This is estimated from the
  observed evidence above; it is not assumed to be known initially.

### Validation property

- **Generalization** — Whether an assessment constructed from the observed
  task set continues to predict output quality and reliability on a broader
  task set.

Output quality is deliberately an umbrella measurement. Depending on the
task, it may mean a correct binary verdict, instruction following, plan
quality, satisfaction of several requirements, or another task-specific
standard. The method for measuring it is not fixed at this stage.

## 4. General Framework

Cross-seed reliability is represented only as a structural dependency:

```text
EstimatedCrossSeedReliability(c, s) = f_s(
    OutputQuality,
    FailureModeDistribution,
    FailureModeRelationships,
    Recovery,
    FailureOutcomeRelationship,
    MeasurementConfidenceAndCoverage
)
```

Here, `c` is a candidate and `s` is the evaluation scenario. The estimate may
eventually be represented as a score, profile, ranking, or abstention. The
function `f_s` is intentionally unspecified: no weights, operators, or
concrete formula are adopted until the measurements and their reliability
have been settled. A component may later be removed if it provides no useful
information.

Generalization is not an input that can be used while scoring a candidate. It
is the validation of whether an assessment built from the observed task set
continues to represent output quality and reliability on the broader task set.

## 5. Research Checkpoints

The research proceeds in this order:

1. **Measurement requirements.** Define exactly which metrics, observations,
   and evidence are required for the components above.
2. **Unreliability and instability.** Identify deviations from the intended
   measurements and decide which can be corrected, bounded, or only reported.
3. **Scoring formula.** Construct a formula from the required measurements and
   the error model. Begin with one general formula; consider scenario-specific
   variants only if evidence later requires them.
4. **Baseline instrument.** Build a reasonable, general
   taxonomy-judge-recovery pipeline that produces the required evidence. Its
   role is to test the relevance of the measurements, not to serve as the main
   research contribution.

No single scoring formula is adopted. Earlier prototype formulas are retained
as sources of evidence about design failures, not as a specification.

Five parameter-free aggregations of the failure-mode distribution — base
amplitude, persistent pairs, full size-2-through-6 combinations,
order-normalized combinations, and pair expansion — were built and validated on
2026-08-12 and none was adopted. They are the five reference baselines in
`experiments/RESULTS.md`, where each is explained and measured; per-candidate
scores are in `experiments/results.json`. Higher-order combinations proved
rank-identical to persistent pairs, and every variant missed Top-1 against both
validation targets.

## 6. Baseline Instrument Boundary

The baseline instrument may contain:

- a general task-appropriate output-quality evaluator;
- a fixed, general failure taxonomy;
- a taxonomy-conditioned trace judge;
- failure relationship and recovery analysis; and
- evidence-confidence and coverage reporting.

When a task has an objective evaluator, its outcome can provide the
output-quality measurement. Less objective tasks may require a task-derived
checklist and judge.

Recovery is an optional measurement and required ablation, not an assumed
source of value. Its contribution must be measured rather than built into the
definition of candidate quality.

## 7. Contribution Boundary

The intended contribution is a validated evidence-and-aggregation framework
for candidate performance and reliability. A taxonomy, judge, recovery
analyzer, or output-quality evaluator is sufficient when it is credible enough
to instantiate the measurements and expose their limitations. Improving those
instruments may be useful engineering, but it is not the primary claim.

Related work, the dated record of method decisions, and parked ideas are kept
in the project's working repository rather than in this package, which carries
only the current state and its experiments.

## 8. Research To-Do

- **Candidate–taxonomy pair as the transferable measurement unit** — Treat
  `(candidate, taxonomy)` as the variables that define the candidate's
  invariant output-quality representation: the candidate supplies the observed
  behavior, while the taxonomy supplies the common coordinates in which that
  behavior is measured. Test whether a score derived from this pair remains
  comparable when tasks and domains change, and identify the conditions under
  which the taxonomy is sufficiently domain-general—or can be consistently
  mapped—to make the quality measurement transferable. Transferability is the
  hypothesis to validate, not an assumption.

- **Verification-depth diminishing returns** — Test the same measurement
  pipeline with zero, one, and additional verification layers. At each depth,
  measure the marginal improvement in instrument validity and final ranking,
  together with added model calls, tokens, latency, runner failures,
  abstentions, and coverage loss. Explicitly count backfires where another
  verifier changes a previously correct assessment into an incorrect one or
  amplifies a shared error. Compare marginal benefit against marginal cost and
  adopt a stopping rule defined before examining the final results. This study
  must answer empirically why another verification layer is or is not justified;
  diminishing returns or backfire are hypotheses, not assumptions.
