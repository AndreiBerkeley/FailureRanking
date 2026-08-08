# Taxonomy freeze record — experiment 1 (v0 shakedown)

## Final artifact

**`taxonomy_frozen_v2.json`, 19 codes** (2 A, 8 B, 9 C), sha256
`658417455b3d8b2cc3e9cfc03c7fa66e1ff1d2a66c399393c1b39c69fb595e38`. This is the
taxonomy scoring uses.

    taxonomy_ladder_v1_calibrated (archive)  ->  taxonomy_frozen_v0.json   19 codes
      -> reflection refinement on the 24-trace validation slice  -> _v1.json  25 codes
      -> admissibility prune                                     -> _v2.json  19 codes

Net change from v0: B.8 + B.9 merged into B.10 `Query_Specificity_Mismatch`
(re-scoped to `query_generator`), C.10
`Gap_Identification_Without_Strategy_Adaptation` added, and B.2/B.3/B.5
definitions sharpened. 17 of v0's codes survive unchanged.

## Selected

`taxonomy_frozen_v0.json` — copied verbatim from `taxonomy_ladder_v1_calibrated.json`
in `AndreiBerkeley/gepa-experiments-archive`, release `runs-2026-07-22`, asset
`taxonomy.tar.zst`, path `taxonomy/taxonomy_ladder_v1_calibrated.json`.

    sha256  387d411b46bf4ac32f802592e721d445c4e0c5f8d8e0249a227c138094c17f67

19 codes: 2 category A (execution), 9 category B (role-local: summarizer,
query_generator), 8 category C (pipeline-wide reasoning). Severity already
assigned per code: 6 critical, 11 major, 2 minor.

## Lineage

    abc_seed0 (36 codes, Jun 19, HoVer multi-hop fact verification)
      -> atlas_generation (45, Jun 23)
      -> self_refined_1782267012 (49, self-refined from 30 traces)
      -> pruned (25) -> pruned_no_phantom (23) -> sanitized
      -> taxonomy_v9 / v10 (23) -> taxonomy_v11 (23, Jul 10)

    ladder V0 induction, Opus 4.6, 60 traces (40 codes)
      -> taxonomy_ladder_v1 (18, Jul 13, manual condensation)
      -> taxonomy_ladder_v1_calibrated (19, Jul 14, 204 judgments audited)   <-- SELECTED

## Why this one over taxonomy_v11

Both are HoVer, both target the same two roles (summarizer, query_generator),
and both already retire the "missing final verdict" codes that a retrieval-only
pipeline can never satisfy — v11 on empirical grounds (A.2 fired 138x and A.7
39x, 29% of all judge observations in run 20260625T193101Z), ladder_v1 on
structural grounds (generator-marked `support=theoretical`).

The deciding factor is what each was refined *for*. The v11 lineage was
self-refined to improve reflection feedback inside the AdaMAST optimization
loop. `ladder_v1_calibrated` was condensed against "trace-observable
boundaries" and calibrated over 204 audited judgments, with the stated goal of
making names-only feedback directional — it splits fabrication from omission,
broad from narrow query scope, and missing-side from incompatible-value
comparisons. That is judge-assignment quality, which is what this experiment
measures. It is also the newest HoVer artifact in the archive and the smallest
(19 vs 23), which matters because the initial influence weights are equal at
`w_m = 100/K`.

`taxonomy_v11.json` is kept alongside as `taxonomy_v11_alternate.json`
(sha256 0574be98...) for a taxonomy-sensitivity arm.

## Known mismatch to repair in the trace adapter

The taxonomy's `role_definitions` name the agents `summarize_hop1`,
`summarize_hop2`, `generate_query_hop2`, `generate_query_hop3`. This run's
components are `summarize1.predict`, `summarize2.predict`,
`create_query_hop2.predict`, `create_query_hop3.predict`. Same architecture,
different labels — the adapter must map them so role-scoped B codes bind to the
right step.

`ladder_v1_calibrated` carries `validation_status: "Offline structural and
integration validation only; no new paid judge calibration was run."` It has
not been calibrated against this run's candidates. That is what the refinement
pass below is for.

## Refinement content and the contamination boundary

The setup doc requires the taxonomy be refined on candidate-generation or
development traces and frozen *before* final evaluation traces are analyzed.
Refinement content therefore comes from the **100-task GEPA validation split**,
which is disjoint from the 300 held-out scoring tasks. All 300 held-out tasks
stay in scoring: **300 x 12 = 3,600 traces**.

