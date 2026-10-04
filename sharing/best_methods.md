# Best methods, without recovery and with it

Which formula orders the candidates most like their pass rates on the generalization set, and, for the formulas whose
score is on the scale of a solve rate, how far the number itself is from the solve rate. Formulas, the measure and the
solve-rate reading are defined in `formulas.md`; per-experiment detail is in `results.md` and `compared_scoring.md`.

**How "best" is chosen** (fixed before the table was read): in each arm, the formula with the highest *mean* tau-b against
the generalization set over the main experiments below. Formulas that read the judged tasks' gold are not candidates. Every
kept failure instance counts (an instance no code fit is its own pseudo-code). The selection is still made on the same
experiments it is reported on, so the best row's mean is optimistic by the size of the gaps between rows.

| experiment | candidates | judged tasks | generalization set |
|---|---:|---:|---|
| GEPA candidates · HoVer | 12 | 50 | eval-1 domain, 500 tasks |
| Models · HoVer (judged set b) | 9 | 50 | models-1 generalization, 500 tasks |
| Models · Terminal-Bench 2.0 | 7 | 19 | pools-1 eval, 69 tasks |
| Models · LiveCodeBench | 9 | 50 | pool_generalization, 755 tasks |
| Models · SWE-bench Verified | 12 | 50 | pools-4 eval, 405 tasks |
| Models · LiveCodeBench, all 150 judged tasks (supplementary) | 9 | 150 | pool_generalization, 755 tasks; shown after the mean, in no mean and no choice |

## Without recovery: every failure instance the judge kept

tau-b against the generalization set's pass rates (ties dropped); lower score is better for every formula.

| | GEPA·HoVer | Models·HoVer | Models·TB | Models·LCB (50) | Models·SWE | **mean** | Models·LCB, 150 (supp.) |
|---|---:|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.785* | *+0.444* | *+0.579* | *+0.765* | *+0.467* | *+0.608* | +0.941 |
| **incidence** (best) | -0.409 | +0.333 | +0.647 | +0.771 | +0.579 | +0.384 | +0.889 |
| amplitude | -0.385 | +0.000 | +0.895 | +0.882 | +0.446 | +0.368 | +0.889 |
| last-turn incidence | +0.365 | +0.310 | +0.333 | +0.771 | -0.094 | +0.337 | +0.889 |
| damped PIE, β=0.5 | -0.424 | -0.056 | +0.810 | +0.833 | +0.477 | +0.328 | +0.889 |
| worst mode | -0.587 | +0.257 | +1.000 | +0.576 | +0.344 | +0.318 | +0.611 |
| containment | -0.333 | +0.000 | +0.619 | +0.882 | +0.138 | +0.261 | +0.889 |
| patterns | -0.206 | -0.167 | +0.714 | +0.793 | +0.143 | +0.255 | +0.706 |
| step-amplitude | -0.406 | +0.000 | +0.600 | +0.882 | +0.138 | +0.243 | +0.889 |
| breadth | -0.519 | -0.059 | +0.455 | +1.000 | +0.220 | +0.220 | +0.565 |

## With recovery: unrecovered instances, plus the recovery-dependent formulas

tau-b against the generalization set's pass rates (ties dropped); lower score is better for every formula.

