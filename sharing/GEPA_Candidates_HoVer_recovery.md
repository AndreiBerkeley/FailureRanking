# GEPA candidates · HoVer (12 candidates, 50 judged tasks) — recovery pass

Recovery reader: `anthropic/claude-sonnet-5` (thinking HIGH), success rule in view: **yes**.
Judge mapping read: `runs/new_pipeline/hover/pointjudge-1`; taxonomy `sharing/GEPA_Candidates_HoVer_taxonomy.json` (15 codes).
Traces with a recovery verdict: **600** (12 candidates × 50 tasks). One call per trace: the reader sees the whole trace and the judge's failure instances, and gives each instance one verdict.
- The judge (tax-13, readers Luna, decider Sol) kept 170 instances no code fit; SP_14 and SP_15 were assigned to them by hand afterwards. Recovery verdicts were given before that relabelling and carried over unchanged.

## Verdicts over every failure instance

| verdict | instances | share | meaning |
|---|---:|---:|---|
| corrected | 566 | 18.6% | a later step replaced the wrong thing and the output does not carry it |
| contained | 1638 | 53.8% | the output does not carry it and nothing corrected it: nothing downstream used it, or it was used and the output was fine regardless, or another path supplied what was needed |
| unrecovered | 839 | 27.6% | the effect is in the final output, or what the instance cost is missing from it, or the trace cannot show otherwise |
| **recovered (corrected + contained)** | **2204** | **72.4%** | removed for the unrecovered-only scores |
| **left standing (unrecovered)** | **839** | **27.6%** | what the unrecovered-only scores read |

## Per trace (one candidate on one task), before and after

| | before recovery | after (unrecovered only) |
|---|---:|---:|
| failure instances per trace, mean | 5.07 | 1.40 |
| distinct failure modes per trace, mean | 3.39 | 1.01 |
| traces with at least one instance | 587 of 600 (98%) | 256 of 600 (43%) |

## Per candidate

| candidate | traces | instances before | per trace | corrected | contained | unrecovered | unrec. per trace | traces flagged before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `cnd-d680fd9955b0` | 50 | 274 | 5.5 | 42 | 176 | 56 | 1.12 | 49 → 21 |
| `cnd-9de4bb39803c` | 50 | 264 | 5.3 | 66 | 141 | 57 | 1.14 | 50 → 19 |
| `cnd-f0557fa27a23` | 50 | 272 | 5.4 | 74 | 138 | 60 | 1.20 | 50 → 19 |
| `cnd-07aed88fb71c` | 50 | 197 | 3.9 | 18 | 114 | 65 | 1.30 | 46 → 25 |
| `cnd-3d586c4fde89` | 50 | 213 | 4.3 | 34 | 110 | 69 | 1.38 | 48 → 21 |
| `cnd-bfb5a480ae8d` | 50 | 191 | 3.8 | 24 | 97 | 70 | 1.40 | 47 → 23 |
| `cnd-19eb2c76d0bc` | 50 | 245 | 4.9 | 24 | 150 | 71 | 1.42 | 47 → 21 |
| `cnd-a21c94c74760` | 50 | 268 | 5.4 | 47 | 149 | 72 | 1.44 | 50 → 25 |
| `cnd-ee33aacb0354` | 50 | 265 | 5.3 | 60 | 132 | 73 | 1.46 | 50 → 21 |
| `cnd-111878302416` | 50 | 265 | 5.3 | 58 | 129 | 78 | 1.56 | 50 → 17 |
| `cnd-b164dc464120` | 50 | 335 | 6.7 | 74 | 182 | 79 | 1.58 | 50 → 24 |
| `cnd-2e1b533698d0` | 50 | 254 | 5.1 | 45 | 120 | 89 | 1.78 | 50 → 20 |

## Per failure mode

| mode | instances before | recovered | unrecovered | share recovered |
|---|---:|---:|---:|---:|
| `SP_06` Misclassification of Evidence Document Status | 782 | 521 | 261 | 67% |
| `SP_02` Reliance on Ungrounded External Knowledge | 583 | 553 | 30 | 95% |
| `SP_05` Unsound Deductive Reasoning from Context | 474 | 399 | 75 | 84% |
| `SP_08` Omission of Target Entities in Search Query | 278 | 132 | 146 | 47% |
| `SP_01` Misinterpretation of Claim Semantics | 252 | 204 | 48 | 81% |
| `SP_11` Invalid Search Query Generation | 216 | 120 | 96 | 56% |
| `SP_03` False Attribution of Claims to Input Passages | 187 | 175 | 12 | 94% |
| `SP_14` Required Page Not Retrieved by a Targeted Query | 132 | 13 | 119 | 10% |
| `SP_07` Failure to Carry Forward Verified Facts Across Turns | 94 | 54 | 40 | 57% |
| `SP_04` Premature Retrieval Loop Termination | 86 | 65 | 21 | 76% |
| `SP_13` Non-Compliance with Required Element Formatting Rules | 82 | 64 | 18 | 78% |
| `SP_09` Omission of Mandatory Output Completion Marker | 57 | 53 | 4 | 93% |
| `SP_10` Omission of Required Output Sections or Headers | 52 | 41 | 11 | 79% |
| `SP_15` Required Document Left Unidentified in Summary | 31 | 13 | 18 | 42% |
| `SP_12` Entity List Cardinality Constraint Violation | 29 | 24 | 5 | 83% |
| `(uncoded)`  | 7 | 6 | 1 | 86% |

An instance with several modes is counted once under each; `(uncoded)` = the judge kept the instance but no code fit it.
