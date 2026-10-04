# Runs (local only)

## SWE-bench, swe-gpt-5-mini

| setting | value |
|---|---|
| data | SWE-bench Verified, model `swe-gpt-5-mini` |
| T | 500 traces, 500 tasks |
| p, N | 5%, 25 traces, seed 0 |
| split of N | 20 initial generation, 5 segment 1, 25 segment 2 |
| other variables | defaults |
| dry run | at most 143 calls, about 3.8M input tokens |

```bash
python3 generation/prepare_data.py --benchmark swebench --model swe-gpt-5-mini --fraction 0.05 --seed 0
python3 generation/run.py --data data/swebench/swe-gpt-5-mini --out runs/<name> --dry-run
python3 generation/run.py --data data/swebench/swe-gpt-5-mini --model arena/gemini-3.8-flash --out runs/<name>
```

## Single model, 3 benchmarks

Tasks drawn at random (seed 0) from `data/<benchmark>/traces/`; one model drawn once, its trace of every task.
The same tasks are used by `multi-model/`.

| setting | SWE-bench | τ²-bench | BFCL |
|---|---|---|---|
| model | `swe-minimax-2-5-high` | `tau2-claude-opus-4-8` (one random run of 4) | `bfcl-grok-4-0709-FC` |
| task pool | 485 tasks | 87 tasks | 200 scenarios, one variant each |
| tasks: initial / seg 1 / final | 20 / 5 / 5 | 10 / 5 / 5 | 20 / 5 / 5 |
| N (sample), F·M (validation) | 25, 5 | 15, 5 | 25, 5 |
| other variables | M = 5, context 532,768 tokens, max output 65,536 | same | same |
| dry run, incl. final validation | ≤ 229 calls, ~9.0M input tokens | ≤ 209 calls, ~6.3M | ≤ 229 calls, ~3.6M |
| run dir | `runs/swebench-single` | `runs/tau2bench-single` | `runs/bfcl-single` |

```bash
python3 generation/select_tasks.py --benchmark swebench --initial 20    # tau2bench: --initial 10; bfcl: --initial 20
python3 generation/run.py --data data/<benchmark>/single-model --traces-per-round 5 --context-tokens 532768 --max-output 65536 --model arena/gemini-3.8-flash --out runs/<benchmark>-single
```

Context and max output are raised by the same amount, so the prompt budget stays 1,401,696 characters (the size at which
SWE-bench field analysis goes through, in 3 calls; at 1M context its single 2.7M-character call timed out 3 times).
At the default max output of 32,768 tokens, abstraction replies were cut off 3 times (thinking counts against it).

| result | SWE-bench | τ²-bench | BFCL |
|---|---|---|---|
| calls, input tokens (est.) | 161, 6.2M | 133, 4.0M | 160, 2.3M |
| modes: final (with evidence) | 22 (17) | 15 (11) | 23 (16) |
| segment 1: failures, κ, coverage | 29, 1.00, 0.93 | 70, 1.00, 0.96 | 12, 1.00, 0.83 |
| final validation: failures, κ, coverage | 25, 1.00, 0.80 | 79, 1.00, 0.94 | 12, 1.00, 0.83 |

τ²: 285 of the 325 instances in the final taxonomy are one mode, "simultaneous message and tool execution in single turn".
287 of the 482 agent turns in these traces have both: the τ² view labels any text in a turn as "message to the customer",
also when the turn makes tool calls, and the next input of such a turn is tool results only.

## Multi model, 3 benchmarks

Same tasks as `single-model/`; per task L = 3 models drawn at random (`data/<benchmark>/multi-model/manifest.json`
lists the model of every trace). M = 15 traces per round, i.e. 5 tasks x 3 models; other settings as above.

```bash
python3 generation/run.py --data data/<benchmark>/multi-model --traces-per-round 15 --context-tokens 532768 --max-output 65536 --model arena/gemini-3.8-flash --out runs/<benchmark>-multi
```

