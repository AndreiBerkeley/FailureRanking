# Trial: adamast-taxonomy-regen (2026-08-07)

**Hypothesis.** The shakedown taxonomy (v3) is instrument-limited: its
role-local B codes are dominated by style/protocol violations with weak or
inverted outcome-link (see the 002/008/009 dissection and the C-only
result, 2026-08-07 discussion). Regenerating the taxonomy with the actual
AdaMAST protocol (`adamast generate`, agreement-gated with a κ target and
coverage floor) over legacy HoVer traces should yield a vocabulary whose
codes are more outcome-relevant — measurable later via gold-pass@aff and
the C-only-style comparison.

**Setup.** `convert_traces.py` maps legacy run-export traces
(`lm_calls`/`prediction` schema) into AdaMAST `messages` format.
Deterministic sample, no RNG: per candidate, first 5 tasks in sorted
source_id order among held-out tasks **not in the 50-task scored subset**,
repeat 0 only → 60 traces across all 12 candidates. Freeze discipline:
taxonomy generation sees no trace that Φ scores. All 60 outputs pass
`adamast validate` (format: messages).

Generation itself is a **billed run** (hard rule 1): command prepared for
Andrei, launched by Andrei, Bedrock credentials via the AWS config chain
sourced from his shell. Model pinned to the legacy runs' judge model
(`us.anthropic.claude-sonnet-4-5-20250929-v1:0`) for comparability.

**Caveats.** Inherits the data amendment's restriction: traces are
shakedown-era, so any taxonomy generated here is prototyping-grade — the
official E001 taxonomy must be frozen on E001's own trace source under its
own TIMELINE entry. Launch of the generate run gets a dated TIMELINE setup
entry at launch time.

**Result.** PENDING — awaiting Andrei's launch of the generate command.

**Conclusion.** PENDING.
