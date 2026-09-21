# Models · HoVer (9 models, judged set b, 50 tasks) — recovery pass

Recovery reader: `anthropic/claude-sonnet-5` (thinking HIGH), success rule in view: **no**.
Judge mapping read: `runs/new_pipeline/hover-models/pointjudge-3`; taxonomy `sharing/Models_HoVer_taxonomy.json` (15 codes).
Traces with a recovery verdict: **450** (9 candidates × 50 tasks). One call per trace: the reader sees the whole trace and the judge's points, and gives each point one verdict.
- This recovery pass ran before the success rule was added to the reader's prompt; a hand audit of 100 of its recovered verdicts found ~15% wrong, all of one kind (a passage that mentions the required document was taken as the document).

## Verdicts over every point

| verdict | points | share | meaning |
|---|---:|---:|---|
| corrected | 126 | 8.1% | a later step fixed the wrong thing itself (the missing item was obtained, the wrong value replaced) |
| contained | 899 | 57.6% | the wrong thing stayed wrong but never reached what the output is scored on |
| made_irrelevant | 275 | 17.6% | a later step made the point moot (a different route obtained what was needed) |
| unrecovered | 260 | 16.7% | the point's effect is still in the final output |
| **recovered (corrected + contained + made_irrelevant)** | **1300** | **83.3%** | removed for the unrecovered-only scores |
| **left standing (unrecovered + unassessable)** | **260** | **16.7%** | what the unrecovered-only scores read |

## Per trace (one candidate on one task), before and after

| | before recovery | after (unrecovered only) |
|---|---:|---:|
| points per trace, mean | 3.47 | 0.58 |
| distinct failure modes per trace, mean | 2.70 | 0.50 |
| traces with at least one point | 441 of 450 (98%) | 133 of 450 (30%) |

## Per candidate

| candidate | traces | points before | per trace | corrected | contained | made irrelevant | unrecovered | unrec. per trace | traces flagged before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| anthropic/claude-haiku-4.5 (`cnd-b2ed881967c8`) | 50 | 115 | 2.3 | 10 | 76 | 14 | 15 | 0.30 | 45 → 7 |
| z-ai/glm-5.3-flash (`cnd-338900243876`) | 50 | 199 | 4.0 | 19 | 105 | 58 | 17 | 0.34 | 50 → 10 |
| xiaomi/mimo-v2.5 (`cnd-480646b48017`) | 50 | 190 | 3.8 | 16 | 111 | 45 | 18 | 0.36 | 49 → 10 |
| minimax/minimax-m3 (`cnd-04e667721381`) | 50 | 177 | 3.5 | 9 | 117 | 32 | 19 | 0.38 | 50 → 15 |
| openai/gpt-5.4-nano (`cnd-d26267ab539c`) | 50 | 148 | 3.0 | 6 | 97 | 16 | 29 | 0.58 | 50 → 15 |
| google/gemini-3.1-flash-lite (`cnd-7a11b9e6099c`) | 50 | 155 | 3.1 | 15 | 87 | 21 | 32 | 0.64 | 47 → 16 |
| bytedance-seed/seed-2.0-mini (`cnd-9ba9da54347f`) | 50 | 143 | 2.9 | 16 | 72 | 17 | 38 | 0.76 | 50 → 16 |
| mistralai/mistral-small-2603 (`cnd-e237f31850ed`) | 50 | 174 | 3.5 | 10 | 91 | 31 | 42 | 0.84 | 50 → 19 |
| deepseek/deepseek-v4-flash-0731 (`cnd-18c951be4aa6`) | 50 | 259 | 5.2 | 25 | 143 | 41 | 50 | 1.00 | 50 → 25 |

## Per failure mode

| mode | points before | recovered | unrecovered | share recovered |
|---|---:|---:|---:|---:|
| `SP_05` REDUNDANT_NEXT_HOP_QUERY_GENERATION | 395 | 293 | 102 | 74% |
| `SP_06` META_OR_EVALUATIVE_QUERY_GENERATION | 308 | 224 | 84 | 73% |
| `SP_01` UNGROUNDED_EXTERNAL_KNOWLEDGE_INCLUSION | 197 | 187 | 10 | 95% |
| `SP_04` OUTPUT_SCHEMA_DELIMITER_MISMATCH | 157 | 157 | 0 | 100% |
| `SP_02` MISREADING_OR_MISINTERPRETING_INPUT_MATERIAL | 143 | 133 | 10 | 93% |
| `SP_09` MISSING_OR_MALFORMED_OUTPUT_TERMINATION | 125 | 114 | 11 | 91% |
| `SP_13` UNCRITICAL_PROPAGATION_OF_PRIOR_CONTEXT | 88 | 78 | 10 | 89% |
| `SP_08` UNREQUESTED_CONTAINER_OR_WRAPPER_STRUCTURE | 81 | 81 | 0 | 100% |
| `SP_03` FUNCTIONAL_OUTPUT_TYPE_MISMATCH | 67 | 40 | 27 | 60% |
| `SP_15` CONCLUSION_UNLICENSED_BY_SUPPLIED_EVIDENCE | 55 | 47 | 8 | 85% |
| `SP_07` FLAWED_PREMISE_OR_MISCONSTRAINED_QUERY_GENERATION | 50 | 31 | 19 | 62% |
| `SP_14` IGNORING_OR_DISREGARDING_PRIOR_CONTEXT | 38 | 35 | 3 | 92% |
| `(uncoded)`  | 13 | 10 | 3 | 77% |
| `SP_12` PREMATURE_TASK_EXECUTION_HALTING | 9 | 4 | 5 | 44% |
| `SP_10` MALFORMED_SECTION_OR_FIELD_DELIMITER | 4 | 4 | 0 | 100% |
| `SP_11` OMISSION_OF_REQUIRED_OUTPUT_FIELD | 3 | 3 | 0 | 100% |

A point with several modes is counted once under each; `(uncoded)` = the judge kept the point but no code fit it.
