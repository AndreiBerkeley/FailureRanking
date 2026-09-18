# tax-15-pool3 — tax-13 plus two hand-authored codes (GEPA candidate set)

Made 2026-09-17. `tax-13`'s 13 codes byte-identical, plus `SP_14` and `SP_15`, written by hand from
the 170 points the tax-13 judge on the GEPA 50 (`runs/new_pipeline/hover/pointjudge-1`) kept but
could not name — 138 of them unrecovered, 16% of that run's unrecovered evidence. Read by hand they
are two mechanisms: a query issued for a known required page that retrieval does not return
(over-constrained, bundled, too broad), and a summary that leaves a required document unidentified.
The nearest existing code, `SP_08`, is the *omission* of the target from the query; these queries
include it and still miss. The suffix on the id is because `tax-15` (models-1) already holds the count.

`assignments.json` maps the uncoded points by turn kind — query turns → SP_14 (132),
summary turns → SP_15 (31) — with 7 set aside by hand (instruction-compliance
items, one empty, three that are neither mechanism). No re-judge: `scripts/assign_uncoded_pool3.py`
applies them to the mapping and its recovery run. The rates of SP_14/SP_15 are therefore the
decider's "nothing fits" points, not a judge pass with these codes in view; a pass with them in
view would also catch instances the decider filed under neighbouring codes.

| id | column | name | definition |
|---|---|---|---|
| `SP_01` | domain | Misinterpretation of Claim Semantics | The agent misinterprets the grammatical structure or semantic relationships of a claim, treating descriptive modifiers or relative clauses as direct identity assertions or false equivalences. |
| `SP_02` | domain | Reliance on Ungrounded External Knowledge | The agent introduces facts, entity attributes, or historical assertions from parametric memory that are completely absent from the provided context or retrieved passages when performing passage-ground |
| `SP_03` | domain | False Attribution of Claims to Input Passages | The agent explicitly attributes a factual claim or entity relationship to a specific retrieved passage that does not contain or support that statement. |
| `SP_04` | domain | Premature Retrieval Loop Termination | The agent incorrectly determines that no further context retrieval is necessary and outputs a non-query string indicating completion (such as 'None required' or 'Not applicable') instead of generating |
| `SP_05` | domain | Unsound Deductive Reasoning from Context | The agent draws invalid logical conclusions, accepts unevidenced premises, or makes false assertions about context contents (such as claiming evidence is missing or unique when it is not) during evalu |
| `SP_06` | domain | Misclassification of Evidence Document Status | The agent misclassifies required evidence documents, listing absent documents as retrieved, or declaring that no documents are missing when essential entity documents remain unretrieved. |
| `SP_07` | domain | Failure to Carry Forward Verified Facts Across Turns | The agent discards or ignores established entities, verified context facts, or prior findings from previous turns during multi-hop synthesis or query formulation. |
| `SP_08` | domain | Omission of Target Entities in Search Query | The agent identifies or deduces specific required bridge entities or missing concepts during reasoning, but omits them from the generated search query string or substitutes generic descriptors. |
| `SP_09` | general | Omission of Mandatory Output Completion Marker | The agent emits an output that omits a required terminal completion marker specified by its instructions. |
| `SP_10` | general | Omission of Required Output Sections or Headers | The agent emits an output that fails to include required structural fields, headers, or section labels required by its instructions. |
| `SP_11` | general | Invalid Search Query Generation | The agent produces a search query string that is malformed or unsearchable, such as wrapping a full natural language sentence in quotation marks or outputting placeholder/conversational text ('None',  |
| `SP_12` | general | Entity List Cardinality Constraint Violation | The agent outputs a list of entity or document titles whose total count violates explicit instructions requiring an exact number of items. |
| `SP_13` | general | Non-Compliance with Required Element Formatting Rules | The agent produces output elements or values whose string casing, title normalization, or structural ordering fails to follow specific formatting rules required by its instructions. |
| `SP_14` | domain | Required Page Not Retrieved by a Targeted Query | The agent issues a search query for a required page whose identity it knows or could take from its context, and the retrieval does not return that page's own document: the query bundles the target wit |
| `SP_15` | domain | Required Document Left Unidentified in Summary | The summary does not resolve a required evidence document to its exact title: it leaves a placeholder or generic description in place of the entity, omits it from the list of missing documents, or des |
