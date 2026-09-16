# GEPA_candidates — 12 instruction sets, one model

The candidate set `pool-3`: twelve four-module instruction sets proposed by a GEPA optimizer
run on hover (`plain_gepa_hover_seed0`), run by gemini-3.1-flash-lite. Eight were accepted
onto the optimizer's frontier and are taken at even intervals over its validation score;
four were rejected, also at even intervals — so the set spans the full score range.
`candidates/registry.jsonl` holds each candidate's four instruction texts, its acceptance and
validation score; `candidates/pool-3.json` the set and its rule.

```
candidates/      pool-3.json, registry.jsonl (the 12 rows)
taxonomy/tax-10  the taxonomy the judge held
splits/          eval-1 (sample 50 + domain 500), judging-sample-2 (50)
outcomes/        cap-2 (sample, 600), cap-5 (judging pool, 5,400), cap-3 (domain = generalization, 6,000)
judge_traces/
  sample-50/     traces (600: 12 × eval-1/sample) + judge (map-5)
  judging-50/    traces (600: 12 × judging-sample-2) + judge (map-6)
results/         tables (tau vs gold-gen, top-1): sample-50, judging-50, both (100 tasks), and the 50x10 draws
```

**Two judged sets, 100 tasks, one taxonomy, one judge.** `eval-1/sample` (50) and
`judging-sample-2` (50) are disjoint from each other and from the 500-task `eval-1/domain`
that serves as gold-gen. `judging-sample-2` was drawn stratified by the tasks' mean
candidate score (four quartiles), so its gold-50 read outcomes at draw time; the sample was
not. Both are stated in the results.

**Taxonomy tax-10.** Ten codes (4 general, 6 domain) — output form breach, missing required
part, wrong content in field, unsupported assertion, premature completion, input misreading,
unlicensed conclusion, work state misjudged, misdirected next step, missing closing marker —
re-levelled by hand from an 18-code induced taxonomy so that every code names a mechanism any
candidate could exhibit; `taxonomy/tax-10/README.md` records the review that motivated it.

**Judge (panel + open reader).** Per trace: two annotators (gemini-3.6-flash, thinking high,
temperature 0) each read with the taxonomy and name the codes; a code fires when both agree.
An open reader (gemini-3.1-pro-preview) reads with no taxonomy and reports problems, mapped
to codes afterwards. `judge/mapping.jsonl` gives per trace the codes that fired and which
source supplied each; `judge/judge_records/` the full record per trace; `judge/manifest.json`
the settings, per-code firing and audits. The judge records code counts per trace, not
steps, so the step-level methods are not computable on these mappings. 600/600 judged, 0
failed, in both sets.

**Traces.** One JSON per trace, the outcome-blind judge view (`messages` = the DSPy turns as
rendered for the judge; `metadata` = task, candidate, candidate index, split). Gold is in
`outcomes/`, keyed by trace id, candidate and task.
