# Experimental setup

## The candidates

Twelve variants of the same three-hop retrieval agent, evolved by
[GEPA](https://github.com/gepa-ai/gepa) from a common DSPy program over a BM25
index of Wikipedia abstracts. They differ only in their prompts: the
instructions given to the summariser and query-generator components. The
architecture, the retriever, and the number of hops are identical across all
twelve.

This matters for interpretation. The candidates are close relatives, not
different systems. Their true quality spans 0.48 to 0.64 on the held-out
tasks, which is a narrow field, and separating them is correspondingly hard.

Each candidate is a pipeline of three components run over three hops:

1. a **query generator** proposes what to retrieve next,
2. the **retriever** returns Wikipedia abstracts (fixed, not part of any candidate),
3. an **evidence summariser** condenses what was found and states what remains missing.

## The data split

| | tasks | runs per candidate | used for |
| --- | :-: | :-: | --- |
| evidence set | 50 | 5 (repeats 0 to 4) | repeat 0 is the trace evidence that scoring reads |
| held-out set | 250 | 1 (repeat 0) | validation only, never touched by scoring |

The split is deliberately asymmetric, because it has to support two different
questions:

- **Does the ranking survive re-running the same tasks?** Repeats 1 to 4 of the
  evidence tasks answer this. Scoring sees only repeat 0, so the other four
  executions are genuinely unseen.
- **Does the ranking transfer to different tasks?** The 250 held-out tasks
  answer this. No scoring path touches them at all.

Both questions matter and they are not the same question, which the results
bear out: the configurations that win on one do not always win on the other.

All twelve candidates were run on exactly the same tasks, so no candidate has
an evidence advantage.

## The trace judge

Every repeat-0 execution of the 50 evidence tasks was read by an automated
judge: 12 candidates times 50 tasks = **600 traces**.

- **Model:** Claude Sonnet 4.6, two passes per trace. The first pass finds
  concrete failure points with quoted evidence from the trace; the second maps
  each to the taxonomy, checking each candidate code's applicability conditions.
- **Input:** the complete untruncated trace, the task, the fixed architecture
  description, and an access manifest stating exactly which information each
  component could see at each step. The last item is what makes role-specific
  judgments checkable: a summariser cannot be blamed for missing something that
  was never in its input.
- **Blindness:** the judge never sees the answer key, the evaluator's score, or
  which candidate produced the trace. It sees a trace and judges the process.
- **Output:** 2,009 failure points across the 600 traces. Each carries the
  taxonomy code, an evidence quote, a severity, and the judge's own rating of
  whether that failure plausibly reached the final answer.

That last field, the judge's self-assessment of consequence, turns out to be
the single most useful signal in the package. See `../pipeline/MODULES.md`.

The judge is an instrument, not the contribution. It is imperfect, and
knowingly so: it over-reports, flagging process imperfections that did not
matter. Part of the scoring pipeline's job is to be robust to that.

## The taxonomy

`taxonomy_v9.json`, 24 codes in three families. Frozen before the judging run
and unchanged since.

**A, system and execution (8 codes)** — failures visible without domain
knowledge: `A.1` input access or parsing, `A.2` output contract violation,
`A.3` output truncation, `A.4` no usable output, `A.5` required workflow action
missing, `A.6` repetition prevents progress, `A.7` handoff information loss,
`A.8` pipeline objective remains unresolved.

**B, role-specific (7 codes)** — failures attributable to one component given
what it could actually see: `B.1` summariser omits relevant evidence, `B.2`
fabricates or misattributes evidence, `B.3` misreads evidence content, `B.4`
fails to make an evidence gap actionable, `B.5` fails to synthesise across
sources; `B.6` query targets a wrong or already-settled need, `B.7` query
presupposes an unverified fact.

**C, domain reasoning (9 codes)** — failures in the multi-hop reasoning itself:
`C.1` claim requirement misparsed, `C.2` entity or reference resolution error,
`C.3` relation, attribute or temporal misattribution, `C.4` multi-hop chain
construction error, `C.5` comparison evidence incomplete, `C.6` comparative
conclusion error, `C.7` evidence sufficiency or absence error, `C.8`
contradiction reasoning error, `C.9` unsupported logical inference.

Nineteen of the 24 codes actually fire in this data. The distribution is
head-heavy: `A.8` appears on 434 of the 600 traces and `B.6` on 299, while nine
codes appear fewer than 25 times in total.

The taxonomy is declared outcome-blind and candidate-identity-blind: no code
can be assigned by knowing whether the task succeeded or which system ran.

## What the scoring pipeline actually consumes

`judge_mapping.json`, the judge's findings in portable form:

```json
{"schema_version": 1, "benchmark": "hover-adapter15",
 "candidates": {"0": {"<task_id>": [{"code": "B.6", "severity": "moderate",
                                     "outcome_link": "direct", ...}]}}}
```

Candidate, then task, then a list of failure records. Only `code` is required;
every other field rides along for modules that want it. **The pipeline does not
read the taxonomy file** — it reads codes as opaque labels. The taxonomy is
shipped so a human can decode them, and is used programmatically only by the
optional coarsening step that collapses codes to their A, B or C family.

This is what makes the pipeline portable: point it at a different benchmark's
judge output in the same format and it runs unchanged.
