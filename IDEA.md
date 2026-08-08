# Failure-Based Comparative Evaluation of LLM Agent Systems

> AUTHORITY: this local file is the single source of truth. The Google Doc
> "New research directions (Andrei / Mert)" is downstream — Andrei updates
> it FROM the local .mds, never the reverse. (Initial content seeded from
> the Doc's "Main Idea" tab on 2026-08-07; that was a one-time seed, not a
> sync relationship.)

## Abstract

Selecting the strongest LLM agent system cannot be reduced to comparing
outcomes from a limited set of executions. Even with an accurate outcome
evaluator, candidate rankings may change across seeds, task samples, and
evidence volumes. Terminal outcomes also conceal process-level differences:
two candidates with similar success rates may differ substantially in the
failures they encounter and recover from.

We study whether structured failure evidence from agent traces can produce
more stable candidate comparisons. The pipeline first identifies failure
modes, then determines whether each failure occurrence was recovered, and
finally aggregates this evidence into a scenario-dependent candidate score
or ranking. The study begins with human or programmatic annotations to
isolate the value of each component before introducing automated judges.
The main question is whether failure-based selection predicts the candidate
ordering supported by broader tasks and repeated executions better than
outcome-only selection using the same limited initial evidence.

## 1. Problem and Objective

An outcome evaluator determines whether one execution succeeded. It does
not necessarily identify the candidate that will perform best across new
seeds or additional representative tasks. Observed outcome rankings can be
unstable when the initial evaluation contains too few tasks, insufficient
repetitions, or an unrepresentative task mixture.

Execution traces contain evidence unavailable in terminal outcomes. A
candidate may succeed only after serious failures and fragile recoveries,
while another may reach the same outcome through a cleaner and more stable
process. Conversely, a visible failure may be harmless if the candidate
later neutralizes it.

Given multiple candidates and their execution traces, the objective is to
transform failure evidence into a candidate score, profile, or ranking
appropriate to a declared evaluation scenario. The method should
distinguish between estimated quality and confidence: additional evidence
should make an assessment more precise, but should not automatically
increase or decrease a candidate's score.

## 2. Failure-Based Evaluation Pipeline

**Stage 1 — Failure identification.** Identify failure occurrences and
assign modes from a fixed taxonomy. Each annotation records failure type,
trace position, task, seed, and supporting evidence. The initial study can
inherit an existing taxonomy (AdaMAST or MAST). Annotations may initially
be produced by humans or programmatic checks, later replaced by an existing
taxonomy-conditioned LLM judge.

**Stage 2 — Recovery analysis.** Determine whether each identified failure
was recovered — corrected or neutralized before it prevents the task
requirements from being satisfied. Recovery is occurrence-specific and
candidate-specific: the same mode may be routinely recovered by one
candidate and terminal for another. Initial labels may come from human
analysis, programmatic state checks, instrumented environments, or executed
replay; automated recovery analysis introduced later.

**Stage 3 — Candidate scoring.** Aggregate failure and recovery evidence
into a candidate-level evaluation. Quality may depend on: failure
prevalence and severity; recovered vs. unrecovered failures; persistence
and propagation; distribution across tasks; recurrence across seeds; task
and trace coverage; uncertainty from limited evidence. Measurements and
aggregation change across scenarios. Output may be a scalar score, a
multidimensional profile, a pairwise comparison, a ranking, or abstention
when evidence is insufficient.

## 3. Evaluation Scenarios

- **Observed-set selection.** Same task set for all candidates. Single-seed:
  which candidate performed best on the observed executions. Multi-seed:
  comparison across repeated runs, reducing the influence of a favorable
  execution.
- **Unequal-evidence comparison.** Candidates differ in tasks, traces, or
  repetitions. Normalize failure evidence and represent uncertainty without
  rewarding or penalizing a candidate merely for having more observations.
  Only meaningful when task settings are sufficiently comparable; otherwise
  account for the mixture difference or decline to produce a confident
  ranking.
- **Reliable selection over additional tasks.** Candidates compared on
  limited evidence, then evaluated on substantially broader tasks and
  repeated executions from the same intended setting. The target is the
  ordering supported by the broader evidence. Central test: does the
  initial failure-based ranking predict this ordering better, or at least
  as well, as an outcome-only ranking from the same initial executions?

## 4. Component-Isolation Study

Do not begin with a fully automated pipeline — poor end-to-end performance
would not reveal which component failed. Oracle conditions isolate each
component:

| Configuration | Failure labels | Recovery labels | Purpose |
|---|---|---|---|
| Oracle pipeline | Human/programmatic | Human/programmatic | Tests the scoring mechanism with accurate evidence |
| Annotation test | Automated | Oracle | Effect of annotation errors |
| Recovery test | Oracle | Automated | Effect of recovery errors |
| No-recovery ablation | Oracle or automated | Not used | Value added by recovery evidence |
| Fully automated | Automated | Automated | The practical system |
| Outcome-only baseline | Not used | Not used | Does trace evidence improve selection at all |

Research path: establish whether the scoring principle works, replace one
oracle component at a time, then evaluate the complete automated system.

## 5. Quality of the Scoring Procedure

Q_scoring(b, s) = f(Q_annotation, Q_recovery, Q_taxonomy, M, {R_i}, C_task, C_trace)

where b is the benchmark; s the evaluation scenario; Q_annotation the
failure-detection/classification quality; Q_recovery the recovery-labeling
quality; Q_taxonomy the adequacy of the failure vocabulary; M the number of
distinct tasks; R_i the executions available for task i; C_task task-set
coverage/representativeness; C_trace trace diversity/representativeness.
These factors are benchmark- and scenario-specific — a judge that performs
well on one benchmark should not be assumed to perform equally well on
another.

## 6. Validation and Supervision

Two supervision regimes:

- **Gold-calibrated:** training outcomes or oracle annotations help learn
  the relationship between failure evidence and candidate quality; final
  candidate selection remains outcome-free.
- **Fully gold-free:** construction and selection rely only on failure
  evidence; hidden outcomes and human annotations are used only for
  research evaluation.

Gold outcomes are validation evidence, not a perfect candidate-selection
method. Failure-based and outcome-only approaches must receive the same
limited initial evidence and be evaluated against the same broader repeated
evaluation. Measures: correct top-candidate selection, rank correlation,
selection regret, ranking stability, appropriate abstention.

## 7. Candidate Scoring (general form)

S_(c,s) = g_s(F(c), A(c), E(c), U(c))

F(c): observed failure occurrences and properties. A(c): recovery,
persistence, propagation. E(c): task/trace/seed coverage. U(c): uncertainty
in evidence and estimate. g_s: scenario-specific aggregation. The scoring
range is a presentation choice and adds no information; test size should
not directly improve a score — it affects normalization and the attached
uncertainty.

## 8. Core Contribution

Not a new taxonomy or judge — existing taxonomies, annotation judges, and
recovery analyzers are replaceable measurement instruments. The central
contribution: **a scenario-conditioned framework for measuring and
aggregating failure occurrence, recovery, distribution, and uncertainty
into a validated representation of candidate quality.** The
component-isolation study establishes the value of these measurements
independently of annotation quality and reveals how errors in each stage
affect the final ranking.

Literature lives in [LITERATURE.md](LITERATURE.md), filed by purpose.
