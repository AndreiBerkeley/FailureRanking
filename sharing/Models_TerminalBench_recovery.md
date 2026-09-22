# Models · Terminal-Bench 2.0 (7 models, 20 judged tasks) — recovery pass

Recovery reader: `anthropic/claude-sonnet-5` (thinking HIGH), success rule in view: **yes**.
Judge mapping read: `runs/new_pipeline/terminalbench/pointjudge-1`; taxonomy `sharing/Models_TerminalBench_taxonomy.json` (10 codes).
Traces with a recovery verdict: **138** (7 candidates × 20 tasks; 2 traces could not be judged). One call per trace: the reader sees the whole trace and the judge's failure instances, and gives each instance one verdict.
- Two traces (Kimi-k2.5 and GPT-5.3-Codex on task vulnerable-secret) could not be judged: the decider's provider refused the content as a possible cybersecurity risk. That task is dropped for every candidate in the scores.

## Verdicts over every failure instance

| verdict | instances | share | meaning |
|---|---:|---:|---|
| corrected | 378 | 34.1% | a later step replaced the wrong thing and the output does not carry it |
| contained | 264 | 23.8% | the output does not carry it and nothing corrected it: nothing downstream used it, or it was used and the output was fine regardless, or another path supplied what was needed |
| unrecovered | 466 | 42.1% | the effect is in the final output, or what the instance cost is missing from it, or the trace cannot show otherwise |
| **recovered (corrected + contained)** | **642** | **57.9%** | removed for the unrecovered-only scores |
| **left standing (unrecovered)** | **466** | **42.1%** | what the unrecovered-only scores read |

## Per trace (one candidate on one task), before and after

| | before recovery | after (unrecovered only) |
|---|---:|---:|
| failure instances per trace, mean | 8.03 | 3.38 |
| distinct failure modes per trace, mean | 2.58 | 1.20 |
| traces with at least one instance | 128 of 138 (93%) | 81 of 138 (59%) |

## Per candidate

| candidate | traces | instances before | per trace | corrected | contained | unrecovered | unrec. per trace | traces flagged before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| GPT-5.3-Codex (`tb2-gpt-5.3-codex`) | 19 | 75 | 3.9 | 34 | 16 | 25 | 1.32 | 14 → 8 |
| Claude-Opus-4.6 (`tb2-claude-opus-4.6`) | 20 | 97 | 4.8 | 37 | 33 | 27 | 1.35 | 18 → 8 |
| GLM-5 (`tb2-glm-5`) | 20 | 157 | 7.8 | 59 | 39 | 59 | 2.95 | 18 → 10 |
| DeepSeek-V3.2 (`tb2-deepseek-v3.2`) | 20 | 175 | 8.8 | 61 | 33 | 81 | 4.05 | 20 → 15 |
| Kimi-k2.5 (`tb2-kimi-k2.5`) | 19 | 179 | 9.4 | 54 | 41 | 84 | 4.42 | 19 → 13 |
| Minimax-m2.5 (`tb2-minimax-m2.5`) | 20 | 195 | 9.8 | 50 | 52 | 93 | 4.65 | 20 → 13 |
| GLM-4.7 (`tb2-glm-4.7`) | 20 | 230 | 11.5 | 83 | 50 | 97 | 4.85 | 19 → 14 |

## Per failure mode

| mode | instances before | recovered | unrecovered | share recovered |
|---|---:|---:|---:|---:|
| `SP_09` incorrect_environment_or_process_state_inference | 344 | 201 | 143 | 58% |
| `(uncoded)`  | 237 | 115 | 122 | 49% |
| `SP_07` incorrect_domain_rules_and_constraints | 206 | 74 | 132 | 36% |
| `SP_05` incorrect_api_parameter_or_interface_usage | 100 | 81 | 19 | 81% |
| `SP_06` flawed_numerical_and_mathematical_algorithms | 83 | 51 | 32 | 61% |
| `SP_02` missing_required_schema_field | 46 | 46 | 0 | 100% |
| `SP_03` malformed_output_syntax_or_formatting | 46 | 37 | 9 | 80% |
| `SP_08` framework_and_compiler_execution_logic_errors | 33 | 20 | 13 | 61% |
| `SP_01` output_placed_in_reasoning_block | 20 | 10 | 10 | 50% |
| `SP_04` invalid_command_formatting_or_syntax | 15 | 13 | 2 | 87% |
| `SP_10` missing_required_header_or_import_declaration | 2 | 1 | 1 | 50% |

An instance with several modes is counted once under each; `(uncoded)` = the judge kept the instance but no code fit it.
