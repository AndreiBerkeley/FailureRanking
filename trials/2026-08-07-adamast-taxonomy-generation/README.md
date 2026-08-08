# Trial: adamast-taxonomy-generation (2026-08-07)

**Hypothesis.** The shakedown v3 taxonomy is instrument-limited: its
high-prevalence B codes are style/protocol violations with weak or
inverted outcome-link (see the 002/008/009 dissection and the C-only
result, 2026-08-07 discussion). Generating the project's prototype
taxonomy with the actual AdaMAST protocol (`adamast generate`,
agreement-gated with a κ target and coverage floor) over legacy HoVer
traces should yield a vocabulary whose codes are more outcome-relevant —
measurable later via gold-pass@aff and a C-only-style comparison after
re-judging.

**Setup.** `convert_traces.py` maps legacy run-export traces
(`lm_calls`/`prediction` schema) into AdaMAST `messages` format.
Deterministic sample, no RNG: per candidate, first 5 tasks in sorted
source_id order among held-out tasks **not in the 50-task scored
subset**, repeat 0 only → 60 traces across all 12 candidates (freeze
discipline: generation sees no trace that Φ scores). All 60 outputs pass
`adamast validate` (format: messages).

**Freeze rule (pre-registered, Andrei).** Only trace-grounded codes
survive the freeze: any code without cited occurrences in the 60
generation traces is dropped by a deterministic post-run filter
(the CLI's `--coverage-floor` gates aggregate agreement coverage in the
acceptance test, not per-code support, so it cannot express this rule).
Accepted consequence: failure modes first appearing in scoring traces
stay unmeasured — absorbed by Q_Taxonomy's coverage term in Ψ.

**Run.** Billed (hard rule 1): prepared here, launched by Andrei.
Bedrock via the AWS credential chain; model pinned to the legacy judge
model (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`) for
comparability. Output dir: `taxonomy_v0/`. Prototyping-grade per the
2026-08-07 data amendment: the official E001 taxonomy must be frozen on
E001's own trace source under its own TIMELINE entry.

**Result.** Run completed by Andrei (2026-08-07 ~20:42, 5/5 agreement
rounds, output `taxonomy_v0/`). **The protocol did not accept the
taxonomy**: coverage 0.94 ≥ 0.70 passed, but macro Fleiss κ = 0.37 vs
the 0.75 target → manifest status `review_required`. 32 codes were
drafted; across all five agreement rounds (25 judged traces,
4 annotators, reconciled assignments) **only 6 codes were ever
assigned**: A.8 Downstream_Handoff_Failure (38), A.5 Output_Truncation
(16), B.9 Coordinator_Premature_Hop_Termination (14), A.4 Task_Refusal
(2), B.1 Coordinator_Unclear_Task_Specification (1),
A.7 Upstream_Information_Loss (1). Five of those six are on the run's
own low-agreement list — only A.5 is both used and consistently
assigned. The draft artifacts carry no per-code trace-id citations, so
reconciled agreement assignments are the only citable support; the
pre-registered grounding filter therefore keeps 6/32 codes (3/32 at
support ≥ 3).

**Conclusion.** The trace-grounding hypothesis was validated harder
than expected: 26 of 32 generated codes are purely theoretical on these
traces, and the annotators cannot consistently apply most of the rest —
the protocol's own κ quantifies Q_Taxonomy for this benchmark/config as
low. Freeze decision (Andrei's): accept the tiny grounded core as
prototype v0, or rerun generation with adjusted config. Not yet frozen;
nothing registered.
