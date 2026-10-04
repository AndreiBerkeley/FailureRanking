# swebench

SWE-bench Verified: 500 real GitHub issues from 12 Python repositories, each
with the repository state the issue was filed against. A run is given the
issue text and the repository and must produce a code patch. Gold is a set of
tests: the patch passes if the tests that failed before the fix now pass
(`FAIL_TO_PASS`) and the tests that passed before still pass (`PASS_TO_PASS`),
run inside the instance's own environment. The 500 were screened by human
annotators from the 2,294-instance SWE-bench test set for solvability and
clear specification; each carries an annotated difficulty band.

## Status

Traces, candidates, split and structure added 2026-09-24 (below). No taxonomy, judge run or mapping yet.

```
tasks/            registry with gold                                   500 tasks
program/          structure.json: the mini-SWE-agent loop and the success rule the judge and recovery reader see
candidates/       registry of 12 models; sets/mini-v2-1
splits/pools-3/   taxonomy 30 / judged 50 / eval 420 (scripts/make_split.py, seed 2026); pools-1, pools-2 superseded, never used
traces/cap-1/     12 candidates x 500 tasks, one attempt       5,985 traces (bodies not in git; see below)
outcomes/         cap-1: resolved per trace, kept out of every trace
scripts/          materialize_tasks.py, convert_mini_swe.py, make_split.py
```

## RedoAdamast runs (copied 2026-09-29)

RedoAdamast's multi-model taxonomy run and judge run on this capture, copied by
`data/scripts/import_redo_adamast.py`; the originals are untouched in `~/Desktop/RedoAdamast`.

```
traces/view-1/     its judge views of 690 cap-1 runs (90 generation, 600 test); index.jsonl joins them to cap-1
splits/pools-4/    taxonomy 30 / judged 50 (600 traces) / eval 405 tasks; its draw, not stratified
taxonomies/tax-1/  29 codes (FM-NN), gemini-3.8-flash, ~$32 est.
mappings/map-1/    600 of 600 judged, 7,202 failure instances, $57.43; no recovery pass
outcomes/cap-1-complete.jsonl   cap-1 outcomes of the 485 tasks every candidate ran (rows identical to cap-1)
```

`traces/cap-1/` bodies and `outcomes/cap-1.*` were moved to RedoAdamast on 2026-09-26
(`data/swebench/traces/`, `data/swebench/outcomes.jsonl` there).

## Where the traces come from

Nothing was run by us. The candidates are the SWE-bench leaderboard's bash-only submissions made with
**mini-SWE-agent 2.0.0** in February 2026: one agent, one bash tool, the same system and task prompt, one
attempt per task. Only the model differs. Trajectories: `s3://swe-bench-submissions/bash-only/<run>/trajs`
(public); per-task outcomes: `github.com/SWE-bench/experiments`, `evaluation/verified/<run>/per_instance_details.json`.

| candidate | resolved | candidate | resolved |
|---|---:|---|---:|
| swe-claude-4-5-opus-high | .768 | swe-claude-4-5-sonnet-high | .714 |
| swe-gemini-3-flash-high | .758 | swe-kimi-k2-5-high | .708 |
| swe-minimax-2-5-high | .758 | swe-gemini-3-pro-high | .706 |
| swe-claude-4-6-opus | .756 | swe-deepseek-3-2-high | .700 |
| swe-glm-5-high | .728 | swe-claude-4-5-haiku-high | .666 |
| swe-gpt-5-2-high | .728 | swe-gpt-5-mini | .562 |

Resolved is the leaderboard's per-task record over all 500. On the 485 tasks every candidate has a trace for,
44 of 66 candidate pairs are resolvable at 1.96 SE of the paired per-task difference; 207 tasks are resolved
by all 12 and 57 by none.

Three things were corrected on the way in:
- **Gemini 3 Pro**'s `per_instance_details.json` marks every task unresolved against a published 69.6%, and
  GPT-5.2 Codex has none. Both are rebuilt from the harness's own `logs/<instance>/report.json`; the
  rebuild reproduces Claude 4.6 Opus's published file exactly (378/378). Gemini 3 Pro rebuilds to .706.
- **GPT-5.2 Codex is left out**: its 500 uploaded trajectories are byte-identical to GPT-5.2 (high)'s and
  record gpt-5.2 as the model, while its evaluated patches differ.
- **Runs the provider cut short** (exit status ServiceUnavailableError or Timeout: 11 Gemini 3 Pro, 4 Gemini 3
  Flash) have neither a trace nor an outcome, as infrastructure errors are handled on tau2bench and bfcl.

Traces average 64K (Claude 4.6 Opus) to 176K characters (Gemini 3 Flash) and are not cut. The bodies
(`traces/cap-1/*.jsonl.gz`, 131 MB) are not committed; to rebuild them:

```
python3 data/scripts/fetch_keys.py https://swe-bench-submissions.s3.amazonaws.com data/swebench/traces/cap-1/source_keys.txt <raw dir> 16
python3 data/swebench/scripts/convert_mini_swe.py --raw <raw dir> --per-instance <dir of per_instance_details.json + metadata.yaml per run> \
    --reports <dir of rebuilt report.json per run> --runs <the 12 runs in candidates/registry.jsonl> --layout data/swebench
```

## The split

`pools-3` (current): taxonomy 30 / judged 50 / eval 420 (J/G 12%). The judged set was raised from 25 to 50 on
2026-09-24. At 25 tasks the ranking resolves pass-rate gaps of about 0.18, while 9 of the 12 candidates sit within
0.07. The taxonomy pool feeds the gate-free generation pipeline (see new_pipeline/README.md), every stage on its own
tasks: generation 16 tasks at 4 traces (69 with the per-candidate failure top-up, 33 failing), refinement 9 tasks at
3 traces, gap test 5 tasks at 4 traces. Each portion has the benchmark's own mix of task difficulty (four strata by
mean resolve rate). `pools-1` (75 / 25 / 400) and `pools-2` (75 / 50 / 375) are superseded and were never used; the
judged 50 are the same in pools-2 and pools-3.

## Identities

| thing | id |
|---|---|
| task | the SWE-bench `instance_id`, e.g. `django__django-11099` |
| candidate | `swe-<model>`, e.g. `swe-claude-4-6-opus` (the run folder's model part) |
| trace | (candidate, task); `trace_id` = sha256("swebench\|candidate\|task")[:24] |

## What exists beyond the 500

The full SWE-bench release is in the same local cache: 2,294 test instances,
225 dev, 19,008 train. The test set is the pool the 500 were drawn from and is
available if a larger pool is wanted, at the cost of the human screening.

## Rules

- `tasks/` is gold-bearing: the gold patch, the test patch, the test lists and
  the evaluation script all live there and nowhere else.
- Running a task requires the instance's container image (`meta.image`) and the
  evaluation harness; neither is stored here.
