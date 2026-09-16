# livecodebench

Nine models, one fixed prompt, one call per problem. 1,055 problems of release_v6 split
into three task-disjoint pools; every pool captured for all nine models; the judging pool
judged with the induced taxonomy.

```
tasks/          tasks.jsonl (registry, no tests), splits/, code_generation_lite.py (loader for the raw release)
program/        prompt.md (the exact prompt), structure.json (one agent, single step)
candidates/     models-1.json — the nine models, ids, aliases
traces/         taxonomy_pool (1,350), judging_pool (450 → 1,350), generalization_pool (6,795)
taxonomies/     tax-1 (induced, 7 codes), tax-2 (tax-1 + 3 hand-authored codes)
taxonomy_generation/run-1   every stage's prompt, raw reply and parsed output; gates; gap test; granularity
judge/          pointjudge-1 (tax-1), pointjudge-1-tax2 (hand-assigned), pointjudge-2 (tax-2, 150 tasks)
results/        the four-column tables
```

**Tests are not here.** The hidden tests (4.2 GB) are LiveCodeBench's own; download
release_v6 from the `livecodebench/code_generation_lite` dataset on Hugging Face into
`tasks/raw/`, clone the upstream `LiveCodeBench` repository for its runner, and
`code/livecodebench_scripts/capture.py score` reproduces every outcome file. `tasks.jsonl`
holds every problem's id, title, platform, difficulty, contest date and prompt variant.

**A trace** (`traces/*/<trace_id>.json`): `messages` = system, user, assistant exactly as
sent and received; `metadata` = task, candidate, difficulty, platform, prompt variant,
reasoning setting. The gold is in `outcomes.json` beside the traces (`scores[trace_id]`,
1.0 = all tests passed) and `pool_manifest.json` records the capture settings and the
`candidate_index` → candidate map the judge output uses.

**Pools.** taxonomy 150 tasks (50/50/50 easy/medium/hard), judging 150 (50/50/50),
generalization 755 (222/283/250), seed 2026. Judged: `judging-50-1` (16/17/17, easy
under-weighted) first, then `judging-100-1` (the rest).

**Taxonomy.** tax-1 is `run-1`'s final taxonomy under `GENERATION_v3.md`: draft of 6 codes
(gate kappa 0.875, coverage 0.784), one refinement round, gap test 0 uncovered on 50 fresh
traces, one code split → 7. tax-2 adds three codes written by hand from the 22 points the
judge could not place under tax-1 (unsound strategy / structural premise; implementation
defect in a sound algorithm; contradicting check dismissed); the seven tax-1 codes are
byte-identical. Each taxonomy's README states this.

**Judge.** Two readers (with / without the taxonomy) + decider, five calls per trace.
`pointjudge-1`: tax-1 on the 450 traces of `judging-50-1`, 181 points, 22 fitting nothing.
`pointjudge-1-tax2`: the same run with those 22 hand-assigned to tax-2 codes, no re-judge —
labelled hand-assigned wherever cited. `pointjudge-2`: tax-2 in view on all 150 judging
tasks (in progress at the time of writing).