| result | SWE-bench | τ²-bench | BFCL |
|---|---|---|---|
| calls, input tokens (est.) | 476, 19.5M | 393, 15.9M | 429, 6.8M |
| modes: final (with evidence) | 29 (25) | 28 (22) | 35 (32) |
| segment 1: failures, κ, coverage | 69, 0.98, 0.97 | 128, 0.99, 0.87 | 21, 0.93, 0.86 |
| final validation: failures, κ, coverage | 63, 1.00, 0.94 | 159, 1.00, 0.99 | 25, 1.00, 0.76 |
| billed cost | not recorded | not recorded | not recorded |

Billed cost is recorded from 2026-09-27 22:10 on (the test runs below and every later run): each reply's cost as Arena
reports it, summed in `call_report.txt`, `cost.json` (generation) and `summary.json` → `cost` (judge). Requests that got
no reply are counted separately; any charge for them is unknown and not included. Earlier runs have no billed cost.

Abstraction version: the three single-model runs and `bfcl-multi` ran before 2026-09-27, when abstraction
still copied every instance into its reply; `swebench-multi` and `tau2bench-multi` use the ids-only abstraction
(the reply names instances by id). Left as is by choice. `call_report.py` shows each run's failed calls.

## Test: single-model taxonomies on the tasks generation did not use

The judge applies each benchmark's final single-model taxonomy, fixed (an instance no mode fits is NONE), to the
same model's trace of every task generation did not use: `data/<benchmark>/single-model/test/` (one run per task;
bfcl: every other scenario, one variant each, none of the 30 generation scenarios). The judge sees the failure
definition (00_concepts.md, 00_mode_rules.md) and the taxonomy.

| | SWE-bench | τ²-bench | BFCL |
|---|---|---|---|
| test traces | 455 | 67 | 170 |
| dry run | 455 calls, ~16.8M input tokens | 67, ~2.0M | 170, ~2.8M |
| run dir | `runs/swebench-single-test` | `runs/tau2bench-single-test` | `runs/bfcl-single-test` |
| failures found (per trace) | 4,052 (8.9) | 919 (13.7) | 589 (3.5) |
| fit a mode | 99.8% (8 NONE) | 100% (0 NONE) | 99.8% (1 NONE) |
| modes used | 21 of 22 | 10 of 15 | 17 of 23 |
| largest mode | FM-14 omitted reasoning before a tool call, 48% | FM-01 message and tool call in one turn, 94% | FM-01 Emitting simulated user turns instead of assistant response, 20% |
| billed; requests without reply | $43.68; 10 | $3.60; 0 | $8.88; 0 |

```bash
python3 generation/export_test.py --benchmark <benchmark>
python3 generation/judge.py --taxonomy runs/<benchmark>-single/final_taxonomy.json --traces data/<benchmark>/single-model/test --no-new-modes --context-tokens 532768 --max-output 65536 --workers 16 --model arena/gemini-3.8-flash --out runs/<benchmark>-single-test
```

## Test, two passes: find without the taxonomy, then verify and assign

Same test traces. Per trace: (1) find every failure with the failure definition and the run's field analysis, no
taxonomy (the observation prompt of generation); (2) with the taxonomy, decide for each candidate whether it is a
failure and give it a mode or NONE (`judge_verify.md`). Coverage = confirmed failures with a mode / confirmed failures.
Failures the second call sees that no candidate describes are stored apart (`missed_by_find`, with their modes) and
left out of found / confirmed / coverage.

| | SWE-bench | τ²-bench | BFCL |
|---|---|---|---|
| dry run (verify sized at 10 candidates) | 910 calls, ~32.9M input tokens | 134, ~3.9M | 340, ~5.1M |
| run dir | `runs/swebench-single-test-blind` | `runs/tau2bench-single-test-blind` | `runs/bfcl-single-test-blind` |
| found; confirmed; rejected | 1,687; 1,514; 173 | 950; 938; 12 | 456; 427; 29 |
| coverage (NONE) | 96.6% (51) | 98.5% (14) | 95.8% (18) |
| coverage without the largest mode | 96.1% (1,248 of 1,299) | 80.6% (58 of 72) | 94.1% (291 of 309) |
| found only by the second call | 574 (all with a mode; 224 FM-14, 211 FM-02) | 4 (all with a mode) | 77 (all with a mode; 50 FM-12) |
| billed; requests without reply | $61.37; 26 | $6.53; 0 | $10.49; 0 |

