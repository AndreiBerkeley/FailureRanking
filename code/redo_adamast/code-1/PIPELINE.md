# Taxonomy generation pipeline

Goal: find every failure mode of one agent system on one domain from a small random sample of
its traces, at the lowest cost.

## Variables

| variable | meaning | default |
|---|---|---|
| T | traces in the full corpus | — |
| p | sample fraction | — |
| N | sampled traces, N = p·T | — |
| K | annotators | 4 |
| R | segment 1 rounds | 1 |
| M | new traces per segment 1 round, and per final round | 5 |
| F | final validation rounds | 1 |
| Q | annotators who must find a failure for it to be kept | 2 |
| D | discussion rounds within a segment 1 round | 2 |
| κ* | agreement target (reported only) | 0.75 |
| c* | coverage target (reported only) | 0.70 |
| S | instances a mode needs before it is checked for a split | 4 |

## Traces

All traces come from the same agent system. N are sampled at random.

- Initial generation uses N − R·M of them.
- Segment 1 uses the other R·M: M new traces each round.
- Segment 2 uses all N.
- The final validation uses F·M further traces that no earlier step has seen (`validation/`).

The traces must not show whether a run succeeded; passing clean traces is up to the caller. The only
exception is the answer-provided variant (`--answers`, see Run), which gives every step each trace's
correct final answer.

Every trace is passed in full; nothing is cut. A trace too long for the model's context is split
into consecutive parts, each sent in its own call, and the results are combined. Field analysis
uses as many calls as its traces need.

## Initial generation

| step | does | input | output |
|---|---|---|---|
| Field analysis | describes the kind of work and what doing it correctly looks like | the N − R·M traces | description of correct work |
| Observation | checks each trace step by step and records every failure instance | description of correct work; one trace | failure instances |
| Abstraction | groups the instances into failure modes | description of correct work; all instances | draft modes, each naming its instances by id (their records are attached from observation); instances it could not place, with reasons |
| Consolidation | merges duplicate modes and fixes format; removes nothing | draft modes | initial taxonomy |

## Segment 1: inter-annotation + refinement

R rounds. Each round:

| step | does | input | output |
|---|---|---|---|
| Discovery | each of the K annotators finds failure instances on its own | description of correct work; one trace | K lists of instances per trace |
| Reconciliation | matches the K lists and keeps failures found by at least Q annotators | one trace; its K lists | agreed failures |
| Assignment | each annotator gives every agreed failure one mode, or NONE | taxonomy without instances; one trace; its agreed failures | K labels per failure |
| Discussion (up to D rounds) | for each failure without a unanimous label, each annotator sees the others' labels and reasons and gives a final label | taxonomy without instances; one trace; its disputed failures with all labels | final labels |
| Agreement (no model call) | measures how consistently the taxonomy was applied | final labels | κ, the mean pairwise Cohen's κ over the K annotators; coverage, the share of labels that are not NONE; κ per mode |
| Refinement (unless every failure got the same mode from all annotators and no label is NONE) | rewrites unclear modes; merges or separates confused pairs; widens or adds modes for unfitted failures; removes a mode only by merging it | taxonomy; agreement; failures still disputed; failures at least half the annotators labelled NONE | revised taxonomy |

κ and coverage are also recorded before discussion.

## Segment 2: gap + split

| step | does | input | output |
|---|---|---|---|
| Gap | gives every actual failure in the trace the existing mode that covers it, and proposes a new mode only when none does, naming the closest mode and why it does not fit; also reports possible failures no mode would cover | taxonomy with two example instances per mode; one trace | actual failures an existing mode covers, added to that mode as instances; proposed modes, each tagged `gap: missed` (has an instance) or `gap: possible` (awaits confirmation) |
| Merge | adds the proposals to the taxonomy, merging duplicates (consolidation prompt) | taxonomy; proposed modes | taxonomy after gap |
| Split (modes with at least S instances) | decides whether a mode is really several kinds of wrong action | taxonomy; the mode; its instances | split or not; if split, the parts and their instances |

## Final validation: inter-annotation + refinement

