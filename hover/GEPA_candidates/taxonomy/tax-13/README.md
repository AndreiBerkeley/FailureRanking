# tax-13 — 13 failure modes for the hover program

Generated on 2026-09-17 by `new_pipeline` from the taxonomy pool `runs/new_pipeline/hover/pool_taxonomy`: 5 general
and 8 domain codes. The draft came from stages 1–6 of `GENERATION_v3.md` on
160 traces over 40 tasks; one refinement round
rewrote it against the judge's reading of 160 traces on 40 other tasks;
the interannotation gate measured draft and result on 60 traces of 15 further tasks
with four readers and the open reader; the gap test read 50 fresh traces. No outcome
was in view at any stage; outcomes were used only to compose the corpora.

Refinement verdicts: {"keep": 8, "edit": 3}. Granularity: {"examined": 6, "left_alone": {"Failure to Carry Forward Verified Facts Across Turns": 3, "Omission of Target Entities in Search Query": 1, "Misclassification of Evidence Document Status": 2}}.
Gap test: 55 findings, verdicts {"covered": 55}, fitness {"median": 95, "min": 85, "max": 100, "below_good": 0, "below_loose": 0}.

Under `GENERATION_v3.md`: codes the blind reader corroborated under 0.30 at the final gate are retired (none this run); gap-test findings no code fits well become proposals and survivors are admitted (this run: {"proposed": 0, "surviving_stage6": 0, "too_few": 0}). No hand codes.

| gate | codes | pooled kappa | coverage | traces judged | result |
|---|---:|---:|---:|---:|---|
| baseline | 11 | 0.656 | 0.975 | 60 | fail |
| round_1 | 11 | 0.622 | 0.985 | 60 | fail |

The full run record, with every prompt, raw model output, judge record and gate file, is in
`../runs/new_pipeline-pool3-v3-1/`. Ids are the `SP_` namespace assigned when the granularity splits were applied,
with the refinement round's `R1_` ids and the draft's ids recorded in `taxonomy.json` provenance.

| id | column | name | definition |
|---|---|---|---|
| `SP_01` | domain | Misinterpretation of Claim Semantics | The agent misinterprets the grammatical structure or semantic relationships of a claim, treating descriptive modifiers or relative clauses as direct identity assertions or false equivalences. |
| `SP_02` | domain | Reliance on Ungrounded External Knowledge | The agent introduces facts, entity attributes, or historical assertions from parametric memory that are completely absent from the provided context or retrieved passages when performing passage-grounded verification. |
| `SP_03` | domain | False Attribution of Claims to Input Passages | The agent explicitly attributes a factual claim or entity relationship to a specific retrieved passage that does not contain or support that statement. |
| `SP_04` | domain | Premature Retrieval Loop Termination | The agent incorrectly determines that no further context retrieval is necessary and outputs a non-query string indicating completion (such as 'None required' or 'Not applicable') instead of generating the required search |
| `SP_05` | domain | Unsound Deductive Reasoning from Context | The agent draws invalid logical conclusions, accepts unevidenced premises, or makes false assertions about context contents (such as claiming evidence is missing or unique when it is not) during evaluation. |
| `SP_06` | domain | Misclassification of Evidence Document Status | The agent misclassifies required evidence documents, listing absent documents as retrieved, or declaring that no documents are missing when essential entity documents remain unretrieved. |
| `SP_07` | domain | Failure to Carry Forward Verified Facts Across Turns | The agent discards or ignores established entities, verified context facts, or prior findings from previous turns during multi-hop synthesis or query formulation. |
| `SP_08` | domain | Omission of Target Entities in Search Query | The agent identifies or deduces specific required bridge entities or missing concepts during reasoning, but omits them from the generated search query string or substitutes generic descriptors. |
| `SP_09` | general | Omission of Mandatory Output Completion Marker | The agent emits an output that omits a required terminal completion marker specified by its instructions. |
| `SP_10` | general | Omission of Required Output Sections or Headers | The agent emits an output that fails to include required structural fields, headers, or section labels required by its instructions. |
| `SP_11` | general | Invalid Search Query Generation | The agent produces a search query string that is malformed or unsearchable, such as wrapping a full natural language sentence in quotation marks or outputting placeholder/conversational text ('None', 'None required...')  |
| `SP_12` | general | Entity List Cardinality Constraint Violation | The agent outputs a list of entity or document titles whose total count violates explicit instructions requiring an exact number of items. |
| `SP_13` | general | Non-Compliance with Required Element Formatting Rules | The agent produces output elements or values whose string casing, title normalization, or structural ordering fails to follow specific formatting rules required by its instructions. |
