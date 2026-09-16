# models — 9 models, one instruction set

The candidate set `models-1`: the same nine models as on livecodebench, each running the
hover program with one fixed instruction set (candidate cand-019's four one-line module
docstrings), so every candidate has an identical contract and any difference in failures is
the model. Solver calls go through OpenRouter; `candidates/models-1.json` lists ids, aliases
and models.

```
candidates/      models-1.json
taxonomies/      tax-14 (induced, 14 codes), tax-15 (tax-14 + one hand-authored code)
splits/          models-1 (taxonomy 600 / judging 500 / generalization 500), models-1-judged-50, models-1-judged-50-b
outcomes/        cap-7 (judging pool, 4,500), cap-8 (generalization, 4,500)
taxonomy_generation/run-1   the new_pipeline run that produced tax-14 (GENERATION_v2)
judge_traces/
  judged-50-a/   traces (450) + judge/pointjudge-1 (tax-14), judge/pointjudge-1-sp15 (tax-15 appended)
  judged-50-b/   traces (450) + judge/pointjudge-3 (tax-15)
results/         the four-column tables per judged set
```

**Two judged 50s.** `models-1-judged-50` is a seeded random draw from the 500-task judging
pool; its gold-50 ties 6 of 36 candidate pairs. `models-1-judged-50-b` is disjoint from it
and was chosen among 500 seeded random draws as the one with the fewest candidate pairs tied
on gold-50 (0 of 36) — a selection that read the judging pool's outcomes and is disclosed
wherever the set is reported; the generalization outcomes were not read. Gold-gen for both is
`cap-8`, the 500-task generalization portion, never judged.

**Taxonomies.** tax-14 was induced by `new_pipeline` under `GENERATION_v2.md` from the
taxonomy pool (6 general, 8 domain codes), then amended by hand where four codes had
described the DSPy harness's own output markers as a breach — the amendment and its
correction are in `taxonomies/tax-14/README.md`. tax-15 adds one hand-authored code
(`SP_15`, conclusion unlicensed by the supplied evidence) for the family behind 42 of the 51
points `pointjudge-1` could not place; the fourteen carried codes are byte-identical.

**Judge.** Failure points: two readers (with / without the taxonomy) + decider,
gemini-3.6-flash readers, claude-sonnet-5 decider, thinking high, five calls per trace.
`pointjudge-1` read set a under tax-14 (450/450 judged, 1,637 points, 51 fitting nothing).
`pointjudge-1-sp15` is that mapping with SP_15 points appended from a single-reader tax-15
pass over the same traces (176 points on 87 traces) — the mapping the set-a results use,
labelled accordingly. `pointjudge-3` reads set b under tax-15 with the two-reader shape.

**Traces.** One JSON per trace, the judge's view of the four module turns; `metadata` gives
task, candidate id and index. Gold in `outcomes/`.
