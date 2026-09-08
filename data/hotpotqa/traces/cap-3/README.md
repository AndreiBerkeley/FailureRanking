# cap-3 — the taxonomy-induction corpus

300 traces of the 12 candidates on 25 tasks of the optimizer's train portion,
one run each, kept in the outcome-blind message form a taxonomy generator
reads. This is the corpus the earlier pipeline's taxonomy was induced from;
that taxonomy is archived in `benchmarks/hotpotqa/taxonomies/tax-1` and not carried
here. The tasks
were seen by the optimizer, which is why they and not the evaluation tasks were
spent on induction. Scores recorded beside the source traces are in
`../../outcomes/cap-3.jsonl`; the `outcome_score` field was removed from the
message metadata. Source: `legacy/archive-2026-09-01/hotpotqa/traces-1/generation/corpus`.
