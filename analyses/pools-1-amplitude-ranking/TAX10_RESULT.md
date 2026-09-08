# What re-levelling changed: tax-10 against tax-18 on the same 600 HoVer traces

`map-5`, 2026-09-08: the 50 judged tasks × 12 candidates judged under `tax-10`, one trace per call
(no batching, so no instruction can leak between traces), 2 panel readers plus the open reader.
600 of 600 judged: 599 on the first pass (4 h 14 m) and the last on 2026-09-08 after a run of
provider 503s. Archived as `data/hover/mappings/map-5`, all audits passing.

## The headline is unchanged

| scored over | gold 50 vs judge 50 | gold generalization vs judge 50 |
|---|---:|---:|
| tax-18, 18 codes (map-3) | +0.12 | +0.02 |
| tax-10, 10 codes (map-5) | +0.05 | +0.06 |

On the complete 600: domain codes +0.23, general codes −0.31, all ten +0.06.
| ceiling: gold 50 vs gold generalization | | +0.78 |

A plain sum of codes still carries no ranking signal.

## But the instrument is now honest, and the residual has one name

**The two columns point in opposite directions and cancel.**

| scored over | gold generalization |
|---|---:|
| the 6 domain codes (the work itself) | **+0.23** |
| the 4 general codes (intake and output edges) | **−0.31** |
| all 10 | +0.06 |

**8 of 10 codes now point the right way**, where under tax-18 six of the eleven frequent codes
pointed the wrong way. **Task-level lift is positive for 8 of 10**: a code's firing now predicts
that the task failed, weakly but consistently. The best are Input Misreading (62% of its firings on
failing tasks, lift +0.14) and Unlicensed Conclusion (57%, +0.17).

**Length proxying is much reduced but not gone.** The worst correlation between a code's rate and
candidate instruction length fell from 0.78 to 0.64, and seven of ten codes are now below 0.36.

**Two codes remain length proxies, and both are general:**

| code | rate vs gold | rate vs instruction length |
|---|---:|---:|
| RL_08 Work State Misjudged | −0.60 | −0.64 |
| RL_01 Output Form Breach | −0.50 | −0.63 |

This is not a wording defect any more; it is **exposure**. A candidate whose instructions impose no
form requirement cannot breach form, and one that never tracks the state of its work explicitly has
less state to misjudge. Re-levelling stopped the judge from applying rules a candidate never had.
It cannot, by itself, make a candidate with fewer requirements comparable to one with more.

Dropping those two codes lifts the sum to **+0.37 on the judged 50 and +0.26 on the generalization
pool**. That selection uses gold, so it is a diagnostic and not a method — but it locates the loss
precisely: the signal is present in the codes and the aggregation destroys it.

## What this settles

The two-part diagnosis from the firing audit is confirmed by measurement. Part one, codes written at
the wrong level, is fixed: the codes now describe mechanisms every candidate could exhibit, and they
behave accordingly. Part two, exposure, is untouched and is now the whole of the residual. The next
move is the one the mode-first discussion arrived at: a rate per opportunity,
`occ_m(c) / exp_m(c)`, where the exposure count comes from the candidate's contract rather than from
the count of tasks.