No validation traces were persisted by the original run — `gepa_state.bin`
holds optimization bookkeeping (`full_program_trace` is subsample ids and
scores) and `best_outputs_valset` holds final `retrieved_docs` only, with no
per-step records and sparse per-program coverage. The 24 refinement traces must
therefore be executed: `scripts/collect_val_refinement_traces.py` reuses the
held-out evaluator's program loading, trace schema, redaction and atomic writes,
so refinement traces are shape-comparable to scoring traces.

`scripts/select_val_refinement_tasks.py` picks the pairs: 2 per candidate, 24
distinct tasks, two slots of deliberately different kind.

| slot | condition | selected range | why |
|---|---|---|---|
| `discriminative_failure` | candidate scores 0 | 8–11 of 12 peers succeed | the failure is the candidate's, not the task's — isolable modes |
| `hard_success` | candidate scores 1 | 1–4 of 12 peers succeed | most likely to contain a failure the candidate recovered from |

Tasks nobody solves (19 of 100) and tasks everybody solves (25 of 100) rank last
by construction and none were selected. The 24 span 8 difficulty buckets.

Selection reads GEPA validation subscores, which are gold-derived but describe
the validation split only — GEPA already used them for Pareto selection. No
held-out gold is opened. Verified: 0 overlap between the 24 selected tasks and
the 300 held-out tasks. The script also asserts the exported candidate manifest
and `gepa_state.bin` agree on all 12 x 100 subscores before indexing one by the
other.

## Re-run outcomes of the slice (collected 2026-08-04)

All 24 traces collected, 4 LM calls each, complete summaries/queries/docs, no
error statuses, no credential leakage.

The task model runs at `temperature=1.0`, so these executions are fresh samples
rather than replays of the recorded validation subscores. **15 of 24 outcomes
flipped.** Both slots select for outlier outcomes, so some reversion is expected
by construction; the question is whether it exceeds what noise alone predicts.
Taking each task's peer success rate as the noise baseline:

| slot | reproduction if pure noise | observed | ratio |
|---|---|---|---|
| `discriminative_failure` | 18% | **50%** | 2.8x |
| `hard_success` | 16% | **25%** | 1.6x |

The failure slot carries real signal — those failures are candidate-specific
weaknesses that recur, not sampling artifacts. The success slot is close to
baseline and is mostly luck, which is itself the expected finding for "candidate
succeeded where almost nobody did."

Actual re-run mix: **15 failures, 9 successes** across 24 distinct tasks and 8
difficulty buckets. That is a usable refinement corpus — arguably better than
the intended one, since the 9 successes on hard tasks are the recovered-failure
examples the recovery half of the taxonomy needs. Slot labels are now partly
wrong *as labels*, but they only governed selection: refinement runs
outcome-blind via `project_fn=outcome_blind_trace`, so neither the slot nor the
gold score enters the refiner. Per-pair re-run outcomes are recorded in
`val_refinement_pairs.json`.

Worth carrying into the reliability arm, not treated as a result here: GEPA's
Pareto frontier is built on single-sample validation subscores, and single
samples at this temperature are unstable. Consistent with candidates 2 and 9
tying at val 0.58, GEPA breaking toward 2, and 9 being the stronger candidate on
held-out (0.610 vs 0.580).

## Refinement process

`adamast.learning.reflection_refinement.refine_with_reflection_judge` —
AdaMASTReflectionJudge over the slice, then an LLM refiner applying
MERGE -> EDIT -> SPLIT -> ADD. `allow_retire=False` (the default) keeps every
existing code alive, matching the two-taxonomy active/inactive position: codes
are merged or edited, never silently forgotten. `project_fn` defaults to
`outcome_blind_trace`, so the judge sees no outcome signal.

Not the older `refinement.py` cadence path: that one is built for the
program/branch-local refinement loop with lineage edges across an ongoing
optimization run, which is not the shape of this one-shot pre-freeze pass.

## Adapter (`src/hover_grading/adapter.py`)

**Taxonomy.** Layered -> flat `{repo, domain, codes}` via AdaMAST's own
`candidate_from_adamast`, which preserves `severity` and `applies_to_role`. Two
normalizations were needed: the ladder taxonomies key each category by code
(`{"A.1": {...}}`) while the abc/atlas lineage stores a list, and
`candidate_from_adamast` reads lists only — a dict silently yields zero codes
and surfaces as "no usable failure modes". The adapter normalizes to lists. The
domain is filled explicitly because our artifact carries it in
`metadata.pipeline`, not in the `full_layer.domain_info` slot that function
reads.

