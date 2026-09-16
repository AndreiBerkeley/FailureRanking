# Results

Every number: candidates ranked by a method from the judge's mapping of the judged tasks;
Kendall tau-b (tied pairs dropped) against the candidates' pass rate on the generalization
tasks (*gold-gen*), which were never judged. The **gold** row is the same comparison for the
judged tasks' own pass rate — the bar every trace method is read against. *Top-1*: is the
method's best candidate gold-gen's best. Formulas in `methods/README.md`; every table is the
unedited output of `code/methods_scripts/run_baselines.py` or `subsample_50.py`, filed
under the `results/` path named beneath it.

## livecodebench — 9 models · tax-2 · judge `pointjudge-2` · gold-gen on 755 tasks

Judge: two readers + decider with tax-2 in view, all 150 judging-pool tasks, 1,350 traces,
627 points, 3 unplaced. On this one-step program step-amplitude and containment equal
amplitude and are not listed.

### all 150 judged tasks
`livecodebench/models/results/judging-150_pointjudge-2.md`

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| gold | +0.941 | yes |
| amplitude | +0.889 | no |
| incidence | +0.889 | yes |
| combinations | +0.771 | no |

### ten random draws of 50 from the 150
`livecodebench/models/results/subsamples-50x10_pointjudge-2.md` — seeds 1–10, uniform, no stratification.

| draw | gold-50 | amplitude | incidence | combinations | top-1 amp / inc / comb |
|---|---:|---:|---:|---:|---|
| 1 | +0.778 | +0.941 | +0.879 | +0.833 | yes / yes / yes |
| 2 | +0.758 | +0.778 | +0.882 | +0.706 | no / yes / no |
| 3 | +0.875 | +0.667 | +0.765 | +0.588 | no / no / no |
| 4 | +0.714 | +0.765 | +0.647 | +0.722 | no / no / no |
| 5 | +0.938 | +0.829 | +0.879 | +0.722 | no / yes / no |
| 6 | +0.833 | +0.706 | +0.771 | +0.500 | no / yes / no |
| 7 | +0.758 | +0.765 | +0.771 | +0.556 | yes / yes / no |
| 8 | +0.941 | +0.829 | +0.939 | +0.771 | no / yes / no |
| 9 | +0.824 | +0.882 | +0.824 | +0.829 | yes / yes / yes |
| 10 | +0.657 | +0.829 | +0.875 | +0.824 | yes / yes / yes |
| **mean** | +0.808 | +0.799 | +0.823 | +0.705 | |

Draws where the method beats gold-50: amplitude 6/10, incidence 4/10, combinations 4/10.

On a random 50, reading the traces and scoring the outcomes predict the 755-task ranking
about equally well (+0.80–0.82 vs +0.81), and which one wins is the draw. On all 150 the
gold pulls ahead (+0.941 vs +0.889).

### the two named judged sets, for the record
`judging-50-1_pointjudge-2.md` (50, easy under-weighted 16/17/17): gold +0.765, amplitude +0.882,
incidence +0.771, combinations +0.833. `judging-100-1_pointjudge-2.md` (the other 100): gold
+0.886, amplitude +0.829, incidence +0.889, combinations +0.722. The earlier tax-1 pass on the
first 50 (`judging-50-1_pointjudge-1.md`, 22 points unplaced) gave amplitude +0.657; with those
22 hand-assigned (`…_pointjudge-1-tax2.md`) +0.941 — the real tax-2 pass lands between them.

## hover / models — 9 models · tax-15 · judge pointjudge · gold-gen on 500 tasks

Judge: two readers + decider. Set a (`models-1-judged-50`, random draw): `pointjudge-1` under
tax-14 with the SP_15 points appended from a single-reader tax-15 pass (`pointjudge-1-sp15`).
Set b (`models-1-judged-50-b`, drawn for an untied gold-50 — selection on the judging pool's
outcomes, disclosed): `pointjudge-3` under tax-15, two readers + decider. Same 15 codes; the
two sets are pooled for the 100-task table and the draws. Step methods apply: four modules.

### both sets, 100 judged tasks
`hover/models/results/both-100_pointjudge-1-sp15_pointjudge-3.md`

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| gold | +0.529 | yes |
| amplitude | +0.056 | no |
| incidence | +0.200 | no |
| combinations | +0.111 | no |
| step-amplitude | +0.111 | no |
| containment | +0.167 | no |

### ten random draws of 50 from the 100
`hover/models/results/subsamples-50x10_both-100.md`

