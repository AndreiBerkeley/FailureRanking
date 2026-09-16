# model_ranking

Can a judge's reading of a small set of execution traces rank candidate systems as well as
their outcomes on that set — measured against the candidates' outcomes on a large, disjoint
task set? This branch holds everything behind that question: the tasks, the candidates, every
trace, the taxonomies, the judge's mappings, the formulas, and the results. Nothing here is
summarised from elsewhere; every number in `results/` recomputes from the files beside it.

| | livecodebench | hover / models | hover / GEPA_candidates |
|---|---|---|---|
| program | one model call writes a Python program | 4-module multi-hop retrieval (DSPy) | same |
| candidates | 9 models, one fixed prompt | 9 models, one fixed instruction set | 12 instruction sets, one model |
| judged tasks | 50 (+100 in progress) | 50 + 50 | 50 + 50 |
| generalization tasks | 755 | 500 | 500 |
| taxonomy | tax-1 → tax-2 (7 + 3 codes) | tax-15 (15 codes) | tax-10 (10 codes) |
| judge | two readers + decider, failure points | same | two-annotator panel + open reader, code counts |

## Layout

```
methodology.md                 the process, start to end
methods/README.md              the scoring formulas, fully derived
livecodebench/                 tasks, prompt, candidates, traces, taxonomies, generation run, judge runs, results
hover/                         program, task registry
hover/GEPA_candidates/         the 12 optimizer candidates: taxonomy, traces, judge mappings, outcomes, results
hover/models/                  the 9 models on hover: taxonomies, traces, judge runs, outcomes, results
analysis/                      traces with signal worth reading closely (pending)
code/                          the pipeline, judge, capture and scoring code, as run
```

Every benchmark directory follows the same pattern: `traces/` holds one JSON per trace in the
judge's view (`{trace_id, messages, metadata}`), with the gold outcomes in a separate file
beside them and never inside a trace; `judge*/` holds the judge's mapping of those traces;
`results/` holds the four-column tables produced by `code/methods_scripts/run_baselines.py`.

## Reading a result

Every results table has the same four columns. For each scoring method, the candidates are
ranked from the judge's mapping of the judged tasks, and that ranking is compared (Kendall
tau-b, tied pairs dropped) with two gold rankings: pass rate on the same judged tasks
(*gold-50*) and pass rate on the generalization tasks (*gold-gen*). The third column,
gold-50 vs gold-gen, is the same for every row: it is how well scoring the judged tasks
themselves predicts the large set, the bar a trace method has to clear. *Top-1* asks whether
the method's best candidate is gold-gen's best.

## Headline

On livecodebench, reading 50 traces per candidate predicts the 755-task ranking about as
well as, or better than, scoring those 50 tasks does: amplitude +0.657 vs gold-gen on the
judge's own mapping and +0.941 after 22 unplaced points were hand-assigned, against
gold-50's +0.765 — the re-judge with tax-2 in view (`pointjudge-2`) decides between those
two. On hover, amplitude is 0 for every candidate set and every judged set; incidence
reaches +0.75 on the models set and ≤ 0 on the optimizer candidates, while gold-50 reaches
+0.37 to +0.87. All tables, with their caveats, are in `RESULTS.md`.
