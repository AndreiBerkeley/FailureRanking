# Models · LiveCodeBench (9 models, 150 judged tasks) — recovery pass

Recovery reader: `claude-sonnet-5` (thinking HIGH), success rule in view: **yes**.
Judge mapping read: `runs/new_pipeline/lcb-models/pointjudge-2`; taxonomy `sharing/Models_LiveCodeBench_taxonomy.json` (10 codes).
Traces with a recovery verdict: **1350** (9 candidates × 150 tasks). One call per trace: the reader sees the whole trace and the judge's failure instances, and gives each instance one verdict.
- Single-turn programs: the solver writes its answer in one reply, so no later step can correct an instance; one is recovered only if the graded program (the first python block) does not carry it.

## Verdicts over every failure instance

| verdict | instances | share | meaning |
|---|---:|---:|---|
| contained | 6 | 1.0% | the output does not carry it and nothing corrected it: nothing downstream used it, or it was used and the output was fine regardless, or another path supplied what was needed |
| unrecovered | 621 | 99.0% | the effect is in the final output, or what the instance cost is missing from it, or the trace cannot show otherwise |
| **recovered (corrected + contained)** | **6** | **1.0%** | removed for the unrecovered-only scores |
| **left standing (unrecovered)** | **621** | **99.0%** | what the unrecovered-only scores read |

## Per trace (one candidate on one task), before and after

| | before recovery | after (unrecovered only) |
|---|---:|---:|
| failure instances per trace, mean | 0.46 | 0.46 |
| distinct failure modes per trace, mean | 0.42 | 0.42 |
| traces with at least one instance | 461 of 1350 (34%) | 459 of 1350 (34%) |

## Per candidate

| candidate | traces | instances before | per trace | corrected | contained | unrecovered | unrec. per trace | traces flagged before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| z-ai/glm-5.3-flash (`cnd-81f7ad42572c`) | 150 | 44 | 0.3 | 0 | 1 | 43 | 0.29 | 38 → 37 |
| google/gemini-3.1-flash-lite (`cnd-00a8e432b474`) | 150 | 50 | 0.3 | 0 | 0 | 50 | 0.33 | 37 → 37 |
| deepseek/deepseek-v4-flash-0731 (`cnd-a576afe10efc`) | 150 | 55 | 0.4 | 0 | 0 | 55 | 0.37 | 42 → 42 |
| minimax/minimax-m3 (`cnd-826d15a02fb0`) | 150 | 59 | 0.4 | 0 | 1 | 58 | 0.39 | 49 → 49 |
| xiaomi/mimo-v2.5 (`cnd-c474168eea25`) | 150 | 59 | 0.4 | 0 | 0 | 59 | 0.39 | 45 → 45 |
| openai/gpt-5.4-nano (`cnd-2c2afebac4dc`) | 150 | 74 | 0.5 | 0 | 0 | 74 | 0.49 | 55 → 55 |
| bytedance-seed/seed-2.0-mini (`cnd-8969db10860c`) | 150 | 85 | 0.6 | 0 | 1 | 84 | 0.56 | 53 → 53 |
| anthropic/claude-haiku-4.5 (`cnd-3d85a2d04024`) | 150 | 87 | 0.6 | 0 | 2 | 85 | 0.57 | 66 → 65 |
| mistralai/mistral-small-2603 (`cnd-cc1b32d219bc`) | 150 | 114 | 0.8 | 0 | 1 | 113 | 0.75 | 76 → 76 |

## Per failure mode

| mode | instances before | recovered | unrecovered | share recovered |
|---|---:|---:|---:|---:|
| `SP_08` unsound_algorithmic_strategy_or_structural_premise | 122 | 0 | 122 | 0% |
| `SP_02` complexity_bound_exceeded | 106 | 0 | 106 | 0% |
| `SP_01` incomplete_or_malformed_output_generation | 95 | 2 | 93 | 2% |
| `SP_09` implementation_defect_in_a_sound_algorithm | 90 | 0 | 90 | 0% |
| `SP_07` incomplete_or_overly_restrictive_logic_condition | 82 | 1 | 81 | 1% |
| `SP_04` flawed_mathematical_or_combinatorial_derivation | 61 | 2 | 59 | 3% |
| `SP_03` invalid_dynamic_programming_state_or_transition | 42 | 0 | 42 | 0% |
| `SP_06` off_by_one_and_boundary_shift_error | 25 | 0 | 25 | 0% |
| `SP_10` contradicting_check_dismissed | 9 | 0 | 9 | 0% |
| `SP_05` simulation_mechanics_and_traversal_state_tracking_defect | 3 | 0 | 3 | 0% |
| `(uncoded)`  | 3 | 1 | 2 | 33% |

An instance with several modes is counted once under each; `(uncoded)` = the judge kept the instance but no code fit it.
