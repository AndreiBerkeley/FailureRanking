# pointjudge — two readers, two passes each, one decider

The successor to the panel judge in `new_pipeline/judge`. **Implemented, never
run.** Two decisions in its design are still open; see
`judges/proposed/two-reader-decider.md`. It becomes `judge-4` in the archive when
it has produced a mapping.

It lives in its own module rather than replacing `new_pipeline/judge`, so the
panel judge stays exactly as it was for the mappings that cite it.

## What changed

The unit of measurement. The panel judge records a code on a turn, which cannot
say where in the turn the behaviour was, cannot separate two failures on one
turn, and cannot be re-checked without re-reading the turn.

This judge measures **failure points**: a step plus the evidence span that shows
the mistake. Two findings are the same point only when their evidence agrees, so
one step can carry several points, including several of the same kind. An absence
is evidenced by saying what is missing and where it was owed.

## The program's success rule

Every pass (both readers, the mode assignment, the decider) also sees "How this
program's output is scored": the `success_rule` from the benchmark's
`structure.json`, when it declares one (hover does since 2026-09-17; a structure
without one gets no section). It is the scoring definition of the task — for
hover, retrieved document titles, a mention inside another document not counting —
not any task's outcome, so it is gold-free. It is there because a reader that does
not know what the output is scored on judges "what this step needed" by its own
reading of the task, and on hover took a passage that mentions an entity for the
entity's document. `summary.json` records `success_rule_in_view`.

## The five calls

| | |
|---|---|
| reader A, pass 1 | reads the trace **with** the taxonomy in view, reports failure points |
| reader B, pass 1 | reads the trace with **no** taxonomy, reports failure points |
| reader A, pass 2 | assigns modes to its own frozen point list |
| reader B, pass 2 | assigns modes to its own frozen point list |
| decider | reads the full trace and both lists; validates, merges, settles each span, assigns the modes |

Pass 1 produces points only, and the list is frozen before pass 2. That is what
makes an unfittable point visible: a reader naming points and modes in one breath
drops silently whatever the vocabulary does not cover, and that dropped thing is
the coverage measurement.

Both readers may answer that **nothing fits**, and so may the decider. The
taxonomy is a description of what failures look like here, not a checklist.

The only asymmetry between the readers is that A saw the vocabulary before
looking. Everything else is identical, so a difference in what they find is
attributable to that, and both mode opinions are formed under the same
conditions.

There is no discussion round. Deciding whether two spans describe the same thing
is settled once by the decider holding both lists and the trace, rather than
twice by negotiation. Model readers in discussion converge by capitulation, so
the consensus a round produces is not evidence that they agreed.

## Use

```bash
python3 -m new_pipeline.pointjudge.run \
  --taxonomy data/hover/taxonomies/tax-10/taxonomy.json \
  --traces   runs/new_pipeline/hover/pool_judging_cap5 \
  --out      runs/new_pipeline/hover/pointjudge-pilot \
  --structure data/hover/program/structure.json \
  --tasks data/hover/splits/judging-sample-2/split.json --tasks-key portions.judged
```

Print all five prompts and spend nothing:

```bash
python3 -m new_pipeline.pointjudge.run ... --dry-run
```

Runs are resumable and idempotent, on the same rule as the panel judge: a trace
recorded `judged` is left alone, a trace recorded `failed` is retried while its
attempt count is below `--max-attempts`.

| knob | default | |
|---|---|---|
| `--model` | `gemini-3.6-flash` | a Gemini id, or `openrouter/<vendor>/<model>` |
| `--reader-model` | falls back to `--model` | readers A and B |
| `--decider-model` | falls back to `--model` | the decider reads the full trace plus both lists; this is the call worth spending on |
| `--workers` | 4 | traces in parallel; the five calls of one trace are sequential |
| `--timeout` | 300 | per socket operation, so a stalled read fails and retries rather than parking a worker |
| `--max-attempts` | 3 | attempts before a failed trace is left be |
| `--limit` | none | first N traces, for a pilot |
| `--thinking` | unset | `MINIMAL` / `LOW` / `MEDIUM` / `HIGH` |

Cost is exactly five calls per trace, against at most four for the panel judge. They are not
five latencies, though: A's two passes and B's two passes are independent chains and only
the decider needs both, so the two chains run concurrently and a trace costs three
call-latencies. The readers never see each other's work; only the issue time changed.

**Never launch a billed pass without Andrei.** Prepare the command and the
estimate; he runs it.

## Output

`codes` is still a `{code: count}` map, so anything that reads the panel judge's
output reads this one. The count is one occurrence per distinct step, the same
rule the panel judge states to its annotators, so the two are commensurable.

Everything else is new and sits beside it:

```
points          the decider's final points: turn, agent, evidence, problem,
                codes, none_fits, missing, and which reader found it
rejected        every point a reader reported that the decider threw out, with why
readers.a/b     each reader's own points, its per-turn `checked` account, and
                its own mode assignments with fitness
agreement       points, found by both, only A, only B, decider only, rejected
mode_agreement  for points both found: same modes or different
coverage        how often each reader and the decider found nothing that fits,
                and the described gaps
```

The last three are the reliability and coverage component of the measurement
framework, and none of them costs an extra call. They exist because a decider
that resolves everything in one call otherwise leaves no record of having been
contested.

## Failure is not silence

A trace whose calls did not all succeed is recorded `status: "failed"` with an
empty code map that no aggregation counts. Gold is stripped at the boundary by
`new_pipeline/goldfree.py` and the removed keys are recorded per trace.
