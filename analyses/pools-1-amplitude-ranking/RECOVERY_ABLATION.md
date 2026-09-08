# Recovery-discounted blame: the August influence score on the current mappings

2026-09-08. `scripts/recovery_influence.py`. **Declared gold-using.** A mode's blame for a candidate
is `w_m = 1 − (recovered_m / appeared_m)^γ`, where "recovered" means the task nevertheless passed by
gold, estimated on the candidate's own judged tasks (support ≥ 3, else the candidate's failure
rate). Three aggregations: mode-first sum, per-task max (the August v1), per-task noisy-OR (v2).
Agreement with gold-50 is circular and is not reported as a result; the generalization column is
the only test.

## Against the generalization gold

| config | γ=1 max | γ=2 max | γ=3 max | best other aggregation |
|---|---:|---:|---:|---:|
| hover/tax-10 | **+0.61** (p=.005) | +0.42 | +0.27 | mode-sum γ=1 +0.39 |
| hover/tax-18 | **+0.61** (p=.006) | **+0.64** (p=.004) | +0.48 | mode-sum γ=1 +0.45 |
| ifbench | 0.00 | 0.00 | 0.00 | ceiling is 0.00 |
| hotpotqa | +0.17 | +0.17 | +0.20 | ceiling +0.36 |

Per-task max beats mode-sum and noisy-OR everywhere. The convex discount (γ=2) is not reliably
better than linear (γ=1): better on tax-18, worse on tax-10. On HoVer the score matches the
instruction-length baseline (+0.64) and is the first trace-derived number to do so.

## But the codes contribute nothing beyond the gold the score consumes

| hover/tax-10, γ=1 | vs gold gen | with gold-50 partialled out | with length partialled out |
|---|---:|---:|---:|
| recovery task-max | +0.61 | **0.00** (p=1.0) | +0.21 (p=.38) |
| gold-50 alone | +0.78 | — | **+0.58** (p=.01) |
| instruction length alone | +0.64 | +0.12 (p=.64) | — |

Partialling out the candidate's gold on the 50 tasks leaves the recovery score with zero
correlation to the generalization gold, on both taxonomies (+0.00, +0.03, +0.06). The score is a
lossy transform of gold-50: gold-50 alone reaches +0.78, the score +0.61. Everything it recovers
comes from the outcomes it reads, and the codes decide only how much of that is lost.

Gold-50 itself survives the length control (+0.58, p=.01) while length adds nothing beyond gold-50.
So on HoVer the ordering of what is known is: gold on 50 tasks (+0.78) > recovery-discounted
codes (+0.61) ≈ instruction word count (+0.64) > any outcome-free count of codes (+0.06).

## What this settles for the method

Recovery is the right evidence component and the discount shape is a detail. What the ablation
shows is that recovery *read from gold* is just gold. For the component to earn its place in an
outcome-free score, recovery has to be read from the trace: whether a mechanism's effect reached
the final output or was caught, contained or overwritten downstream. This judge does not record
that; the occurrence schema in `GENERATION_v2.md` has the slot for it.
