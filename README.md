# model_ranking

Can a judge's reading of a small set of execution traces rank candidate systems as well as
their outcomes on that set — measured against the candidates' outcomes on a large, disjoint
task set? This branch holds everything behind that question: the tasks, the candidates, every
trace, the taxonomies, the judge's mappings, the formulas, and the results. Nothing here is
summarised from elsewhere; every number in `results/` recomputes from the files beside it.

| | livecodebench | hover / models | hover / GEPA_candidates | terminalbench |
|---|---|---|---|---|
| program | one model call writes a Python program | 4-module multi-hop retrieval (DSPy) | same | Terminus 2 agent in a terminal (Terminal-Bench 2.0 leaderboard) |
| candidates | 9 models, one fixed prompt | 9 models, one fixed instruction set | 12 instruction sets, one model | 7 models |
| judged tasks | 150; the main results read the 50-task split | 50 + 50 | 50 (current instrument) · 50 + 50 (superseded panel judge) | 20, 19 usable |
| generalization tasks | 755 | 500 | 500 | 69 |
| taxonomy | tax-1 → tax-2 (7 + 3 codes) | tax-15 (15 codes) | tax-13 generated → tax-15-pool3 (13 + 2 hand codes) | tax-1 (10 codes) |
| judge | two readers + decider, failure points | same | same, with the program's success rule in view | same, with the success rule in view |
| recovery pass | all 150 (`recovery-1`) | set b (`recovery-2`) | yes | yes |
| unrecovered incidence vs gold-gen (bar: gold on the judged tasks) | +0.771 (+0.765) | +0.543 (+0.444) | +0.828 (+0.785) | +1.000 (+0.579) |

**Status 2026-10-03.** Four experiments, each with a recovery pass. The share of judged tasks whose trace
has a failure the program never recovered from (unrecovered incidence) ranks the candidates at least as well
as the judged tasks' own outcomes on all four: mean tau +0.785 against the bar's +0.643. Without the recovery
pass the best formula, last-turn incidence, averages +0.445. Read as a solve rate, 1 − unrecovered incidence is
on average 8.5 points from each candidate's generalization solve rate; the judged tasks' own solve rate is 6.8
points away. `sharing/best_methods.md` has every formula on all four, `sharing/formulas.md` defines each one
step by step, and `sharing/first_last_study.md` covers the scores built from each trace's first and last
failure instance.

## Layout

```
methodology.md                 the process, start to end
methods/README.md              the scoring formulas, fully derived
livecodebench/                 program, task registry
livecodebench/models/          the 9 models on livecodebench: taxonomies, traces, judge runs, outcomes, results
hover/                         program, task registry
hover/GEPA_candidates/         the 12 optimizer candidates: taxonomy, traces, judge mappings, outcomes, results
hover/models/                  the 9 models on hover: taxonomies, traces, judge runs, outcomes, results
terminalbench/                 program, task registry
terminalbench/models/          the 7 models on terminal-bench: taxonomy, its generation run, judged traces, judge and recovery runs, outcomes
sharing/                       the four experiments side by side: taxonomies, recovery reports, formulas, results, studies
analysis/                      traces worth reading closely, with their judge records, per benchmark and candidate set
code/                          the pipeline, judge, capture and scoring code, as run
```

Every benchmark directory follows the same pattern: `traces/` holds one JSON per trace in the
judge's view (`{trace_id, messages, metadata}`), with the gold outcomes in a separate file
beside them and never inside a trace; `judge*/` holds the judge's mapping of those traces;
`results/` holds the tables produced by `code/methods_scripts/run_baselines.py`, `subsample_50.py`,
`size_sweep.py`, `recovery_weighted.py` and `gen_set_sweep.py`. Where a recovery pass exists, `recovery-*/`
holds its verdict per point and `*-unrecovered/` the mapping with the recovered points removed.

## Reading a result

Every results table has the same shape. For each scoring method the candidates are ranked
from the judge's mapping of the judged tasks, and that ranking is compared (Kendall tau-b,
tied pairs dropped) with the ranking by pass rate on the generalization tasks — disjoint,
never judged. The *gold* row is the same comparison for the judged tasks' own pass rate: the
bar a trace method has to clear. *Top-1* asks whether the method's best candidate is
gold-gen's best. `RESULTS.md` has every table; `methods/README.md` every formula.

## Headline as of 2026-09-16, before the recovery pass

On livecodebench, reading 50 traces per candidate predicts the 755-task ranking about as
well as scoring those 50 tasks does — over ten random draws of 50, amplitude averages +0.80
and incidence +0.82 against gold-50's +0.81, and amplitude beats gold-50 on 6 of 10 draws.
On hover, for both candidate sets, both judges and every draw, no trace method clears the
bar; most are within ±0.2 of zero while gold-50 sits at +0.5 to +0.8.
