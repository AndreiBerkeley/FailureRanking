# Recovery-discounted blame with (code, step) as the unit

2026-09-08. `scripts/recovery_by_step.py`. **Declared gold-using**: recovery is read from the
candidate's own gold on the judged tasks. A mode is now a (code, agent-turn) pair, so Unsupported
Assertion at summarize1 and at summarize2 are two units with separate appear / recover counts and
separate blame. No relationships between units. Steps from `votes_by_turn`.

## HoVer, tax-10, both readers placing the code on the same turn

| γ | mode-first sum vs gold gen | partial, gold-50 removed | task-max | task-noisy-OR |
|---|---:|---:|---:|---:|
| 1 | **+0.76** (p<.001) | **+0.36** (p=.12) | +0.64 | +0.64 |
| 2 | +0.73 (p=.001) | +0.39 (p=.09) | +0.55 | +0.61 |
| 3 | +0.67 (p=.002) | +0.39 (p=.09) | +0.52 | +0.52 |

The ceiling is +0.78. Mode-first sum reaches it, and for the first time something survives
removing gold-50: a partial of +0.36 to +0.39, consistent across γ, though not significant on
twelve candidates. Leave-one-candidate-out: tau between +0.71 and +0.82, partial between +0.20
and +0.49, never negative. Not the work of one candidate.

Other cells are weaker and the pattern is not uniform: under the any-reader rule on tax-10 the
partial falls to +0.09 to +0.18; on tax-18 it is near zero under both-readers and +0.39 (p=.09) only
for task-max under any-reader. Across the 36 cells run, four have partial p<.15, which is about
what chance gives. The evidence for information beyond gold is the consistency within the
tax-10 / placed / mode-sum family and its leave-one-out stability, not any single p.

## Why the step split does what the code-level version could not

| unit | firings | unit rate vs gold gen | recovery share vs gold gen |
|---|---:|---:|---:|
| Missing Closing Marker @ summarize1 | 105 | +0.51 fires more on worse | −0.39 worse recover less |
| Unsupported Assertion @ summarize1 | 105 | +0.74 fires more on worse | +0.17 |
| Missing Closing Marker @ summarize2 | 90 | −0.46 fires more on **better** | +0.12 |
| Unsupported Assertion @ summarize2 | 52 | −0.32 fires more on **better** | **+0.54** better recover more |
| Misdirected Next Step @ hop3 | 49 | +0.72 fires more on worse | −0.29 |
| Premature Completion @ summarize1 | 41 | −0.52 fires more on better | **+0.45** |
| Work State Misjudged @ summarize2 | 23 | −0.44 fires more on better | **+0.77** |

The units that fire more on the better candidates, the exposure artefacts concentrated at
summarize2, are exactly the units those candidates recover from. Read through gold, "exposure"
becomes "fires but does not cost": the mechanism occurred and the task still passed. Per unit, the
recovery discount prices those firings near zero. At the code level the same code mixes a
summarize1 population with low recovery and a summarize2 population with high recovery, the
recovery share averages out, and the discount cannot tell them apart. That is why the step split
lifts mode-sum from +0.39 to +0.76 while the code-level version added nothing beyond gold.

## The ordering of what is known on HoVer, against the generalization gold

| score | reads gold? | tau | partial, gold-50 removed |
|---|---|---:|---:|
| gold on the 50 judged tasks | yes | +0.78 | — |
| recovery-discounted (code, step) mode-sum | yes, for recovery | +0.76 | +0.36 |
| instruction word count | no | +0.64 | +0.12 |
| placed (code, step) amplitude, equal weights | **no** | +0.50 | +0.30 |
| code-level amplitude, any placement | no | +0.06 | — |

The outcome-free line that matters is the fourth: firings both readers can place on a turn, counted
per (code, step), with no gold anywhere, reach +0.50. What gold-read recovery adds on top is the
difference between +0.50 and +0.76, and the table above says exactly which units it acts on. A
trace-read recovery signal, whether the downstream steps corrected or ignored what happened at
summarize2, would have to reproduce that to earn the difference outcome-free.