**Traces.** GEPA trace -> `{problem_id, task, raw_trajectory, metadata}`. The
trajectory is rebuilt from `prediction` fields, **never from the raw LM
prompts**: each call's system prompt contains that candidate's GEPA-optimized
instructions, which are precisely the candidate's identity. Only per-step
reasoning is lifted out of the raw completions. Steps are labelled with the
taxonomy's agent names (`summarize_hop1`, `generate_query_hop2`, ...) rather
than the DSPy attribute names, so role-scoped B codes bind correctly.

The rendered trajectory is a 7-step transcript following `HoverMultiHop.forward`
— three retrievals with their queries and full passage text, and four LM steps
each showing the inputs visible to it, its reasoning, and its output. It states
explicitly that the pipeline emits documents and not a verdict, so a judge does
not read the missing verdict as a failure.

`assert_blind` runs on every record and rejects any leak of gold, candidate
index, component hash, or slot label. `tests/test_adapter.py` (15 tests) checks
the blinding against the real artifacts — including asserting that no
candidate's actual instruction text from `candidate_manifest.json` appears in
any judge record.

Trajectories run 13.4k–29.3k chars (median 18.2k), so 2 of 24 exceed AdaMAST's
default 25,000-char excerpt cap. The runner sets `ADAMAST_JUDGE_CAP=0` to judge
full traces — 24 traces is small enough that truncation costs more than it
saves.

## Refinement result and the admissibility prune

The refinement pass judged all 24 traces with no warnings and took the taxonomy
from 19 to 25 codes: 7 added, 3 edited (B.2, B.3, B.5), 1 merge
(B.8 + B.9 -> B.10), 0 retired (`allow_retire=False`).

Six of the seven additions describe parts of the system no candidate can vary.
GEPA edits exactly four instruction strings — `summarize1`, `summarize2`,
`create_query_hop2`, `create_query_hop3`. Control flow, hop count, deduplication,
output filtering, the BM25 retriever and the metric are fixed harness, identical
across all 12 candidates.

| dropped | describes |
|---|---|
| A.3 `Pipeline_Terminates_With_Unresolved_Gaps` | `HoverMultiHop.forward`'s fixed hop limit |
| A.4 `Output_Contains_Duplicate_Documents` | concatenation with no dedup stage; metric ignores duplicates |
| A.5 `Retrieval_Accepts_Invalid_Query_Input` | the fixed BM25 retriever; candidate side is already B.4 |
| A.6 `Pipeline_Lacks_Early_Termination_Logic` | absence of control flow the architecture never had |
| A.7 `Output_Includes_Irrelevant_Documents` | no filtering stage exists, and the metric is recall-only |
| C.9 `Retrieval_System_Fails_On_Valid_Query` | self-scopes to failures "not from query formulation defects" |

Kept: C.10 (summarizer flags a gap, query generator fails to adapt — both
GEPA-editable), the B.10 merge, and the three edits.

Under equal weights `w_m = 100/K`, keeping them would have moved K from 19 to 25,
cutting every discriminating code's weight from 5.26 to 4.00 while six codes that
fire near-uniformly on every candidate absorbed 24 points of the influence
budget — plus their firing-rate jitter as noise in the ranking.

**Rule applied:** a code is admissible only if the candidate population can vary
it. Reproducible via `scripts/prune_taxonomy.py`; every drop and its reason is
recorded in `prune_record.json`.

This is the third time the lineage has needed the pass — `taxonomy_v11` retired
A.2/A.7 after they fired 138x/39x on a verdict contract the pipeline never had,
and `taxonomy_ladder_v1` merged 8 theoretical A-codes into 3. The refiner has no
way to know which parts of the system are fixed, so it keeps proposing accurate
observations about invariant structure. If this pipeline is reused, stating the
invariants in the refiner prompt is the durable fix.

## Severity

Present and resolvable on all 19 codes (7 critical, 12 major) but **not used by
the current scoring logic**, which weights every code equally at `100/K`. Note
for anyone who later adds severity weighting: the flat encoding omits severity
when it equals the default `"major"`, so raw JSON shows it on 7 codes only.
Read it through `Taxonomy.from_flat`, which restores the default.
