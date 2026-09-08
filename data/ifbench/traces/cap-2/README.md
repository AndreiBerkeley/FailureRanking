# cap-2 — the taxonomy-induction corpus

300 traces of the 12 candidates on 50 tasks of the optimizer's train portion,
one run each, kept in the outcome-blind message form a taxonomy generator
reads. This is the corpus the earlier pipeline's taxonomy was induced from;
that taxonomy is archived in `benchmarks/ifbench/taxonomies/tax-1` and not carried
here. The tasks
were seen by the optimizer, which is why they and not the evaluation tasks were
spent on induction. Scores recorded beside the source traces are in
`../../outcomes/cap-2.jsonl`; the `outcome_score` field was removed from the
message metadata. Source: `benchmarks/ifbench/traces/traces-1/generation/corpus`.
