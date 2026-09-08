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
| placed (code, step) amplitude, equal weights | **no** | +0.50 (p=.025) | +0.12 |
| code-level amplitude, any placement | no | +0.06 | — |

The outcome-free line that matters is the fourth: firings both readers can place on a turn, counted
per (code, step), with no gold anywhere, reach +0.50. It carries almost nothing beyond gold-50 on its own (partial +0.12), so what gold-read
recovery adds is both the rise from +0.50 to +0.76 and the partial of +0.36, and the table above says exactly which units it acts on. A
trace-read recovery signal, whether the downstream steps corrected or ignored what happened at
summarize2, would have to reproduce that to earn the difference outcome-free.

## All benchmarks

Kendall tau-b against the generalization gold; "placed amp" is the outcome-free count of (code, step)
units per task; the recovery scores read gold for the recovery share; "partial" removes gold-50.

| config | rule | units | ceiling | placed amp, no gold | mode-sum γ=1 | partial | mode-sum γ=2 | partial | task-max γ=1 | partial |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| hover/tax-10 | both | 27 | +0.78 | **+0.50** (p=.03) | **+0.76** (p<.01) | +0.36 | **+0.73** (p<.01) | +0.39 | +0.64 | +0.03 |
| hover/tax-10 | any | 32 | +0.78 | +0.45 (p=.05) | +0.61 | +0.09 | +0.64 | +0.18 | +0.67 | +0.21 |
| hover/tax-18 | both | 33 | +0.78 | +0.41 (p=.08) | +0.52 | 0.00 | +0.45 | −0.06 | +0.61 | +0.15 |
| hover/tax-18 | any | 38 | +0.78 | +0.47 (p=.04) | +0.61 | +0.09 | +0.58 | +0.06 | **+0.76** (p<.01) | +0.39 |
| ifbench/tax-1 | both | 9 | 0.00 | +0.05 | 0.00 | −0.12 | +0.09 | 0.00 | +0.13 | +0.12 |
| ifbench/tax-1 | any | 12 | 0.00 | +0.19 | +0.09 | +0.09 | +0.16 | +0.15 | +0.19 | +0.18 |
| hotpotqa/tax-1 | both | 13 | +0.36 | −0.03 | +0.20 | +0.06 | +0.26 | +0.06 | +0.23 | +0.06 |
| hotpotqa/tax-1 | any | 17 | +0.36 | +0.12 | +0.20 | 0.00 | +0.20 | −0.12 | +0.29 | +0.09 |

IFBench has no ceiling to reach and nothing reaches anything. HotpotQA sits at +0.20 to +0.29
against a ceiling of +0.36, with partials at zero: the step split does not rescue a taxonomy that
lacks the mechanism deciding gold. On HoVer the step split takes every recovery variant to +0.45
or above on both taxonomies and under both rules; the single best cell per taxonomy reaches the
ceiling (tax-10 mode-sum/both +0.76, tax-18 task-max/any +0.76), and the partial after gold-50 is
positive but below significance in each.
