# The measurement judge

Turns a frozen taxonomy plus a trace set into code counts per (task, candidate).
This is the instrument the score is computed from. It is **not** the judge inside
the taxonomy pipeline: that one reads a refinement corpus and feeds a refiner,
and there is no refiner downstream of this.

```
python -m measure.run --taxonomy <tax.json> --traces <dir> --out <dir>
python -m measure.run ... --dry-run     # print the exact prompts, spend nothing
```

## The output

Per trace, and deliberately nothing more:

```json
{"A.1": 2, "C.3": 1}
```

Occurrence and count. No confidence, evidence, severity, ordering, or recovery.
Each of those is a later layer, and the module is arranged so each arrives as an
added stage or an added field rather than a rewrite.

Everything else the run learns -- per-annotator answers, the vote split, the open
reader's problems, what mapped to nothing -- lands in the same file beside
`codes`, where no scoring path has to read it.

## The shape

```
panel   N independent readers, each holding the taxonomy   -> vote
open    one reader holding NO vocabulary                   -> mapped to codes
        union of the two branches
```

Neither branch is told **how** to look. No search procedure, no causality
reconstruction, no ordering of attention. The panel is given the vocabulary and
asked what occurred; the open reader is given nothing and asked what went wrong.

**Every turn is accounted for (2026-09-02).** Traces are rendered as
delineated agent turns (`taxonomy2/render.py`: each turn carries its agent,
its own instructions, its input, its output), and both readers answer per
turn: codes or problems, or a one-line `checked` account when there are
none. A response that omits a turn or leaves one silent is re-asked once,
then the trace is recorded as failed. This is not telling the reader how to
look; it is refusing silence as an answer. Measured on ten audited traces, a
reader asked for one trace-level answer recorded findings on the first agent
and stopped, skipping the query-writing turns in six of ten. A trace-level
count is the sum over turns, so "how many times" is a count of turns and
steps rather than a reading-style artifact. Per-turn votes are kept
(`votes_by_turn`), and `profiles.json` carries a per-agent breakdown, so a
profile can be split by sub-agent without re-judging.

**Traces are never elided.** `--max-trace-chars` defaults to 0. The earlier
48,000-character limit cut the middle out of 142 of the 600 hover judging
traces; a cut trace loses turns, and a reader then reports that the agent
produced nothing.

**Model.** `--model` takes a Gemini id or `openrouter/<vendor>/<model>`;
`--thinking` sets the reasoning level; `--max-output` defaults to 65,536 since
thinking tokens count against it. Measured on the observation pass with the
same traces: Gemini 3.1 Pro found about twice what 3.6 Flash did at the same
thinking budget. `--per-turn` makes one call per turn per reader instead of
one per trace; it multiplies calls by the turn count.

| knob | default | |
|---|---|---|
| `--annotators` | 4 | panel size |
| `--threshold` | 2 | annotators needed for a code to fire |
| `--open` / `--no-open` | on | the vocabulary-free reader |
| `--temperature` | 0.0 | matches the rest of the pipeline |
| `--workers` | 4 | |
| `--structure` | none | benchmark structure json, names the agents in turn headers |
| `--model` / `--thinking` / `--max-output` | gemini-3.6-flash / unset / 65536 | reader model and effort |
| `--per-turn` | off | one call per turn per reader |
| `--max-trace-chars` | 0 | never elide |

Cost is `annotators + 2` calls per trace with the open branch, `annotators`
without. Judging is the dominant cost of the project, so measure the marginal
value of a stage on a sample before paying for it at full scale.

## Four decisions worth knowing

**The panel does not deliberate.** A threshold vote is mechanically identical for
every trace and every candidate; a deliberation's outcome turns on which
annotator speaks first. And the vote split is the raw material for a later
confidence layer -- recorded for free while annotators are independent, destroyed
unrecoverably once they reconcile. Deliberation can be added as an opt-in stage.

**The open branch is for recall, not coverage.** An unmapped problem cannot enter
a per-code score, and forcing it into the nearest code is the bad assignment the
design exists to avoid. It is there because a reader holding twenty codes misses
what a reader holding none notices; those findings map onto codes we already have
and enter cleanly. `"none"` is a legal answer, and that escape hatch is what
separates mapping from force-fitting. Unmapped problems are recorded and never
scored.

**Counts are max across branches, never sum.** We do not record where a behaviour
occurred, so two branches reporting one code cannot be shown to have found
different incidents. Summing would double count. The count rule is stated to the
annotator -- one per distinct step -- because otherwise "how many times" is a
reading-style artifact rather than a measurement.

**Failure is not silence.** A trace whose calls did not all succeed is recorded
`status: "failed"` with an empty map that no aggregation counts. "Judged, found
nothing" and "we could not judge this" must never collapse into the same empty
dict. Partial panels are refused for the same reason the threshold exists: 2 of 2
is not the evidence 2 of 4 is. `summary.json` reports failures per candidate,
because uneven failure across candidates biases the ranking.

## Gold

Stripped at the boundary by `pipeline/goldfree.py`, the same rule the taxonomy
pipeline uses, and the removed keys are recorded per trace so the outcome-free
claim is auditable.

## Open

Whether the count should be used at all, or only `count > 0`. Counts are
confounded with trace length -- a verbose candidate has more steps and so more
opportunities -- which sits badly with the rule that more evidence should affect
uncertainty and coverage rather than mechanically penalise a candidate. Binary
stays derivable as `count > 0`, so this can be settled without re-judging.
