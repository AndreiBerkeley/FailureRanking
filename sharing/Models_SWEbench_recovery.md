# Models · SWE-bench Verified (12 models, 50 judged tasks) — recovery pass

Recovery reader: `gemini-3.8-flash` (thinking HIGH), success rule in view: **yes**.
Judge mapping read: `../../swebench/mappings/map-1/run`; taxonomy `data/swebench/taxonomies/tax-1/taxonomy.json` (29 codes).
Traces with a recovery verdict: **600** (12 candidates × 50 tasks). One call per trace: the reader sees the whole trace and the judge's failure instances, and gives each instance one verdict.
- Judge: RedoAdamast one-pass judge, gemini-3.8-flash, taxonomy fixed (29 codes). Recovery reader: gemini-3.8-flash via Arena, thinking HIGH; one trace (5cd520e18dab3d276a7507b4) whose answer ran past the output limit twice was read again with thinking MEDIUM (runs/new_pipeline/swebench/recovery-fill-1).
- The run's output is the submitted patch, which follows the last turn; the reader's quotes about the output were re-checked against it (code/recheck_recovery_output.py): unverifiable claims fell from 5,060 to 1,698, no verdict changed.

## Verdicts over every failure instance

| verdict | instances | share | meaning |
|---|---:|---:|---|
| corrected | 1754 | 24.4% | a later step replaced the wrong thing and the output does not carry it |
| contained | 3924 | 54.5% | the output does not carry it and nothing corrected it: nothing downstream used it, or it was used and the output was fine regardless, or another path supplied what was needed |
| unrecovered | 1524 | 21.2% | the effect is in the final output, or what the instance cost is missing from it, or the trace cannot show otherwise |
| **recovered (corrected + contained)** | **5678** | **78.8%** | removed for the unrecovered-only scores |
| **left standing (unrecovered)** | **1524** | **21.2%** | what the unrecovered-only scores read |

## Per trace (one candidate on one task), before and after

| | before recovery | after (unrecovered only) |
|---|---:|---:|
| failure instances per trace, mean | 12.00 | 2.54 |
| distinct failure modes per trace, mean | 4.24 | 0.42 |
| traces with at least one instance | 598 of 600 (100%) | 125 of 600 (21%) |

## Per candidate

| candidate | traces | instances before | per trace | corrected | contained | unrecovered | unrec. per trace | traces flagged before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `swe-gemini-3-flash-high` | 50 | 278 | 5.6 | 157 | 118 | 3 | 0.06 | 50 → 3 |
| `swe-claude-4-5-opus-high` | 50 | 176 | 3.5 | 112 | 59 | 5 | 0.10 | 49 → 1 |
| `swe-glm-5-high` | 50 | 615 | 12.3 | 206 | 396 | 13 | 0.26 | 50 → 7 |
| `swe-deepseek-3-2-high` | 50 | 426 | 8.5 | 184 | 219 | 23 | 0.46 | 50 → 13 |
| `swe-gemini-3-pro-high` | 50 | 238 | 4.8 | 139 | 73 | 26 | 0.52 | 49 → 10 |
| `swe-claude-4-5-sonnet-high` | 50 | 252 | 5.0 | 128 | 94 | 30 | 0.60 | 50 → 13 |
| `swe-claude-4-5-haiku-high` | 50 | 337 | 6.7 | 196 | 108 | 33 | 0.66 | 50 → 14 |
| `swe-gpt-5-2-high` | 50 | 755 | 15.1 | 109 | 523 | 123 | 2.46 | 50 → 9 |
| `swe-claude-4-6-opus` | 50 | 904 | 18.1 | 95 | 651 | 158 | 3.16 | 50 → 7 |
| `swe-kimi-k2-5-high` | 50 | 1019 | 20.4 | 168 | 559 | 292 | 5.84 | 50 → 11 |
| `swe-minimax-2-5-high` | 50 | 1146 | 22.9 | 161 | 687 | 298 | 5.96 | 50 → 11 |
| `swe-gpt-5-mini` | 50 | 1056 | 21.1 | 99 | 437 | 520 | 10.40 | 50 → 26 |

## Per failure mode

| mode | instances before | recovered | unrecovered | share recovered |
|---|---:|---:|---:|---:|
| `FM-01` omitted required reasoning or plan | 3751 | 2509 | 1242 | 67% |
| `FM-12` flawed verification script or test harness | 492 | 481 | 11 | 98% |
| `FM-07` incorrect environment configuration or python runtime invocation | 437 | 432 | 5 | 99% |
| `FM-10` flawed file modification execution | 371 | 368 | 3 | 99% |
| `FM-06` violating submission command format or protocol | 357 | 355 | 2 | 99% |
| `FM-13` excessive output generation | 192 | 186 | 6 | 97% |
| `FM-22` leaving stray backup or scratch files in repository tree | 175 | 171 | 4 | 98% |
| `FM-09` modifying unrelated source files | 174 | 127 | 47 | 73% |
| `FM-29` malformed shell command syntax or flawed operator logic | 166 | 166 | 0 | 100% |
| `FM-15` incorrect logic or flawed fix implementation | 154 | 75 | 79 | 49% |
| `FM-03` targeting non-existent test target or file | 142 | 140 | 2 | 99% |
| `FM-05` invoking non-existent environment command or tool | 139 | 138 | 1 | 99% |
| `FM-02` referencing non-existent symbol or import | 128 | 128 | 0 | 100% |
| `FM-19` incorrect command argument or test invocation syntax | 107 | 90 | 17 | 84% |
| `FM-30` omitting mandatory tool call or malformed tool call structure | 97 | 66 | 31 | 68% |
| `FM-08` modifying test files contrary to constraints | 73 | 69 | 4 | 95% |
| `FM-11` skipping or abandoning verification and regression testing | 51 | 30 | 21 | 59% |
| `FM-14` improper git staging or commit action | 51 | 48 | 3 | 94% |
| `FM-26` modifying unrelated functionality within target file | 27 | 3 | 24 | 11% |
| `FM-27` unproductive retry loop | 24 | 23 | 1 | 96% |
| `FM-17` ineffective search or command filter | 23 | 23 | 0 | 100% |
| `FM-16` ignoring or misinterpreting execution failure | 22 | 8 | 14 | 36% |
| `FM-25` destructive working tree reset or progress deletion | 12 | 11 | 1 | 92% |
| `FM-21` overly broad or unconstrained search query | 10 | 8 | 2 | 80% |
| `FM-18` issuing non-functional or no-op command | 10 | 10 | 0 | 100% |
| `(uncoded)`  | 7 | 6 | 1 | 86% |
| `FM-28` modifying configuration or build files contrary to constraints | 4 | 4 | 0 | 100% |
| `FM-20` misreading problem description or code behavior | 3 | 2 | 1 | 67% |
| `FM-24` submitting malformed, unpopulated, or non-diff patch | 2 | 0 | 2 | 0% |
| `FM-23` unrestored working tree state or abandoned stash | 1 | 1 | 0 | 100% |

An instance with several modes is counted once under each; `(uncoded)` = the judge kept the instance but no code fit it.
