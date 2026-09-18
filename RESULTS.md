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

### agreement vs judged-set size
`livecodebench/models/results/size-sweep_pointjudge-2.md` — 20 uniform draws at each k (one at k = 150, the whole set); draws at large k overlap, so their spread shrinks for that reason alone. Step-amp and containment equal amplitude here.

| k | draws | gold-k | amplitude | incidence | combinations | step-amp | containment | beats gold-k |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 10 | 20 | +0.620 | +0.593 | +0.598 | +0.540 | +0.593 | +0.593 | amplitude 10/20, incidence 7/20, combinations 7/20, step-amp 10/20, containment 10/20 |
| 20 | 20 | +0.724 | +0.691 | +0.705 | +0.605 | +0.691 | +0.691 | amplitude 9/20, incidence 8/20, combinations 6/20, step-amp 9/20, containment 9/20 |
| 30 | 20 | +0.752 | +0.682 | +0.738 | +0.595 | +0.682 | +0.682 | amplitude 8/20, incidence 7/20, combinations 1/20, step-amp 8/20, containment 8/20 |
| 50 | 20 | +0.783 | +0.775 | +0.794 | +0.692 | +0.775 | +0.775 | amplitude 10/20, incidence 9/20, combinations 8/20, step-amp 10/20, containment 10/20 |
| 75 | 20 | +0.832 | +0.815 | +0.835 | +0.761 | +0.815 | +0.815 | amplitude 8/20, incidence 5/20, combinations 4/20, step-amp 8/20, containment 8/20 |
| 100 | 20 | +0.874 | +0.836 | +0.877 | +0.764 | +0.836 | +0.836 | amplitude 6/20, incidence 9/20, combinations 3/20, step-amp 6/20, containment 6/20 |
| 150 | 1 | +0.941 | +0.889 | +0.889 | +0.771 | +0.889 | +0.889 | amplitude 0/1, incidence 0/1, combinations 0/1, step-amp 0/1, containment 0/1 |

Both curves rise with k and stay within 0.05 of each other up to k = 100; at k = 150 gold is
ahead by 0.05 on a single draw. There is no crossover in either direction: on this
benchmark, n judged traces and n outcomes carry about the same ranking information at every
n tried.

On a random 50, reading the traces and scoring the outcomes predict the 755-task ranking
about equally well (+0.80–0.82 vs +0.81), and which one wins is the draw. On all 150 the
gold pulls ahead (+0.941 vs +0.889). Why not +1: points per failing trace differ by model
(1.00–1.54), some failures leave nothing to read (time limits, sandbox modules, recursion
depth), a few passing programs draw complexity warnings, two candidate pairs are within
0.004 on gold-gen, and the checker itself rejects valid answers on some tasks —
`analysis/livecodebench_model/README.md`, "Why it is still not perfect", with the per-model
counts.

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

### agreement vs judged-set size
`hover/models/results/size-sweep_both-100.md`

| k | draws | gold-k | amplitude | incidence | combinations | step-amp | containment | beats gold-k |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 10 | 20 | +0.330 | -0.031 | +0.525 | +0.006 | +0.016 | +0.048 | amplitude 1/20, incidence 9/20, combinations 2/20, step-amp 4/20, containment 5/20 |
| 20 | 20 | +0.378 | -0.014 | +0.446 | +0.017 | +0.033 | +0.056 | amplitude 1/20, incidence 12/20, combinations 1/20, step-amp 1/20, containment 2/20 |
| 30 | 20 | +0.400 | +0.010 | +0.381 | +0.017 | +0.045 | +0.070 | amplitude 0/20, incidence 8/20, combinations 1/20, step-amp 1/20, containment 1/20 |
| 50 | 20 | +0.500 | +0.029 | +0.274 | +0.048 | +0.093 | +0.097 | amplitude 0/20, incidence 3/20, combinations 0/20, step-amp 0/20, containment 0/20 |
| 75 | 20 | +0.501 | +0.076 | +0.212 | +0.097 | +0.123 | +0.126 | amplitude 0/20, incidence 1/20, combinations 0/20, step-amp 0/20, containment 0/20 |
| 100 | 1 | +0.529 | +0.056 | +0.200 | +0.111 | +0.111 | +0.167 | amplitude 0/1, incidence 0/1, combinations 0/1, step-amp 0/1, containment 0/1 |

