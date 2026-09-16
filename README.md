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
| judged tasks | 150 | 50 + 50 | 50 + 50 |
| generalization tasks | 755 | 500 | 500 |
| taxonomy | tax-1 → tax-2 (7 + 3 codes) | tax-15 (15 codes) | tax-10 (10 codes) |
| judge | two readers + decider, failure points | same | two-annotator panel + open reader, code counts |

## Layout

```
methodology.md                 the process, start to end
methods/README.md              the scoring formulas, fully derived
livecodebench/                 program, task registry
livecodebench/models/          the 9 models on livecodebench: taxonomies, traces, judge runs, outcomes, results
hover/                         program, task registry
hover/GEPA_candidates/         the 12 optimizer candidates: taxonomy, traces, judge mappings, outcomes, results
hover/models/                  the 9 models on hover: taxonomies, traces, judge runs, outcomes, results
analysis/                      traces worth reading closely, with their judge records, per benchmark and candidate set
code/                          the pipeline, judge, capture and scoring code, as run
```

Every benchmark directory follows the same pattern: `traces/` holds one JSON per trace in the
judge's view (`{trace_id, messages, metadata}`), with the gold outcomes in a separate file
beside them and never inside a trace; `judge*/` holds the judge's mapping of those traces;
`results/` holds the tables produced by `code/methods_scripts/run_baselines.py` and `subsample_50.py`.

## Reading a result

Every results table has the same shape. For each scoring method the candidates are ranked
from the judge's mapping of the judged tasks, and that ranking is compared (Kendall tau-b,
tied pairs dropped) with the ranking by pass rate on the generalization tasks — disjoint,
never judged. The *gold* row is the same comparison for the judged tasks' own pass rate: the
bar a trace method has to clear. *Top-1* asks whether the method's best candidate is
gold-gen's best. `RESULTS.md` has every table; `methods/README.md` every formula.

## Headline

On livecodebench, reading 50 traces per candidate predicts the 755-task ranking about as
well as scoring those 50 tasks does — over ten random draws of 50, amplitude averages +0.80
and incidence +0.82 against gold-50's +0.81, and amplitude beats gold-50 on 6 of 10 draws.
On hover, for both candidate sets, both judges and every draw, no trace method clears the
bar; most are within ±0.2 of zero while gold-50 sits at +0.5 to +0.8.
