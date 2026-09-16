# Results

Every table: candidates ranked by the method from the judge's mapping of the judged tasks;
Kendall tau-b (tied pairs dropped) against gold-50 (pass rate on the judged tasks) and
gold-gen (pass rate on the generalization tasks); the third column is gold-50 vs gold-gen,
the bar; top-1 is whether the method's best candidate is gold-gen's best. Formulas in
`methods/README.md`. The raw tables with all eleven methods are the `results/*.md` files
named under each heading; they are the unedited output of
`code/methods_scripts/run_baselines.py`.

## livecodebench — 9 models, 50 judged tasks, 755 generalization tasks

### judge `pointjudge-1-tax2` (tax-2; 22 of 181 points hand-assigned, no re-judge)
`livecodebench/results/judging-50-1_pointjudge-1-tax2.md`

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| gold | +1.000 | +0.765 | +0.765 | yes |
| amplitude | +0.818 | +0.941 | +0.765 | yes |
| incidence | +0.939 | +0.824 | +0.765 | yes |
| combinations | +0.758 | +1.000 | +0.765 | yes |

### judge `pointjudge-1` (tax-1; the same run, the 22 unplaced points dropped)
`livecodebench/results/judging-50-1_pointjudge-1.md`

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| gold | +1.000 | +0.765 | +0.765 | yes |
| amplitude | +0.879 | +0.657 | +0.765 | no |
| incidence | +0.812 | +0.588 | +0.765 | no |
| combinations | +0.867 | +0.867 | +0.765 | no |

The two tables differ only in whether the 22 points the decider could not place carry a
code. Those 22 points (13 traces, almost all failing) move amplitude from +0.657 to +0.941
against gold-gen — four pair orderings among nine candidates. Which number stands is
settled by `pointjudge-2`, the judge pass with tax-2 in view on all 150 judging tasks
(pending). Gold-50 ties 2 of 36 pairs; the judged 50 under-weights easy tasks (16/17/17).

### judge `pointjudge-2` (tax-2 in view, 150 judged tasks) — pending

## hover / models — 9 models, 50 judged tasks, 500 generalization tasks

### set a, judge `pointjudge-1-sp15` (tax-15; SP_15 points lifted from a single-reader pass)
`hover/models/results/judged-50-a_pointjudge-1-sp15.md`

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| gold | +1.000 | +0.867 | +0.867 | yes |
| amplitude | +0.067 | +0.000 | +0.867 | no |
| incidence | +0.750 | +0.750 | +0.867 | no |
| combinations | −0.067 | +0.000 | +0.867 | no |

Gold-50 ties 6 of 36 pairs on this set. Amplitude carries no information; incidence —
whether anything fired at all — carries most of what gold-50 has.

### set b, judge `pointjudge-3` (tax-15, two readers + decider) — pending
Set b was drawn for an untied gold-50 (selection on the judging pool's outcomes, disclosed
in `hover/models/splits/models-1-judged-50-b/`).

## hover / GEPA_candidates — 12 instruction sets, 500 generalization tasks

### sample-50, judge `map-5` (tax-10, panel + open reader)
`hover/GEPA_candidates/results/sample-50_map-5.md`

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| gold | +1.000 | +0.785 | +0.785 | no |
| amplitude | +0.046 | +0.061 | +0.785 | no |
| incidence | −0.184 | −0.320 | +0.785 | no |
| combinations | +0.231 | +0.242 | +0.785 | no |

### judging-50, judge `map-6` (tax-10; the set was drawn stratified by mean candidate score)
`hover/GEPA_candidates/results/judging-50_map-6.md`

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| gold | +1.000 | +0.367 | +0.367 | no |
| amplitude | +0.017 | −0.077 | +0.367 | no |
| incidence | −0.347 | −0.283 | +0.367 | no |
| combinations | +0.233 | +0.000 | +0.367 | no |

### both sets, 100 judged tasks, `map-5` + `map-6`
`hover/GEPA_candidates/results/both-100_map-5+map-6.md`

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| gold | +1.000 | +0.742 | +0.742 | no |
| amplitude | +0.032 | −0.091 | +0.742 | no |
| incidence | −0.148 | −0.345 | +0.742 | no |
| combinations | +0.226 | +0.091 | +0.742 | no |

On the optimizer candidates no trace method carries signal on 50 or on 100 tasks, while
gold-50 on 100 tasks predicts the 500-task ranking at +0.742. The panel judge records codes
per trace only, so step-level methods are not computable here. Top-1 is "no" even for gold
because gold-50's best candidate differs from gold-gen's on every set.

## Reading across the benchmarks

Same nine models, same judge shape, same formulas: on livecodebench the mapping ranks them;
on hover it does not. The hover taxonomies describe the *form* of the modules' work (48% of
hover points are two form codes that fire on passing and failing traces alike) while the
gold is decided by whether the right entities were retrieved; the livecodebench codes name
what makes a program wrong, and nothing fires on passing traces (2 points on 298 passing
traces vs 151 on 152 failing). Whether that is a property of the benchmark, of the
taxonomy, or of single-step vs multi-step programs is the open question this branch is set
up to examine.