| draw | gold-50 | amplitude | incidence | combinations | step-amp | containment | top-1 amp / inc / comb / step / cont |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | +0.438 | +0.056 | +0.143 | +0.200 | +0.222 | +0.222 | no / no / no / no / no |
| 2 | +0.486 | −0.056 | +0.200 | −0.056 | +0.111 | +0.056 | no / no / no / no / no |
| 3 | +0.588 | +0.000 | +0.200 | −0.111 | +0.111 | +0.111 | no / no / no / no / no |
| 4 | +0.636 | +0.056 | +0.333 | +0.056 | +0.111 | +0.167 | no / no / no / no / no |
| 5 | +0.543 | +0.056 | +0.333 | +0.111 | +0.111 | +0.111 | no / no / no / no / no |
| 6 | +0.647 | +0.200 | +0.143 | +0.056 | +0.167 | +0.167 | no / no / no / no / no |
| 7 | +0.697 | +0.000 | +0.200 | +0.111 | +0.111 | +0.167 | no / no / no / no / no |
| 8 | +0.375 | +0.167 | +0.333 | +0.167 | +0.167 | +0.167 | no / no / no / no / no |
| 9 | +0.278 | +0.111 | +0.143 | −0.111 | +0.086 | +0.111 | no / no / no / no / no |
| 10 | +0.394 | −0.029 | +0.143 | +0.056 | +0.056 | +0.029 | no / no / no / no / no |
| **mean** | +0.508 | +0.056 | +0.217 | +0.048 | +0.125 | +0.131 | |

No method beats gold-50 on any draw.

### the two named sets
`judged-50-a_pointjudge-1-sp15.md`: gold +0.867, amplitude +0.000, incidence +0.750,
combinations +0.000, step-amplitude +0.111, containment +0.111.
`judged-50-b_pointjudge-3.md`: gold +0.444, amplitude −0.056, incidence +0.200,
combinations +0.056, step-amplitude +0.000, containment +0.000. Set a's incidence +0.750 is
the only hover value above 0.35 anywhere and does not repeat on set b or on any draw.

## hover / GEPA_candidates — 12 instruction sets · tax-10 · panel judge · gold-gen on 500 tasks

Judge: two-annotator panel + open reader. `map-5` on `eval-1/sample` (50, random); `map-6` on
`judging-sample-2` (50, stratified by mean candidate score — selection on the judging pool's
outcomes, disclosed). Pooled for the 100-task table and the draws. Steps for the two
step-attributed methods come from the judge records: a code that counted is placed at every
turn an annotator reported it and at the turn of every open-reader problem mapped to it —
the same turns the per-trace count was built from (every counted code has at least one).

### both sets, 100 judged tasks
`hover/GEPA_candidates/results/both-100_map-5_map-6.md`

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| gold | +0.742 | no |
| amplitude | −0.091 | no |
| incidence | −0.345 | no |
| combinations | +0.091 | no |
| step-amplitude | +0.061 | no |
| containment | +0.323 | no |

### ten random draws of 50 from the 100
`hover/GEPA_candidates/results/subsamples-50x10_both-100.md`

| draw | gold-50 | amplitude | incidence | combinations | step-amp | containment | top-1 amp / inc / comb / step / cont |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | +0.621 | −0.152 | −0.585 | +0.091 | +0.000 | +0.273 | no / no / no / no / no |
| 2 | +0.815 | +0.030 | −0.053 | +0.152 | +0.152 | +0.415 | no / no / no / no / no |
| 3 | +0.627 | −0.231 | −0.423 | +0.061 | +0.015 | +0.312 | no / no / no / no / no |
| 4 | +0.633 | −0.061 | −0.259 | +0.152 | +0.091 | +0.292 | no / no / no / no / no |
| 5 | +0.778 | +0.015 | −0.333 | +0.273 | +0.152 | +0.424 | no / no / no / no / no |
| 6 | +0.867 | −0.016 | −0.138 | +0.030 | +0.091 | +0.212 | no / no / no / no / no |
| 7 | +0.692 | +0.094 | −0.583 | +0.212 | +0.212 | +0.242 | no / no / no / no / no |
| 8 | +0.746 | −0.077 | −0.393 | +0.030 | +0.094 | +0.323 | no / no / no / no / no |
| 9 | +0.841 | −0.046 | −0.176 | +0.030 | +0.156 | +0.303 | no / no / no / no / no |
| 10 | +0.700 | −0.030 | −0.088 | +0.182 | +0.152 | +0.273 | no / no / no / no / no |
| **mean** | +0.732 | −0.047 | −0.303 | +0.121 | +0.112 | +0.307 | |

No method beats gold-50 on any draw. Incidence is consistently negative: the candidates on
which something fires more often are the better ones. Containment is the one method with a
consistent positive sign on this set (+0.21 to +0.42 on every draw), still well under the
bar. Top-1 is "no" even for gold because gold-50's best candidate differs from gold-gen's
on every set.

### the two named sets
`sample-50_map-5.md`: gold +0.785, amplitude +0.061, incidence −0.320, combinations +0.242,
step-amplitude +0.121, containment +0.364.
`judging-50_map-6.md`: gold +0.367, amplitude −0.077, incidence −0.283, combinations +0.000,
step-amplitude +0.108, containment +0.333.

## Across the benchmarks

Same nine models, same judge, same formulas: on livecodebench the trace read is level with
the outcomes on 50 tasks; on hover it carries nothing, for either candidate set, either
judge, any draw. The hover taxonomies describe the *form* of the modules' work — on the
models set two form codes make up 48% of all points and fire on passing and failing traces
alike — while the gold is decided by which entities were retrieved; the livecodebench codes
name what makes a program wrong, and on the first judged 50 nothing fired on 296 of 298
passing traces. Whether that is the benchmark, the taxonomy, or single-step vs multi-step
programs is the open question this branch is set up to examine.
