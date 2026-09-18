# recovery — did the program's output carry the failure?

A separate pass after the judge. The judge says *what went wrong and where*; this pass
says, for each of those points, *whether the final output carries it*. It is
outcome-free: it reads the trace and the final output the trace contains, never the gold.

```
python3 -m new_pipeline.recovery.run --traces <pool> --mapping <pointjudge run> --out <dir> \
    --structure <benchmark structure.json> [--model openrouter/anthropic/claude-sonnet-5] [--dry-run]
```

## Why a separate pass

The judge must stay blind to whether a failure mattered, or it starts under-reporting the
harmless ones and the occurrence rates lose their meaning. Recovery is a different question
with different evidence — what happened after the point, and what the output shows — and
as its own pass it runs over every existing mapping without re-judging.

## What "recovered" means here

A failure point is recovered when the final output does not carry its effect, **however**
that came about: a later turn corrected it, nothing consumed it, or another path supplied
what the failed step was meant to supply (a union of retrievals, a best-of-n selector).
That last case is what earlier recovery instruments could not see: they looked only for
downstream *events* (a correction, a containment), so a failure at the last step could never
be recovered even when the output was fine without it.

## The program's success rule

The reader sees the same "How this program's output is scored" section the judge's
passes see (`success_rule` in the benchmark's `structure.json`, when declared), and
its `cost_supplied` question says what "contains it" means under that rule: where the
output is scored on documents, only the document's own title line counts; a passage
elsewhere that mentions the entity, or a page about its neighbours, does not supply
it. Added 2026-09-17 after a hand audit of 100 recovered verdicts (60 hover models,
40 GEPA) found 10 wrong, all of one kind: a wasted query hop excused because related
material came back while the entity's own document never did. `summary.json` records
`success_rule_in_view`; the runs `hover-models/recovery-1` and `hover/recovery-1`
predate it.

## The process, per trace (one call)

The reader receives the whole trace, its final output, and the judge's points — turn,
evidence, what was wrong — with the **codes hidden**. For every point it answers four
questions, each with a verbatim quote:

1. **effect** — the artifact the point produced, quoted from the point's own turn;
2. **consumed** — later turns whose input contains that artifact (quoted there);
3. **events** — later turns that corrected it or demonstrably did not use it (quoted);
4. **output** — is the effect visible in the final output (quoted), and, for a point whose
   harm is an absence, is the missing thing present in the output anyway (quoted).

The reader states no verdict. `recovery.py` checks every quote against the section it
claims to come from (exact after whitespace normalisation, else a contiguous match of
≥ 85% of the quote), checks that consumed/event turns are after the point, drops what
fails and records why, and then applies the rule:

| answer | verdict |
|---|---|
| what the point cost is absent from the output | `unrecovered` |
| effect visible in the output | `unrecovered` |
| output cannot settle it, nothing else | `unassessable` |
| output does not carry it, a correction event stands | `corrected` |
| output does not carry it, no later turn consumed it | `contained` |
| output does not carry it, consumed, not corrected — or the cost was supplied by another path | `made_irrelevant` |

Recovered = `corrected` ∪ `contained` ∪ `made_irrelevant`. Missing evidence never becomes
recovery: a recovery claim whose quote is not in the trace is dropped; a point with no
usable output answer is unrecovered.

## Output

`<out>/traces/<trace_id>.json` is the mapping record with `recovery` and
`recovery_evidence` on every point; the mapping itself is untouched. `summary.json` counts
verdicts, quote locations (exact / fuzzy / none) and dropped claims. Traces with no points
are copied through without a call.

## Scoring

`methods/scripts/run_baselines.py --recovery <out>` adds two rows: **unrecovered amplitude**
and **unrecovered incidence** — the existing formulas over the points not found recovered
(`unassessable` and unrecorded points count as unrecovered). On a one-step program every
point is unrecovered and the rows equal amplitude and incidence.

## Tests

`new_pipeline/recovery/test_recovery.py` — quote location, chronology, every branch of the
verdict rule (12 tests, no model calls).
