# cap-2 — pool-1 on the domain portion, one run each, judge view only

12 candidates × 200 tasks (split `eval-1`, portion `domain`) × 1 repeat =
2,400 traces. Solver `gemini/gemini-3.1-flash-lite`. The source kept only the
outcome-blind message list for these runs, so each body carries a `judge_view`
and no stage record. The recorded scores are in `../../outcomes/cap-2.jsonl`;
the `outcome_score` the source stored beside each message list was removed.
Source: `legacy/archive-2026-09-01/hotpotqa/traces-1/generalization/corpus`.
