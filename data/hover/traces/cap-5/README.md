# cap-5 — pool-3 on the pools-1 judging fill, one run each

12 candidates (set `pool-3`) × 450 tasks (split `pools-1`, portion `judging`, the
tasks that still lacked traces) × 1 repeat = 5,400 traces. Solver `gemini/gemini-3.1-flash-lite`
(gemini-direct route). Captured 2026-09-06 by `data/hover/scripts/capture_pool.py`;
turned into this capture on 2026-09-06, re-keyed to the registries and verified by hash.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what was expected, what is present, audit results |
| `index.jsonl` | one row per trace: ids, status, call count, cost, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces, one candidate per file, one trace per line |
| `program_states/<candidate_id>.json` | the DSPy program state that ran |

Bodies hold the full run record and the outcome-blind `judge_view`. No gold is
here; scores are in `../../outcomes/cap-5.jsonl`. Together with the earlier
captures this completes the `judging` pool of `pools-1`.