```bash
python3 generation/judge_blind.py --run runs/<benchmark>-single --traces data/<benchmark>/single-model/test --context-tokens 532768 --max-output 65536 --workers 6 --model arena/gemini-3.8-flash --out runs/<benchmark>-single-test-blind
```

## HoVer seed program, 100 traces

`data/hover/`: the 750 traces of the unoptimised HoVer seed program (solver openai/gpt-5.6-luna), copied from
`NewGEPAChanges/results/seed_traces` (kept there) into `raw/` and converted by `data/hover/convert.py` (score, gold and
the evaluator's feedback go to `outcomes.jsonl`, never into a trace). 100 tasks drawn at random from all 750 (seed 0):
90 initial generation, 5 segment 1, 5 final validation.

| setting | value |
|---|---|
| N (sample), F·M (validation) | 95, 5 |
| other variables | M = 5, context 532,768 tokens, max output 65,536 |
| dry run | ≤ 370 calls, ~4.9M input tokens |
| run dir | `runs/hover-single` (log `runs/hover-single.log`) |
| calls; billed | 304; $9.52 (no failed attempts, every request got a reply) |
| modes: final (with evidence) | 27 (15): 11 from generation, 4 added by the gap test with an instance, 12 possible |
| segment 1: failures, κ, coverage | 18, 1.00, 0.94 |
| final validation: failures, κ, coverage | 13, 1.00, 1.00 (no refinement needed) |

```bash
python3 data/hover/convert.py
python3 generation/select_tasks.py --benchmark hover --initial 90 --seg1 5 --final 5
python3 generation/run.py --data data/hover/single-model --traces-per-round 5 --context-tokens 532768 --max-output 65536 --model arena/gemini-3.8-flash --out runs/hover-single
```

## HotpotQA and IFBench seed programs, 100 test-split traces each

`data/hotpotqa/`, `data/ifbench/`: the 750 traces (train 150, val 300, test 300) of each unoptimised seed program
(solver openai/gpt-5.6-luna), copied from `NewGEPAChanges/results/seed_traces/<benchmark>` (kept there) into `raw/` and
converted by `data/<benchmark>/convert.py` (scores, gold, grading and the verifier's instruction ids go to
`outcomes.jsonl`, never into a trace). 100 tasks drawn at random from the **test split only** (seed 0): 90 initial
generation, 5 segment 1, 5 final validation. Settings as for HoVer; per-request timeout 10 min.

| | HotpotQA | IFBench |
|---|---|---|
| program | retrieve → summarize1 → create_query_hop2 → retrieve → summarize2 → final_answer | generate_response → ensure_correct_response |
| test-split score (sample of 100) | answer F1 0.562 (0.520) | instruction-level strict 0.55 (0.525) |
| dry run | ≤ 370 calls, ~4.5M input tokens | ≤ 369 calls, ~3.3M |
| run dir | `runs/hotpotqa-single` | `runs/ifbench-single` |
| calls; billed | 276; $6.72 (no failed attempts, every request got a reply) | 272; $5.69 (0 requests without reply) |
| modes: final (with evidence) | 24 (9): 8 from generation, 1 added by the gap test with an instance, 15 possible | 14 (13), 1 possible |
| segment 1: failures, κ, coverage | 6, 1.00, 1.00 (no refinement needed) | 8, 1.00, 1.00 |
| final validation: failures, κ, coverage | 5, 1.00, 1.00 (no refinement needed) | 3, 1.00, 1.00 |
| two-pass test (650 unused traces, full taxonomy): found; confirmed; coverage (NONE) | 989; 971; 99.9% (1); 7 of 15 possible modes got failures (1–4 each); 236 found only by the second call, incl. 84 full-sentence answers (FM-09); $23.81 | 1,064; 976; 99.4% (6; 4 are the checker flagging compliant text as violating); all 14 modes got failures; 88 found only by the second call (84 FM-01 leaked scaffolding); 1 trace failed (pass 1 unparseable 3 times); $23.25 |

```bash
python3 data/<benchmark>/convert.py
python3 generation/select_tasks.py --benchmark <benchmark> --initial 90 --seg1 5 --final 5 --split test
python3 generation/run.py --data data/<benchmark>/single-model --traces-per-round 5 --context-tokens 532768 --max-output 65536 --model arena/gemini-3.8-flash --out runs/<benchmark>-single
```

## HoVer tests (full taxonomy)

The full 27-mode taxonomy (`runs/hover-single/final_taxonomy.json`, 12 of them possible) on the seed program's trace of
each of the 650 tasks generation did not use (`data/hover/single-model/test/`). These replace a first pair of tests
with the 15-mode evidence-only taxonomy (moved to the Trash: one-pass 100% fit, $28.79; two-pass 99.7%, 3 NONE, $31.82).

| | one-pass (`judge.py --no-new-modes`) | two-pass (`judge_blind.py`) |
|---|---|---|
| run dir | `runs/hover-single-test` | `runs/hover-single-test-blind` |
| failures found (per trace) | 1,859 (2.9) | 1,168 found; 1,138 confirmed; 30 rejected |
| fit a mode | 100% (0 NONE) | 99.9% (1 NONE); 99.9% without FM-02 |
| possible modes with failures | 6 of 12, 1–4 each; never used: FM-12 (1 generation instance) and 6 possible ones | 5 of 12, 9 failures in all; 284 more found only by the second call (FM-02 118, FM-08 106) |
| largest mode | FM-02 redundant follow-up query, 40.7% | FM-02, 31.6% |
| billed; requests without reply | $27.33; 0 | $31.93 (two sessions: stopped at 397, resumed); 6 |

## Tests: multi-model taxonomies

Each benchmark's multi-model taxonomy (`runs/<benchmark>-multi/final_taxonomy.json`) on 50 tasks drawn at random
(seed 0) from those generation did not use, with every model's trace of each, one run per model drawn at random:
`data/<benchmark>/multi-model/test/` (`export_test.py --setup multi-model --all-models --tasks 50`; bfcl: 50 scenarios,
one variant each). This replaces an earlier 3-models-per-task set (moved to the Trash, never run).
Per-request timeout: 5 min for BFCL and τ²; 10 min from the SWE-bench run on (long traces timed out 5 times per attempt).

| | SWE-bench | τ²-bench | BFCL |
|---|---|---|---|
| test traces | 600 (50 × 12 models) | 600 (50 × 12) | 850 (50 × 17) |
| dry run, one-pass | 600 calls, ~26.0M input tokens | 600, ~23.2M | 850, ~15.1M |
| dry run, two-pass | 1,200 calls, ~51.7M | 1,200, ~45.7M | 1,700, ~26.7M |
| run dirs | `runs/swebench-multi-test`, `-test-blind` | `runs/tau2bench-multi-test`, `-test-blind` | `runs/bfcl-multi-test`, `-test-blind` |
| one-pass: failures (per trace) | 7,202 (12.0) | 4,250 (7.1); 2 traces failed (Inkling, 490K and 550K chars, timed out) | 1,257 (1.5) |
| one-pass: fit a mode (NONE) | 99.9% (7) | 99.8% (9); 99.3% without FM-01 | 97.2% (35); per model 0–5.7% NONE |
| one-pass: largest mode | FM-01 omitted required reasoning or plan, 52% | FM-01 message and tool call in one turn, 71% | FM-04 redundant tool invocation, 16% |
| one-pass: billed; requests without reply | $57.43; 3 | $38.20; 49 (30 from the two failed traces) | $38.70; 13 (two network blips) |

```bash
python3 generation/judge.py --taxonomy runs/<benchmark>-multi/final_taxonomy.json --traces data/<benchmark>/multi-model/test --no-new-modes --context-tokens 532768 --max-output 65536 --workers 6 --model arena/gemini-3.8-flash --out runs/<benchmark>-multi-test
python3 generation/judge_blind.py --run runs/<benchmark>-multi --traces data/<benchmark>/multi-model/test --context-tokens 532768 --max-output 65536 --workers 6 --model arena/gemini-3.8-flash --out runs/<benchmark>-multi-test-blind
```

Keys: `ARENA_API_KEY` (for `arena/...`), `OPENROUTER_API_KEY` (for `openrouter/...`), or `GEMINI_API_KEY`.

The v3 prompts this pipeline was adapted from are in `v3_reference/`.
