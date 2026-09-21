# GEPA candidates · HoVer (12 candidates, 50 judged tasks) — recovery pass

Recovery reader: `anthropic/claude-sonnet-5` (thinking HIGH), success rule in view: **yes**.
Judge mapping read: `runs/new_pipeline/hover/pointjudge-1`; taxonomy `sharing/GEPA_Candidates_HoVer_taxonomy.json` (15 codes).
Traces with a recovery verdict: **600** (12 candidates × 50 tasks). One call per trace: the reader sees the whole trace and the judge's points, and gives each point one verdict.
- The judge (tax-13, readers Luna, decider Sol) kept 170 points no code fit; SP_14 and SP_15 were assigned to them by hand afterwards. Recovery verdicts were given before that relabelling and carried over unchanged.

## Verdicts over every point

| verdict | points | share | meaning |
|---|---:|---:|---|
| corrected | 566 | 18.6% | a later step fixed the wrong thing itself (the missing item was obtained, the wrong value replaced) |
| contained | 1239 | 40.7% | the wrong thing stayed wrong but never reached what the output is scored on |
| made_irrelevant | 399 | 13.1% | a later step made the point moot (a different route obtained what was needed) |
| unrecovered | 839 | 27.6% | the point's effect is still in the final output |
| **recovered (corrected + contained + made_irrelevant)** | **2204** | **72.4%** | removed for the unrecovered-only scores |
| **left standing (unrecovered + unassessable)** | **839** | **27.6%** | what the unrecovered-only scores read |

## Per trace (one candidate on one task), before and after

| | before recovery | after (unrecovered only) |
|---|---:|---:|
| points per trace, mean | 5.07 | 1.40 |
| distinct failure modes per trace, mean | 3.39 | 1.01 |
| traces with at least one point | 587 of 600 (98%) | 256 of 600 (43%) |

## Per candidate

| candidate | traces | points before | per trace | corrected | contained | made irrelevant | unrecovered | unrec. per trace | traces flagged before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `cnd-d680fd9955b0` | 50 | 274 | 5.5 | 42 | 137 | 39 | 56 | 1.12 | 49 → 21 |
| `cnd-9de4bb39803c` | 50 | 264 | 5.3 | 66 | 118 | 23 | 57 | 1.14 | 50 → 19 |
| `cnd-f0557fa27a23` | 50 | 272 | 5.4 | 74 | 111 | 27 | 60 | 1.20 | 50 → 19 |
| `cnd-07aed88fb71c` | 50 | 197 | 3.9 | 18 | 75 | 39 | 65 | 1.30 | 46 → 25 |
| `cnd-3d586c4fde89` | 50 | 213 | 4.3 | 34 | 85 | 25 | 69 | 1.38 | 48 → 21 |
| `cnd-bfb5a480ae8d` | 50 | 191 | 3.8 | 24 | 70 | 27 | 70 | 1.40 | 47 → 23 |
| `cnd-19eb2c76d0bc` | 50 | 245 | 4.9 | 24 | 104 | 46 | 71 | 1.42 | 47 → 21 |
| `cnd-a21c94c74760` | 50 | 268 | 5.4 | 47 | 108 | 41 | 72 | 1.44 | 50 → 25 |
| `cnd-ee33aacb0354` | 50 | 265 | 5.3 | 60 | 101 | 31 | 73 | 1.46 | 50 → 21 |
| `cnd-111878302416` | 50 | 265 | 5.3 | 58 | 108 | 21 | 78 | 1.56 | 50 → 17 |
| `cnd-b164dc464120` | 50 | 335 | 6.7 | 74 | 117 | 65 | 79 | 1.58 | 50 → 24 |
| `cnd-2e1b533698d0` | 50 | 254 | 5.1 | 45 | 105 | 15 | 89 | 1.78 | 50 → 20 |

## Per failure mode

| mode | points before | recovered | unrecovered | share recovered |
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

A point with several modes is counted once under each; `(uncoded)` = the judge kept the point but no code fit it.
