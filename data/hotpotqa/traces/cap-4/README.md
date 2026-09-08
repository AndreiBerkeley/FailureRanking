# cap-4 — pool-1 on the pools-1 generalization fill, one run each

12 candidates × 400 tasks (split `pools-1`, portion `generalization`, the tasks that
still lacked traces) × 1 repeat = 4,800 traces. Solver `openrouter/google/gemini-3.1-flash-lite` (openrouter
route). Captured 2026-09-06 by `data/scripts/capture_artifact_pool.py`; turned into this
capture on 2026-09-06.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what is present, audit results, provider usage |
| `index.jsonl` | one row per trace: ids, status, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces: each module's inputs and outputs in order, the prediction, and the outcome-blind `judge_view` |

The runner's per-trace score is not in the body; it is in `../../outcomes/cap-4.jsonl`.
Together with the earlier captures this completes the `generalization` pool of `pools-1`.
