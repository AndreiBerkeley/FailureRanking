# terminalbench

Terminal-Bench 2.0: an agent solves a task in a Linux container by typing shell
commands; a hidden test suite then checks the container's final state (reward
0 or 1). Nothing here was run by us. Every trace is a trajectory the public
leaderboard recorded (`harborframework/terminal-bench-2-leaderboard`, Apache
2.0), converted to the judge view by `scripts/convert_tb2.py`; the task texts
come from `harborframework/terminal-bench-2.0`.

The candidates are the eight models the benchmark's own reference agent,
Terminus 2, was run with on the leaderboard (89 tasks × 5 trials each). The
agent, its instructions and its harness are identical across candidates, so a
candidate is a model, not a prompt.

## Identities

| thing | id | where defined |
|---|---|---|
| task | the benchmark's task name, e.g. `largest-eigenval` | `tasks/tasks.jsonl` |
| candidate | `tb2-<model>` | `candidates/registry.jsonl`; the set is `candidates/sets/terminus2-1.json` |
| trace | (candidate, task, repeat); `trace_id` = sha256("tb2\|model\|trial")[:24] | `traces/<capture>/<candidate>.jsonl.gz` |
| repeat | per task and model, the five trials ordered by `started_at`; the earliest is repeat 0 | `traces/<capture>/manifest.json` |
| capture | `cap-1` (repeat 0, all 89 tasks), `cap-2` (repeats 1–4 of the 20 judged tasks) | `traces/cap-N/manifest.json` |
| split | `pools-1`: judged 20 / eval 69 | `splits/pools-1/split.json` |

## Layout

```
tasks/            89 tasks: instruction (verbatim), category, difficulty, tags — the benchmark's own labels
program/          structure.json: the Terminus 2 loop, its tools, and the success rule the judge and recovery reader see
candidates/       registry of the 8 models; sets/terminus2-1
splits/pools-1/   judged 20 + eval 69 (scripts/make_split.py, seed 2026)
traces/cap-1/     8 candidates × 89 tasks × repeat 0            712 traces
traces/cap-2/     8 candidates × 20 judged tasks × repeats 1–4  637 traces (3 trials never produced a trajectory)
outcomes/         cap-1, cap-2: the verifier reward per trace, kept out of every trace
scripts/          convert_tb2.py (leaderboard -> this layout), make_split.py
```

## How the pieces are used

- **judged, repeat 0** (160 traces, `cap-1`): the judge and the recovery reader read these; incidence and the other scores are computed from them.
- **judged, repeats 1–4** (637 traces, `cap-2`): the taxonomy generator's corpora — generation, refinement, gate and gap test. Exported with `export_pool --task-repeat-ids`, each rerun of a task is its own task to the corpus planner (80 pseudo-tasks), so the planner's task-disjointness holds by (task, repeat). No judged trace (repeat 0) is ever in a generator corpus.
- **eval, repeat 0** (552 traces, `cap-1`): the generalization target. Only its outcomes are read, after the fact.
- The bar (judged-20 repeat-0 pass rate ranking vs eval-69 repeat-0) is tau-b **+0.579** over the seven frontier models.

## Outcomes

`score` is the verifier's reward (0/1). A trial with no reward — the verifier did not run or its
reward file is missing, 12 of 712 in cap-1 — scores 0 and carries `reward_missing: true`, as the
leaderboard counts it. `exception` records how the harness ended the run (`AgentTimeoutError`
after 900 s is the common one); it is not an outcome and the converter also writes it into the
trace's closing ENVIRONMENT block, because the agent's run really did end that way.

Repeat-0 pass rates: Claude-Opus-4.6 .685, GPT-5.3-Codex .596, GLM-5 .506, Minimax-m2.5 .416,
Kimi-k2.5 .404, GLM-4.7 .382, DeepSeek-V3.2 .371, AfterQuery-GPT-OSS-20B .225.

## Caveats

- Traces are long: 57K chars per trace (GPT-5.3-Codex) to 115K (GLM-4.7) on the judged set; the
  AfterQuery candidate averages 338K chars with one trace of 1.02M chars. Nothing in the pipeline
  truncates a trace.
- The AfterQuery submission is the only non-frontier candidate and carries 8 of the 12
  unresolved trials; it is in the registry and the set but was not used to build the split's strata.
- Three trials of the judged tasks (Kimi ×1, GLM-4.7 ×2, all `DaytonaError`) have a result record
  but no trajectory; they still take their repeat slot (none is repeat 0) and are absent from cap-2.
