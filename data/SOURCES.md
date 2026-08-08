# Data Sources — provenance ledger

Every item under `data/` gets an entry: origin path, what produced it, date,
and usage caveats. `data/` is immutable — nothing here is ever edited in
place; corrections happen by adding a new dated bundle and a new entry.

---

## legacy-hover-shakedown/ (imported 2026-08-07)

**From-zero amendment, approved by Andrei 2026-08-07** (TIMELINE.md setup
entry of the same date): shakedown-era artifacts from the pre-reset
workspaces, imported as provenance-tracked test data. Tree made read-only
(`chmod -R a-w`) after import.

**Global caveat — read before using anything below.** This is shakedown-era
data: taxonomy, judge prompts, and pipeline all predate the FailureRank
reset and its frozen Ψ/Φ definitions. Usable ONLY for formula/integration
prototyping in `trials/` (loading real annotation distributions, running
Φ variants side by side, schema work). NEVER claims-bearing: no result
computed from it may appear in a paper, an official experiment, or any
evaluation of the method's validity. Official runs require a TIMELINE.md
experiment entry and fresh data.

**Benchmark context.** HoVer three-hop multi-hop fact verification; the
candidate pool is 12 GEPA-evolved variants of a three-hop BM25/DSPy
retrieval program (adapted from MIT-licensed `gepa-ai/gepa-artifact`).
See `certification_analysis/experiments/hover_gepa_baseline/README.md`
(imported below).

### grading/annotations_v3/
- **Origin:** `~/Desktop/GEPA_Experiments/grading/annotations_v3/`
- **Produced by:** AdaMAST-style two-pass taxonomy-conditioned judge
  (model `us.anthropic.claude-sonnet-4-5-20250929-v1:0`, judge prompt v1,
  mode `two_call`) over 600 traces; 596 succeeded (`_run_summary.json`).
  Taxonomy: `taxonomy_frozen_v3.json`. Run date: 2026-08-04.
- **Layout:** `candidate_000/ … candidate_011/`, one JSON per trace
  (filename = trace id; `task_id` inside). Schema: `failure_points[]` with
  `taxonomy_mappings[]` (primary/secondary), `recovery_status`
  (vocabulary observed: `unrecovered`, `not_applicable`,
  `made_irrelevant`, `partially_recovered`, `fully_recovered`,
  `unclear`), `causal_role`, `severity`; `relations[]` with
  causal links (`caused` / `contributed_to`) between failure points;
  `selection_summary` per-trace rollups. `candidate_id` is `"blind"`
  inside files — candidate identity lives in the folder name.
- **Caveats:** global caveat applies. NOTE: the taxonomy folder's
  `FREEZE_RECORD.md` declares `taxonomy_frozen_v2.json` (19 codes) as
  the scoring taxonomy, but this run used `taxonomy_frozen_v3.json` —
  discrepancy inherited from the shakedown, unresolved here; loaders
  must derive K from the taxonomy file the run actually used.

### grading/annotations_pilot/
- **Origin:** `~/Desktop/GEPA_Experiments/grading/annotations_pilot/`
- **Produced by:** same judge pipeline, earlier pilot pass; 20/20 traces,
  taxonomy `taxonomy_frozen_v2.json`. Run date: 2026-08-04.
- **Caveats:** global caveat applies; different taxonomy version than
  annotations_v3 — do not pool across runs without mapping.

### grading/annotations_pilot_mast/
- **Origin:** `~/Desktop/GEPA_Experiments/grading/annotations_pilot_mast/`
- **Produced by:** same judge pipeline over 2 traces with
  `taxonomy_frozen_mast.json` (MAST). Run date: 2026-08-05.
- **Caveats:** global caveat applies; tiny (2 traces, 2 candidates) —
  schema exemplar only, not even prototype-grade volume.

### grading/refinement_slice/
- **Origin:** `~/Desktop/GEPA_Experiments/grading/refinement_slice/`
- **Produced by:** the taxonomy-refinement stage (24-trace validation
  slice per `taxonomy/FREEZE_RECORD.md`); `traces/` (candidate_000–004),
  `val_refinement_pairs.json`, and `gold_do_not_pass_to_judge/`.
- **Caveats:** global caveat applies, plus: **`gold_do_not_pass_to_judge/`
  contains gold labels. Hard rule 3 applies with full force — nothing in
  any scoring path may read it; trials harnesses must structurally
  exclude the folder.** Retained because Andrei's import list included
  the slice and the gold is needed later for after-the-fact rank
  validation.

### grading/evaluation_subset.json
- **Origin:** `~/Desktop/GEPA_Experiments/grading/evaluation_subset.json`
- **Produced by:** deterministic uniform sample (seed 0, gold not
  consulted) of 50 task ids from a 300-task held-out split — the common
  task subset annotated for every candidate. Date: 2026-08-04.
- **Caveats:** global caveat applies. Use as the shared-N task universe
  when comparing candidates on annotations_v3.

### grading/taxonomy/
- **Origin:** `~/Desktop/GEPA_Experiments/grading/taxonomy/`
- **Produced by:** the shakedown taxonomy ladder: v0 (copied from
  `gepa-experiments-archive` release `runs-2026-07-22`) → reflection
  refinement (v1) → admissibility prune (v2, 19 codes, sha256 recorded in
  `FREEZE_RECORD.md`) → v3; plus `taxonomy_frozen_mast.json` and
  `taxonomy_v11_alternate.json`. Whole folder imported so every version
  referenced by any annotation run travels with its freeze/prune records.
- **Caveats:** global caveat applies; see the v2-vs-v3 discrepancy noted
  under annotations_v3.

### certification_analysis/ (README.md, examples/, experiments/hover_gepa_baseline/README.md)
- **Origin:** `~/Desktop/certification_analysis/` (git repo; only the
  interpretive artifacts imported — no source code, caches, or venvs).
- **What they are:** the top-level README documents the three-phase
  certification pipeline whose Phase-2 semantics define recovery
  effect-inclusively ("both the direct error and its downstream effects
  were neutralized") — the reading our Stage-2 definition matches;
  `examples/` holds two sample I/O JSONs for that pipeline; the
  `hover_gepa_baseline` README documents how the 12-candidate HoVer pool
  was generated (plain GEPA, disjoint 100/100/300 splits, frontier
  stopping rule) — needed to interpret candidate folders in the
  annotation runs. Dates: 2026-07-29 – 2026-08-04.
- **Caveats:** global caveat applies. The certification pipeline itself
  is NOT an instrument of this project; these files are context for
  reading the annotations, nothing more.
