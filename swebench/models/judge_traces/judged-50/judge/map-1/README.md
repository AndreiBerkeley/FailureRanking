# map-1 — RedoAdamast judge run on the judged portion (swebench)

`arena/gemini-3.8-flash`, one pass per trace, batches in parallel; taxonomy fixed, unfitted instances NONE. Taxonomy `tax-1`, no modes added.
600 traces (50 tasks × 12 candidates), 600 judged.
7,202 failure instances, 2,020 candidate instances the judge rejected;
99.9% fit an existing mode; 486 quotes not verbatim.
Billed $57.43. No recovery pass has been run on these traces.

- `mapping.jsonl` — one row per trace: view and cap-1 trace ids, candidate, task, repeat, status, per-code counts,
  the failure instances (turn, message, codes, problem, missing, evidence, quote_valid, none_fits) and the rejected
  ones. No outcome: join `outcomes/cap-1-complete.jsonl` on `cap1_trace_id`.
- `run/` — RedoAdamast's run folder minus `prompts/`: per-trace records (`run/traces/`), `summary.json`,
  `call_report.txt`, `call_log.jsonl`, `taxonomy_extended.json` (identical to `tax-1`). `run/calls/` is not in git.
- `provenance.json` — counts, checks, cost, code hashes.
