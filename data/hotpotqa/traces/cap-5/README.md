# cap-5 — pool-1 on the pools-1 judging fill, one run each

12 candidates × 50 tasks (split `pools-1`, portion `judging`, the tasks that
still lacked traces) × 1 repeat = 600 traces. Solver `gemini/gemini-3.1-flash-lite` (gemini-direct
route). Captured 2026-09-06 by `data/scripts/capture_artifact_pool.py`; turned into this
capture on 2026-09-06.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what is present, audit results, provider usage |
| `index.jsonl` | one row per trace: ids, status, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces: each module's inputs and outputs in order, the prediction, and the outcome-blind `judge_view` |

The runner's per-trace score is not in the body; it is in `../../outcomes/cap-5.jsonl`.
Together with the earlier captures this completes the `judging` pool of `pools-1`.
