# cap-1 — pool-3 on the optimizer's split, one run each

12 candidates (set `pool-3`) × 550 tasks (split `gepa-1`, train and validation
portions) × 1 repeat = 6,600 traces. Solver `gemini/gemini-3.1-flash-lite`.
Captured 2026-09-01 as `benchmarks/hover/traces/traces-3/generation`; duplicated
here on 2026-09-06 with every identity re-keyed to the registries and verified by hash.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what was expected, what is present, audit results |
| `index.jsonl` | one row per trace: ids, status, call count, cost, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces, one candidate per file, one trace per line |
| `program_states/<candidate_id>.json` | the DSPy program state that ran, as saved by the runner |

A body holds the full run record (`input`, `prediction`, every `lm_call`) and,
under `judge_view`, the outcome-blind message list exactly as it was emitted for
judging. No gold appears anywhere in this directory; scores are in
`../../outcomes/cap-1.jsonl` and the gold itself in `../../tasks/tasks.jsonl`.

These tasks are the ones the optimizer saw. Under the project's rules they are
forbidden for any scoring that claims to be free of optimizer influence. The
two taxonomies in `../../taxonomies/` were induced from traces in this capture.