Incidence's +0.5 at k = 10 is not a signal: on hover something fires on 889 of 900 traces,
so at k = 10 most candidates have incidence exactly 1.0 and the tau is computed on ~7 of 36
pairs (12 at k = 20, 17 at k = 50, 21 at k = 100); it falls toward +0.2 as pairs become
untied. Every other method is flat near zero at every k.

### the two named sets
`judged-50-a_pointjudge-1-sp15.md`: gold +0.867, amplitude +0.000, incidence +0.750,
combinations +0.000, step-amplitude +0.111, containment +0.111.
`judged-50-b_pointjudge-3.md`: gold +0.444, amplitude −0.056, incidence +0.200,
combinations +0.056, step-amplitude +0.000, containment +0.000. Set a's incidence +0.750 is
the only hover value above 0.35 anywhere and does not repeat on set b or on any draw.

### set b with the recovery pass (2026-09-16) — points the reader found unrecovered
`hover/models/results/judged-50-b_pointjudge-3_unrecovered.md` — `pointjudge-3` under tax-15, every
point read by the recovery pass (`recovery-1`, Sonnet 5, before the success rule; its audit found
15% of its "recovered" verdicts wrong, see `hover/GEPA_candidates/results/explored-formulas.md`
§8), then the recovered points removed. Same 50 tasks, same gold-50 bar.

| method | tau vs gold-gen | top-1 | tau vs gold-50 |
|---|---:|---|---:|
| gold | +0.444 | yes | — |
| amplitude | +0.722 | no | +0.389 |
| incidence | +0.750 | no | +0.312 |
| last-turn incidence | +0.758 | no | +0.333 |
| step-amplitude | +0.714 | no | +0.257 |
| containment | +0.771 | no | +0.200 |
| combinations | +0.611 | yes | +0.278 |

Every method clears the bar once the recovered points are out; before the pass none did
(+0.20 at best). The recovery-weighted variants (`recovery-weighted_judged-50-b.md`) reach
+0.889 per-candidate at γ=3 on this set — and do not repeat on the GEPA set below.

## hover / GEPA_candidates — 12 instruction sets · tax-15-pool3 · pointjudge + recovery · gold-gen on 500 tasks

The current instrument (2026-09-17/18; `hover/GEPA_candidates/README.md`): taxonomy `tax-13`
generated by GENERATION_v3.1, extended by hand to `tax-15-pool3` for the two mechanisms the
judge found and could not name; the two-reader + decider judge (Luna readers, Sol decider)
with the program's success rule in view, 3,043 points on the 600 traces of `eval-1/sample`;
the recovery pass (Sonnet 5, rule in view) over every point, 839 unrecovered. Scores are
computed on the **unrecovered points** unless marked raw. Gold-gen is the 500-task
`eval-1/domain`, disjoint from the judged 50.

### the judged 50 — incidence in every scenario
`sample-50_pointjudge-1-tax15_unrecovered.md`, `…_raw.md`, `…-tax13_unrecovered.md`

| scenario | incidence vs gold-gen | top-1 | vs gold-50 | gold-50 vs gold-gen (bar) |
|---|---:|---|---:|---:|
| raw judge points, no recovery (tax-15-pool3) | −0.409 | no | −0.636 | +0.785 |
| unrecovered points, tax-13 codes only (the 138 uncoded unrecovered points dropped) | +0.738 | yes | +0.600 | +0.785 |
| unrecovered points, tax-15-pool3 (every point the decider kept) | **+0.828** | **yes** | **+0.860** | +0.785 |
| last-turn incidence, same mapping (an unrecovered point on the final hop) | +0.833 | no | +0.966 | +0.785 |

