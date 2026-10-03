# Models · HoVer (9 models, judged set b, 50 tasks) — recovery pass

Recovery reader: `claude-sonnet-5` (thinking HIGH), success rule in view: **yes**.
Judge mapping read: `runs/new_pipeline/hover-models/pointjudge-3`; taxonomy `sharing/Models_HoVer_taxonomy.json` (15 codes).
Traces with a recovery verdict: **450** (9 candidates × 50 tasks). One call per trace: the reader sees the whole trace and the judge's failure instances, and gives each instance one verdict.
- recovery-2: the same judge instances as before (pointjudge-3, which ran without the success rule), re-read with the success rule in view, through Arena. It supersedes recovery-1 (no success rule; 83% of instances recovered, 102 of 215 failed tasks fully excused, against 74% and 46 here).

## Verdicts over every failure instance

| verdict | instances | share | meaning |
|---|---:|---:|---|
| corrected | 113 | 7.2% | a later step replaced the wrong thing and the output does not carry it |
| contained | 1045 | 67.0% | the output does not carry it and nothing corrected it: nothing downstream used it, or it was used and the output was fine regardless, or another path supplied what was needed |
| unrecovered | 402 | 25.8% | the effect is in the final output, or what the instance cost is missing from it, or the trace cannot show otherwise |
| **recovered (corrected + contained)** | **1158** | **74.2%** | removed for the unrecovered-only scores |
| **left standing (unrecovered)** | **402** | **25.8%** | what the unrecovered-only scores read |

## Per trace (one candidate on one task), before and after

| | before recovery | after (unrecovered only) |
|---|---:|---:|
| failure instances per trace, mean | 3.47 | 0.89 |
| distinct failure modes per trace, mean | 2.70 | 0.76 |
| traces with at least one instance | 441 of 450 (98%) | 174 of 450 (39%) |

## Per candidate

| candidate | traces | instances before | per trace | corrected | contained | unrecovered | unrec. per trace | traces flagged before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| anthropic/claude-haiku-4.5 (`cnd-b2ed881967c8`) | 50 | 115 | 2.3 | 10 | 83 | 22 | 0.44 | 45 → 11 |
| z-ai/glm-5.3-flash (`cnd-338900243876`) | 50 | 199 | 4.0 | 23 | 141 | 35 | 0.70 | 50 → 13 |
| minimax/minimax-m3 (`cnd-04e667721381`) | 50 | 177 | 3.5 | 12 | 129 | 36 | 0.72 | 50 → 22 |
| openai/gpt-5.4-nano (`cnd-d26267ab539c`) | 50 | 148 | 3.0 | 7 | 103 | 38 | 0.76 | 50 → 18 |
| xiaomi/mimo-v2.5 (`cnd-480646b48017`) | 50 | 190 | 3.8 | 13 | 133 | 44 | 0.88 | 49 → 21 |
| google/gemini-3.1-flash-lite (`cnd-7a11b9e6099c`) | 50 | 155 | 3.1 | 11 | 95 | 49 | 0.98 | 47 → 20 |
| bytedance-seed/seed-2.0-mini (`cnd-9ba9da54347f`) | 50 | 143 | 2.9 | 11 | 79 | 53 | 1.06 | 50 → 23 |
| mistralai/mistral-small-2603 (`cnd-e237f31850ed`) | 50 | 174 | 3.5 | 9 | 108 | 57 | 1.14 | 50 → 22 |
| deepseek/deepseek-v4-flash-0731 (`cnd-18c951be4aa6`) | 50 | 259 | 5.2 | 17 | 174 | 68 | 1.36 | 50 → 24 |

## Per failure mode

| mode | instances before | recovered | unrecovered | share recovered |
|---|---:|---:|---:|---:|
| `SP_05` REDUNDANT_NEXT_HOP_QUERY_GENERATION | 395 | 261 | 134 | 66% |
| `SP_06` META_OR_EVALUATIVE_QUERY_GENERATION | 308 | 177 | 131 | 57% |
| `SP_01` UNGROUNDED_EXTERNAL_KNOWLEDGE_INCLUSION | 197 | 176 | 21 | 89% |
| `SP_04` OUTPUT_SCHEMA_DELIMITER_MISMATCH | 157 | 154 | 3 | 98% |
| `SP_02` MISREADING_OR_MISINTERPRETING_INPUT_MATERIAL | 143 | 107 | 36 | 75% |
| `SP_09` MISSING_OR_MALFORMED_OUTPUT_TERMINATION | 125 | 124 | 1 | 99% |
| `SP_13` UNCRITICAL_PROPAGATION_OF_PRIOR_CONTEXT | 88 | 56 | 32 | 64% |
| `SP_08` UNREQUESTED_CONTAINER_OR_WRAPPER_STRUCTURE | 81 | 79 | 2 | 98% |
| `SP_03` FUNCTIONAL_OUTPUT_TYPE_MISMATCH | 67 | 36 | 31 | 54% |
| `SP_15` CONCLUSION_UNLICENSED_BY_SUPPLIED_EVIDENCE | 55 | 43 | 12 | 78% |
| `SP_07` FLAWED_PREMISE_OR_MISCONSTRAINED_QUERY_GENERATION | 50 | 27 | 23 | 54% |
| `SP_14` IGNORING_OR_DISREGARDING_PRIOR_CONTEXT | 38 | 33 | 5 | 87% |
| `(uncoded)`  | 13 | 8 | 5 | 62% |
| `SP_12` PREMATURE_TASK_EXECUTION_HALTING | 9 | 5 | 4 | 56% |
| `SP_10` MALFORMED_SECTION_OR_FIELD_DELIMITER | 4 | 3 | 1 | 75% |
| `SP_11` OMISSION_OF_REQUIRED_OUTPUT_FIELD | 3 | 2 | 1 | 67% |

An instance with several modes is counted once under each; `(uncoded)` = the judge kept the instance but no code fit it.