F rounds on the unseen `validation/` traces, M per round, with the same steps as segment 1
(discovery, reconciliation, assignment, discussion, agreement, refinement unless perfect). It checks
the taxonomy after the gap step and the split, on traces none of them saw.

## Judge

Applies a taxonomy to traces and adds modes as it goes. Traces are judged in batches of W (default 6),
in parallel, all with the same taxonomy; each batch is judged with the modes added before it.
With `--no-new-modes` the judge only applies the taxonomy, and the traces go through one continuous pool of W
workers instead of batches (each call starts as soon as a worker is free): an instance no mode fits is marked NONE
with what kind of failure it is, and nothing is added (prompt `judge_fixed.md`).

| step | does | input | output |
|---|---|---|---|
| Judge (one call per trace) | finds every failure instance in the trace and gives each one a mode; for an instance no mode fits, proposes a new mode (the new modes of one trace are distinct from each other); lists what it considered and rejected | the current taxonomy without instances; one trace | final points (turn, evidence, what went wrong), each with its mode; rejected points with reasons; new modes |
| Add modes (end of each batch) | makes the batch's new modes distinct from each other (one call, when there are at least two; edits only), then appends them with new ids; existing modes are never changed | the batch's new modes and their instances | the taxonomy used for the next batch |

The points are in the format the recovery pass reads.

## Recovery

FailureRank's recovery pass, copied into `recovery/` with only its imports changed. It runs after the
judge and says, for each point, whether the final output carries it.

| step | does | input | output |
|---|---|---|---|
| Recovery (one call per trace) | for each point, answers four questions with quotes: what it produced, which later steps used it, what corrected it, and whether the final output carries it | the trace; its final output; the judge's points with modes hidden | the answers; no verdict |
| Verdict (no model call) | checks each quote against the trace, drops what it cannot find, and applies a fixed rule | the answers | each point: unrecovered, corrected or contained |

A point whose mode was added in its own batch is marked, so "fitted an existing mode" can be counted.

## Label mapping