Raw, every method is negative: the GEPA-optimised candidates carry longer instructions and
the instruction-compliance codes fire more on them. With the recovery pass, incidence is
level with the judged tasks' own outcomes and above the bar on the full generalization set.
The 138 unrecovered points that fit no tax-13 code are 16% of the unrecovered evidence and
fall unevenly across candidates; dropping them costs 0.09 — hence tax-15-pool3.

### incidence vs judged-set size
`size-sweep_sample-50_unrecovered.md` — 30 uniform draws of k tasks from the 50 (one draw at k = 50).

| k | draws | gold-k | incidence | last-turn incidence | containment | amplitude | incidence beats gold-k |
|---:|---:|---:|---:|---:|---:|---:|---|
| 10 | 30 | +0.598 | +0.403 | +0.600 | +0.208 | +0.081 | 3/30 |
| 20 | 30 | +0.751 | +0.536 | +0.686 | +0.313 | +0.136 | 1/30 |
| 30 | 30 | +0.780 | +0.639 | +0.717 | +0.325 | +0.159 | 3/30 |
| 40 | 30 | +0.789 | +0.708 | +0.745 | +0.340 | +0.152 | 5/30 |
| 50 | 1 | +0.785 | +0.828 | +0.833 | +0.354 | +0.143 | 1/1 |

Incidence climbs with k while gold-k saturates from k = 30; each trace flag carries ~10%
error (12% of failed traces unflagged, 6% of passed traces flagged), so the trace signal
needs more tasks than the outcomes do to settle. The +0.828 at k = 50 is the top of its own
distribution: at k = 40 the mean is +0.708 and incidence beats gold-k on 5 of 30 draws. The
fair statement is that incidence on 50 judged tasks is about as informative as the 50
outcomes; the full set landed high. The last-turn flag is above incidence at every k.

### incidence vs many generalization sets
`gen-set-sweep_sample-50_unrecovered.md` — the scores fixed, the 500-task target resampled.

| gen-set size | gold-50 | incidence | last-turn incidence |
|---:|---:|---:|---:|
| 50 (30 draws) | +0.689 ± 0.12 | +0.693 ± 0.13 | +0.724 ± 0.11 |
| 100 (30 draws) | +0.766 ± 0.08 | +0.764 ± 0.10 | +0.798 ± 0.08 |
| 300 (30 draws) | +0.771 ± 0.05 | +0.783 ± 0.08 | +0.829 ± 0.05 |
| 300 (ten named draws) | +0.760 ± 0.04 | +0.783 ± 0.08 · beats gold-50 7/10 | +0.814 ± 0.04 · 10/10 |
| 500 (all) | +0.785 | +0.828 | +0.833 |
| five disjoint parts of 100 | +0.65 … +0.84 | +0.60 … +0.86 | +0.65 … +0.90 |

Incidence and gold-50 are the same predictor: their means agree within 0.04 at every size
and their spreads overlap entirely. The target is itself noisy — the full 500-task gold-gen
agrees with its own disjoint 100-task parts at +0.72 … +0.94, and the top six candidates
sit within 0.02 of each other on it — so anything above ~+0.8 here is inside the target's
own noise band. Last-turn incidence is the only score consistently at or above gold-50
(above it on 10 of 10 named draws, never below +0.73).

### the other formulas
`sample-50_pointjudge-1-tax15_unrecovered.md`, `recovery-weighted_recovery-2-tax15.md`, `explored-formulas.md`

