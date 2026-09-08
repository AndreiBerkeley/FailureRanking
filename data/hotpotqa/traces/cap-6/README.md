# cap-6 — pool-1 on the pools-1 taxonomy fill, one run each

12 candidates × 200 tasks (split `pools-1`, portion `taxonomy`, the tasks that
still lacked traces) × 1 repeat = 2,400 traces. Solver `openrouter/google/gemini-3.1-flash-lite` (openrouter
route). Captured 2026-09-07 by `data/scripts/capture_artifact_pool.py`; turned into this
capture on 2026-09-07.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what is present, audit results, provider usage |
| `index.jsonl` | one row per trace: ids, status, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces: each module's inputs and outputs in order, the prediction, and the outcome-blind `judge_view` |

The runner's per-trace score is not in the body; it is in `../../outcomes/cap-6.jsonl`.
Together with the earlier captures this completes the `taxonomy` pool of `pools-1`.

Statuses: {'ok': 2400}. `ok` is a complete run; `parse_failed` is a run whose
output dspy could not parse (the candidate's failure, scored 0 by the metric);
`capture_failed` is a task for which the provider returned no completion at all,
almost always a content block on the prompt itself. Such a trace is empty, carries
the provider's reason, is scored 0.0 like a parse failure, and is flagged
`capture_failed` in the outcomes file so an analysis can leave it out. The pool
export never includes it.