Checks a taxonomy against failures humans marked: for each marked step, does the failure fit one of its modes?
Needs a labels file (one item per human label: the task, the step before the marked one, the marked step,
and the annotator's reason); the dataset's converter writes it.

| step | does | input | output |
|---|---|---|---|
| Map (one call per label, W in parallel) | checks the annotator's reason against the step text; decides whether it is a wrong action by the agent at that step (AGENT) or only a tool, environment or outcome problem (NOT_AGENT); for AGENT gives the one mode that fits, or NONE with what kind of failure it is | the taxonomy without instances; one label item | verdict, mode, what went wrong, why |
| Map with `--as-given` (instead of the above) | takes the label as a failure, as the annotator says; gives the one mode that fits, or NONE with what kind of failure it is | the taxonomy without instances; one label item | mode, what went wrong, why |
| Summary (no model call) | counts verdicts and modes; coverage = share of failures (AGENT items, or every item with `--as-given`) with a mode; with a judge run on the same traces, compares the mode with the judge's modes at the marked step | the mapped items; optionally the judge's points | coverage, the NONE items, agreement with the judge |

## Automatic checks (no model call)

- Steps that change an existing taxonomy (consolidation, merge, refinement, adding judge modes) reply with their edits
  only: merges, rewrites and, for refinement, added modes. The edits are applied in code, so a mode
  not mentioned is unchanged and instances are never rewritten by the model. Mode ids stay stable:
  a merged mode keeps one member's id, and new modes get the next free id. Every mode refinement
  touches carries a `refinement` entry: round, change, why.
- Each quote appears verbatim in its trace, ignoring whitespace and escape characters.
- Every instance is accounted for after abstraction and consolidation.
- A split is applied only if every part has instances, no instance is in two parts, and every
  instance is in a part.

## Prompts

Every prompt is shared blocks, then the step's own prompt, separated by a line of 70 `=`.
`00_concepts.md` goes before every prompt; `00_mode_rules.md` goes before every prompt that
works with modes (all except field analysis, observation, discovery, reconciliation and label mapping).

| step | prompt |
|---|---|
| Field analysis | `01_field_analysis.md` |
| Observation, Discovery | `02_observation.md` |
| Abstraction | `03_abstraction.md` |
| Consolidation, Merge | `04_consolidation.md` |
| Reconciliation | `05b_reconcile.md` |
| Assignment | `05c_assign.md` |
| Discussion | `05d_discuss.md` |
| Refinement | `06_refinement.md` |
| Gap | `07_gap.md` |
| Final validation | as segment 1 |
| Split | `08_split.md` |
| Judge | `judge.md`; `judge_fixed.md` with `--no-new-modes` |
| Add modes | `judge_new_modes.md` |
| Label mapping | `map_labels.md`; `map_labels_given.md` with `--as-given` |
| Concepts, answer-provided variant | the last section of `00_concepts.md` replaced by `00_traces_answer_provided.md` |

## Run

Input: a directory with `sample/` (the N traces) and `validation/` (F·M more), one JSON file per trace:
`{"trace_id": "...", "messages": [{"role": "system" | "user" | "assistant", "content": "..."}]}`.
The traces carry no outcome labels, and all come from the same agent system.

```bash
python3 run.py --data <data dir> --out <run dir> --dry-run
python3 run.py --data <data dir> --model <provider/model> --out <run dir>
```

The run writes `final_taxonomy.json` with every mode, and `final_taxonomy_evidence.json` without the
modes tagged `gap: possible`, for use when only evidence-backed modes are wanted. The judge's summary
lists how many points each possible mode received.

`--variant NAME` runs a variant beside an existing run in the same folder: every file it writes gets the
suffix `_NAME` (e.g. `final_taxonomy_NAME.json`), and a saved reply of the original run is reused only
where the prompt is identical, so nothing of the original run is overwritten.

`--answers <answers.json>` (`{trace_id: correct final answer}`) runs the answer-provided variant: every
trace shows its correct final answer at the top, and the last section of `00_concepts.md` (no outcome is
shown) is replaced by `00_traces_answer_provided.md`, which says how to use it. The suffix defaults to
`answer_provided` (`final_taxonomy_answer_provided.json`). `judge.py --answers` does the same for the judge.
The default pipeline never sees an answer.

The dry run makes no model calls; it prints the number of calls and input tokens per step.
Rerunning the same command resumes an interrupted run. Variables are flags: `--annotators` (K),
`--rounds` (R), `--traces-per-round` (M), `--quorum` (Q), `--discussion-rounds` (D),
`--kappa-target` (κ*), `--coverage-target` (c*), `--split-min` (S). `--context-tokens` is the
model's context window (default 1M); traces are split only when they do not fit it.
`--max-output` caps each reply, thinking included (default 32,768 tokens).

Every call attempt is logged to `call_log.jsonl` in the run dir (finish reason, token counts, the billed cost the
provider reports with the reply, requests that got no reply, warnings),
and the run ends by writing `call_report.txt`: per step, the replies kept, the failed attempts by kind
(no reply, cut off at the output limit, not JSON, malformed) and the largest share of the output limit a
kept reply used. `call_report.py <run dir>` prints the same for any run, older ones included; for those,
the kind of a failed attempt is read from its saved text.

Two-pass test (`judge_blind.py`): per trace, (1) find every failure without the taxonomy, with the observation
prompt and the run's field analysis; (2) with the taxonomy (no instances), decide for each candidate whether it is a
failure and give it a mode or NONE (`judge_verify.md`). Coverage is the share of confirmed failures with a mode.

Judge, then recovery:

```bash
python3 judge.py --taxonomy <run dir>/final_taxonomy.json --traces <traces dir> --model <provider/model> --out <judge dir>
python3 -m recovery.run --traces <traces dir> --mapping <judge dir> --out <recovery dir>
```

Keys: `ARENA_API_KEY` (for `arena/...`), `OPENROUTER_API_KEY` (for `openrouter/...`), or `GEMINI_API_KEY`.

## Not in this pipeline

Columns, consequence pathways, retiring modes, the "constant" rule, per-agent applicability, a
separate conformance pass, and AdaMAST's A/B/C typing.