On the same unrecovered mapping: containment +0.354, patterns +0.344, step-amplitude
+0.188, amplitude +0.143, breadth 0.000, worst mode −0.129, combinations −0.169; the
recovery-weighted (code, step) units +0.182 at best (per-candidate γ=1; pooled −0.515).
Everything else that was tried — per-task units other than the plain flag, failure-mode-
centric aggregations, a Shapley blame decomposition, profile-risk models with pooled or
candidate-specific consequences in seven context bases, and a split-half transfer test of the
profile — is written up with its numbers in `explored-formulas.md`; the best of each family
is: per-task flags +0.83, profile risk with the candidate's own rates +0.61, containment
+0.35, mode-centric +0.18, recovery-weighted +0.18, pooled-consequence profiles ≤ 0. The
reason is the same throughout: amplitude is incidence times the unrecovered points per
failed task, and that factor has tau −0.24 on its own (the best candidate gets 4.6 points per
failed task, the worst three 2.6–3.0); code composition is a class signature whose sign flips
across codes; and the modes on a task recover jointly, so per-mode rates combined under
independence over-count verbose candidates. What transfers is whether a task has an
unrecovered failure, not how many points or which codes describe it.

## hover / GEPA_candidates (superseded) — tax-10 · panel judge · gold-gen on 500 tasks

Kept for the record: the panel judge under the hand-levelled tax-10, before the success rule,
the recovery pass and the pointjudge. Superseded by the section above on the same 50 tasks.

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

### agreement vs judged-set size
`hover/GEPA_candidates/results/size-sweep_both-100.md`

| k | draws | gold-k | amplitude | incidence | combinations | step-amp | containment | beats gold-k |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 10 | 20 | +0.449 | -0.053 | -0.253 | +0.062 | +0.054 | +0.205 | amplitude 2/20, incidence 2/20, combinations 3/20, step-amp 3/20, containment 4/20 |
| 20 | 20 | +0.574 | -0.099 | -0.280 | +0.033 | +0.030 | +0.275 | amplitude 0/20, incidence 0/20, combinations 0/20, step-amp 0/20, containment 1/20 |
| 30 | 20 | +0.631 | -0.078 | -0.242 | +0.058 | +0.057 | +0.268 | amplitude 0/20, incidence 0/20, combinations 0/20, step-amp 0/20, containment 1/20 |
| 50 | 20 | +0.692 | -0.064 | -0.321 | +0.102 | +0.092 | +0.302 | amplitude 0/20, incidence 0/20, combinations 0/20, step-amp 0/20, containment 0/20 |
| 75 | 20 | +0.719 | -0.049 | -0.329 | +0.119 | +0.072 | +0.328 | amplitude 0/20, incidence 0/20, combinations 0/20, step-amp 0/20, containment 0/20 |
| 100 | 1 | +0.742 | -0.091 | -0.345 | +0.091 | +0.061 | +0.323 | amplitude 0/1, incidence 0/1, combinations 0/1, step-amp 0/1, containment 0/1 |

Flat at every k: amplitude and step-amplitude near zero, incidence negative, containment
+0.2 to +0.3, while gold-k climbs from +0.45 to +0.74.

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

Same formulas everywhere. On livecodebench the trace read is level with the outcomes on 50
tasks and the point count itself tracks outcome (amplitude +0.89 on 150 tasks). On hover the
raw read carried nothing for either candidate set: the taxonomies name the *form* of the
modules' work, which the multi-step program mostly absorbs, and the instruction-compliance
codes fire more on the better-instructed candidates. Two changes made hover measurable — a
separate recovery pass that reads each point's fate in the final output, and putting the
program's success rule (documents by title, mentions do not count) in front of both the judge
and the recovery reader — and with them **incidence over unrecovered points** reaches
+0.75 on the models set (gold-50 bar +0.44) and +0.83 on the GEPA set (bar +0.785), and
last-turn incidence +0.76 / +0.83. What transfers on hover is whether a task has an
unrecovered failure, not how many points or which codes describe it: every count- or
code-weighted formula sits at +0.35 or below on the GEPA set for reasons the exploration
write-up gives in numbers. The open question is now the one this leaves: a per-task flag is
the outcomes reconstructed from traces, and the candidate's failure profile — which modes,
how reliably it recovers each — is the object that should generalize; at 50 tasks its
factors are too noisy to beat the flag, and the repeats of the judged tasks are the way to
find out whether they can.
