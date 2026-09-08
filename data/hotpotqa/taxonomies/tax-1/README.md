# tax-1 — 7 failure modes for the hotpotqa program

Generated on 2026-09-07 by `new_pipeline` from the `pools-1` taxonomy pool: 3 general
and 4 domain codes. The draft came from stages 1–6 of `GENERATION_v2.md` on
120 traces over 30 tasks; one refinement round
rewrote it against the judge's reading of 60 traces on 30 other tasks;
the interannotation gate measured draft and result on 60 traces of 30 further tasks
with four readers and the open reader; the gap test read 40 fresh traces. No outcome
was in view at any stage; outcomes were used only to compose the corpora.

Refinement verdicts: {"edit": 1, "keep": 5}. Granularity: {"examined": 1, "left_alone": {"False Factual Assertion in Reasoning": 3, "Ungrounded External Knowledge Import": 5}}.
Gap test: 14 findings, verdicts {"covered": 14}, fitness {"median": 95, "min": 80, "max": 100, "below_good": 0, "below_loose": 0}.

| gate | codes | pooled kappa | coverage | traces judged | result |
|---|---:|---:|---:|---:|---|
| baseline | 6 | 0.784 | 0.697 | 55 | fail |
| round_1 | 7 | 0.863 | 0.795 | 60 | pass |

The full run record, with every prompt, raw model output, judge record and gate file, is in
`../runs/new_pipeline-run-1/`. Ids are the `SP_` namespace assigned when the granularity splits were applied,
with the refinement round's `R1_` ids and the draft's ids recorded in `taxonomy.json` provenance.

| id | column | name | definition |
|---|---|---|---|
| `SP_01` | general | Output Format Non-Conformance | An agent emits an output that fails to follow required structural, markup, or formatting specifications at the edge of execution, such as using invalid section headers, omitting mandatory syntax, or using non-conforming  |
| `SP_02` | general | Output Payload Type Mismatch | An agent emits a conversational comment, declarative explanation, or full answer statement at output emission instead of the contracted output payload type (such as a targeted search query). |
| `SP_03` | general | Irrelevant Passage Intake Inclusion | An agent fails to filter out distractor or irrelevant documents during input intake and includes facts about unrelated subjects in its output summary. |
| `SP_04` | domain | Ungrounded External Knowledge Import | During task execution, an agent imports ungrounded external domain knowledge to supply missing facts rather than strictly grounding its work on the provided input evidence. |
| `SP_05` | domain | Entity Selection Contradicting Explicit Constraints | An agent selects a target entity as the final answer despite explicitly identifying in its own intermediate reasoning that the candidate entity violates one or more query constraints. |
| `SP_06` | domain | False Factual Assertion in Reasoning | An agent asserts incorrect biographical, historical, or organizational facts during intermediate reasoning, or fabricates non-existent relationships to reconcile conflicting prompt constraints. |
| `SP_07` | domain | Redundant Query Generation for Existing Facts | An agent generates a search query targeting facts, attributes, or entities that were already explicitly present in the input summary or context, failing to recognize that the required information was already established. |
