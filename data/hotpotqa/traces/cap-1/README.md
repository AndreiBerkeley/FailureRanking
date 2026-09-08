# cap-1 — pool-1 on the sample portion, five runs each

12 candidates × 100 tasks (split `eval-1`, portion `sample`) × 5 repeats = 6,000
traces. Solver `gemini/gemini-3.1-flash-lite`. Repeats are independent samples from the
provider's default sampler, not seeded replicates; caching was disabled, so they
genuinely re-execute. Captured 2026-08-26 as `legacy/archive-2026-09-01/hotpotqa/traces-1/measurement`;
duplicated here on 2026-09-06, re-keyed to the registries.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what is present, audit results |
| `index.jsonl` | one row per trace: ids, status, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces, one candidate per file, one trace per line |

A body holds each module's inputs and outputs in order (`stages`), the final
`prediction`, and, where the source produced one, the outcome-blind message
list a judge reads (`judge_view`). The runner's per-trace score is not in the
body; it is in `../../outcomes/cap-1.jsonl`. Trace ids follow the source's own
recipe, so anything the earlier trial recorded against these traces can be
looked up by the same id.
