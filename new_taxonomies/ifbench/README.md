# tax-1 — 13 failure modes for the ifbench program

Generated on 2026-09-07 by `new_pipeline` from the `pools-1` taxonomy pool: 6 general
and 7 domain codes. The draft came from stages 1–6 of `GENERATION_v2.md` on
120 traces over 30 tasks; one refinement round
rewrote it against the judge's reading of 60 traces on 30 other tasks;
the interannotation gate measured draft and result on 60 traces of 30 further tasks
with four readers and the open reader; the gap test read 40 fresh traces. No outcome
was in view at any stage; outcomes were used only to compose the corpora.

Refinement verdicts: {"keep": 9, "edit": 1}. Granularity: {"examined": 3, "left_alone": {"output_conformance_and_structural_constraint_violation": 4, "incorrect_textual_audit_or_counting_evaluation_during_reasoning": 3, "unauthorized_constraint_import_from_system_context": 1, "verbatim_repetition_target_span_truncation_during_intake": 1}}.
Gap test: 35 findings, verdicts {"covered": 35}, fitness {"median": 95, "min": 90, "max": 100, "below_good": 0, "below_loose": 0}.

| gate | codes | pooled kappa | coverage | traces judged | result |
|---|---:|---:|---:|---:|---|
| baseline | 10 | 0.832 | 0.952 | 55 | pass |
| round_1 | 12 | 0.876 | 0.975 | 50 | pass |

The full run record, with every prompt, raw model output, judge record and gate file, is in
`../runs/new_pipeline-run-1/`. Ids are the `SP_` namespace assigned when the granularity splits were applied,
with the refinement round's `R1_` ids and the draft's ids recorded in `taxonomy.json` provenance.

| id | column | name | definition |
|---|---|---|---|
| `SP_01` | general | unauthorized_constraint_import_from_system_context | During query intake and instruction parsing, the agent incorporates constraints or formatting requirements from example text or general system instructions that are not present in the user's explicit query. |
| `SP_02` | general | verbatim_repetition_target_span_truncation_during_intake | During query intake and constraint parsing, the agent misidentifies the boundary of the required repetition text, truncating preceding context lines or command prefixes from the segment to be repeated verbatim. |
| `SP_03` | general | preamble_and_wrapper_symbol_injection_before_verbatim_text | When forming and emitting the final response, the agent inserts unauthorized preamble symbols, quotation marks, or list markers immediately preceding or wrapping a verbatim repeated text segment. |
| `SP_04` | general | verbatim_repetition_text_omission | The model fails to output a complete verbatim block by omitting required sentences, clauses, or the entire repeated query segment. |
| `SP_05` | general | verbatim_repetition_text_modification | The model attempts to repeat the text but alters its surface representation through casing changes, symbol substitutions, formatting alterations, or language translation. |
| `SP_06` | general | output_conformance_and_structural_constraint_violation | The agent produces output that breaches explicit structural, length, envelope, or formatting rules, such as paragraph/sentence counts, JSON formatting requirements, outer quote wrappers, or required section content. |
| `SP_07` | domain | incorrect_textual_audit_or_counting_evaluation_during_reasoning | In the middle of execution, while performing working steps, the agent computes an incorrect count or evaluation of words, sentences, character occurrences, or structural elements when auditing draft material. |
| `SP_08` | domain | inconsistent_state_assertion_between_reasoning_and_output | During intermediate analytical reasoning, the agent makes a false factual assertion about the state, language, or content of the generated text that directly contradicts the actual state of the output. |
| `SP_09` | domain | unintentional_removal_of_required_code_components_during_refactoring | During programmatic refactoring or code synthesis steps, the agent unintentionally drops essential class methods or domain functionality required by the task specifications. |
| `SP_10` | domain | linguistic_declension_and_grammatical_inflection_error | During non-English text composition or translation work, the agent generates grammatically incorrect case inflection or modifier-noun agreement errors. |
| `SP_11` | domain | whitespace_and_microformatting_alteration_during_string_processing | In the middle of performing verbatim text processing or formatting work, the agent alters micro-formatting elements such as replacing double spaces with single spaces. |
| `SP_12` | domain | mathematical_calculation_or_algebraic_derivation_error | During intermediate mathematical reasoning or problem solving, the agent makes an arithmetic mistake, invalid algebraic step, or incorrect numerical calculation when deriving a result. |
| `SP_13` | domain | generation_of_invalid_programming_language_syntax | During code generation, refactoring, or string construction, the agent produces or introduces code containing invalid programming language syntax, such as missing commas between function arguments. |
