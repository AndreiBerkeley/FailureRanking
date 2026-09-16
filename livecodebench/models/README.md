# models — 9 models, one fixed prompt

The candidate set `models-1`: the same nine models as on hover, each answering every problem
once with the prompt in `../program/prompt.md`. gemini-3.1-flash-lite, claude-haiku-4.5,
gpt-5.4-nano, deepseek-v4-flash, glm-5.3-flash, mistral-small-2603, minimax-m3, mimo-v2.5,
seed-2.0-mini, all via OpenRouter; temperature 0 (gpt-5.4-nano 1.0 as its endpoint
requires), 16,000 output tokens, reasoning off where the endpoint allows. A candidate id
hashes `{prompt, solver_model}`; `candidates/models-1.json` lists ids, aliases and models.

```
candidates/      models-1.json
splits/          judging-50-1 (the first judged 50), judging-100-1 (the rest of the judging pool)
taxonomies/      tax-1 (induced, 7 codes), tax-2 (tax-1 + 3 hand-authored codes)
traces/          taxonomy_pool (1,350: 9 × 150), generalization_pool (6,795: 9 × 755)
taxonomy_generation/run-1   every stage's prompt, raw reply and parsed output; gates; gap test; granularity
judge_traces/
  judging-150/   traces (1,350: 9 × the whole judging pool) + judge/pointjudge-2 (tax-2)
  judging-50-1/  traces (450, a subset of the above) + judge/pointjudge-1 (tax-1), judge/pointjudge-1-tax2 (hand-assigned)
results/         tables (tau vs gold-gen, top-1) per judged set, and the 50x10 draws
```

**Traces.** One JSON per trace: `messages` = system, user, assistant exactly as sent and
received; `metadata` = task, candidate, candidate index, difficulty, platform, prompt variant,
reasoning setting. Gold is in `outcomes.json` beside each pool (`scores[trace_id]`, 1.0 = all
tests passed) and `pool_manifest.json` records the capture settings and the
`candidate_index` → candidate map the judge output uses. Length-capped and fence-less replies
are traces like any other and score 0.

**Judged sets.** `judging-50-1`: 50 tasks drawn seeded within difficulty, 16/17/17
easy/medium/hard (easy under-weighted because the taxonomy pool showed 39 of 50 easy tasks
solved by every model), before any candidate ran on the judging pool. `judging-100-1`: the
other 100. Together they are the whole judging pool, judged in one pass as `judging-150`.

**Taxonomy.** tax-1 is `run-1`'s final taxonomy under `GENERATION_v3.md`: draft of 6 codes
(gate kappa 0.875, coverage 0.784), one refinement round, gap test 0 uncovered on 50 fresh
traces, one code split → 7 (one general, six domain). tax-2 adds three codes written by hand
from the 22 points the judge could not place under tax-1 — unsound strategy or structural
premise; implementation defect in a sound algorithm; contradicting check dismissed — with
the seven tax-1 codes byte-identical. Each taxonomy's README states this.

**Judge.** Two readers (with / without the taxonomy) + decider, five calls per trace, the
same instrument as hover/models. `pointjudge-1`: tax-1 on `judging-50-1`, 181 points, 22
fitting nothing. `pointjudge-1-tax2`: the same run with those 22 hand-assigned to tax-2
codes, no re-judge — labelled hand-assigned wherever cited. `pointjudge-2`: tax-2 in view on
all 150 judging tasks, 1,350 traces, 627 points, 3 unplaced — the mapping every
livecodebench result uses.