| | GEPA·HoVer | Models·HoVer | Models·TB | Models·LCB (50) | Models·SWE | **mean** | Models·LCB, 150 (supp.) |
|---|---:|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.785* | *+0.444* | *+0.579* | *+0.765* | *+0.467* | *+0.608* | +0.941 |
| **unrecovered incidence** (best) | +0.828 | +0.543 | +1.000 | +0.771 | +0.806 | +0.790 | +0.886 |
| unrecovered damped PIE, β=0.5 | +0.631 | +0.667 | +0.810 | +0.778 | +0.750 | +0.727 | +0.889 |
| unrecovered last-turn incidence | +0.833 | +0.697 | +0.700 | +0.771 | +0.357 | +0.672 | +0.886 |
| profile risk (own consequence, max) | +0.545 | +0.722 | +0.810 | +0.771 | +0.508 | +0.671 | +0.889 |
| unrecovered amplitude | +0.188 | +0.765 | +0.700 | +0.829 | +0.724 | +0.641 | +0.889 |
| unrecovered patterns | +0.344 | +0.588 | +0.474 | +0.857 | +0.574 | +0.567 | +0.657 |
| recovery-weighted amplitude, γ=1 | +0.182 | +0.778 | +0.619 | +0.829 | +0.385 | +0.558 | +0.889 |
| unrecovered step-amplitude | +0.188 | +0.771 | +0.619 | +0.829 | +0.323 | +0.546 | +0.889 |
| unrecovered containment | +0.385 | +0.657 | +0.524 | +0.829 | +0.323 | +0.543 | +0.889 |
| recovery-weighted amplitude, γ=2 | +0.000 | +0.833 | +0.619 | +0.829 | +0.415 | +0.539 | +0.889 |
| recovery-weighted amplitude, γ=3 | -0.182 | +0.889 | +0.524 | +0.829 | +0.415 | +0.495 | +0.889 |
| unrecovered breadth | +0.000 | +0.481 | +0.333 | +1.000 | +0.655 | +0.494 | +0.565 |
| unrecovered worst mode | -0.129 | +0.588 | +0.579 | +0.576 | +0.733 | +0.469 | +0.611 |

## Read as a solve rate: absolute distance from the actual solve rate

For each formula on the scale of a share of tasks, 1 − score is the share of judged tasks the traces say were solved. The
entry is the mean over candidates of |that share − the candidate's actual solve rate|, in percentage points. Formulas that
count (amplitude and the rest) are not on this scale and have no entry.

**Against the generalization set's solve rate** (the reference row is the judged tasks' own solve rate against it: the part
of the gap that is the task draw)

| | GEPA·HoVer | Models·HoVer | Models·TB | Models·LCB (50) | Models·SWE | **mean** | Models·LCB, 150 (supp.) |
|---|---:|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (reference)* | 3.7 | 7.6 | 11.6 | 4.5 | 9.6 | 7.4 | 3.0 |
| 1 − incidence | 55.3 | 43.9 | 41.8 | 5.1 | 73.1 | 43.8 | 4.0 |
| 1 − last-turn incidence | 18.9 | 37.5 | 10.2 | 5.1 | 20.7 | 18.5 | 4.0 |
| 1 − unrecovered incidence | 3.5 | 15.4 | 10.2 | 5.1 | 7.8 | 8.4 | 4.1 |
| 1 − unrecovered last-turn incidence | 8.4 | 18.5 | 7.9 | 5.1 | 19.9 | 12.0 | 4.1 |
| 1 − profile risk | 8.1 | 12.8 | 4.1 | 5.4 | 11.7 | 8.4 | 4.3 |

**Against the judged tasks' own solve rate** (same tasks the traces are from)

| | GEPA·HoVer | Models·HoVer | Models·TB | Models·LCB (50) | Models·SWE | **mean** | Models·LCB, 150 (supp.) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 − incidence | 52.2 | 48.9 | 33.1 | 1.6 | 63.5 | 39.8 | 1.3 |
| 1 − last-turn incidence | 15.8 | 42.4 | 10.5 | 1.6 | 17.8 | 17.6 | 1.3 |
| 1 − unrecovered incidence | 4.7 | 10.4 | 6.0 | 1.6 | 15.3 | 7.6 | 1.4 |
| 1 − unrecovered last-turn incidence | 11.5 | 13.6 | 16.5 | 1.6 | 29.5 | 14.5 | 1.4 |
| 1 − profile risk | 5.2 | 9.2 | 9.6 | 1.5 | 12.7 | 7.6 | 1.4 |

Generated by `scripts/best_methods.py` from the recorded judge and recovery runs; no model call.
