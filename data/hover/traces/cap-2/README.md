# cap-2 — pool-3 on the sample portion, one run each

12 candidates (set `pool-3`) × 50 tasks (split `eval-1`, portion `sample`) × 1
repeat = 600 traces. Solver `gemini/gemini-3.1-flash-lite`. Captured
2026-09-02 as `benchmarks/hover/traces/traces-3/judging`; duplicated here on
2026-09-06 with every identity re-keyed to the registries and verified by hash.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what was expected, what is present, audit results |
| `index.jsonl` | one row per trace: ids, status, call count, cost, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces, one candidate per file, one trace per line |
| `program_states/<candidate_id>.json` | the DSPy program state that ran, as saved by the runner |

A body holds the full run record and, under `judge_view`, the outcome-blind
message list exactly as it was emitted for judging. No gold appears anywhere in
this directory; scores are in `../../outcomes/cap-2.jsonl`.

Every trace here has been judged under both taxonomies: see `../../mappings/`.
