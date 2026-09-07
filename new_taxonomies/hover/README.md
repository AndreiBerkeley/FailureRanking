# tax-18 — 18 failure modes for the HoVer program

Eighteen failure modes obtained by splitting `tax-7`. Five of its seven codes
were found to carry more than one mechanism and were split into parts; two were
kept whole. A split was accepted only when its parts occur independently in the
data: if every trace showing one part also showed the others, they were one
mechanism described several ways and the split was refused. Parts keep their
parent's column. The ids are a fresh namespace (`SP_`) so a result under this
taxonomy can never be silently compared with one under `tax-7`.

Counts: 7 parent codes, 5 split, 2 kept, 18 codes.
The gap test that supplied the records is in `../runs/taxgen-2/`, the split
decisions in `../runs/taxgen-3/`.

| id | column | name | definition | split from (tax-7 code) |
|---|---|---|---|---|
| `SP_01` | general | CONVERSATIONAL_OR_NATURAL_LANGUAGE_QUERY | The agent formulates a search query as a conversational natural language question or narrative statement (e.g., 'Who directed...', 'Did X form a band...') rather than constructing a dense, keyword-rich search string. | DISALLOWED_QUERY_SYNTAX_OR_STYLE |
| `SP_02` | general | DISALLOWED_QUERY_SYNTAX_OPERATORS | The agent includes forbidden syntax, operators, or punctuation in the search query field, such as quotation marks, explicit Boolean operators (AND, OR), or advanced search syntax, violating explicit query formatting cons | DISALLOWED_QUERY_SYNTAX_OR_STYLE |
| `SP_03` | domain | REASONING_PARAMETRIC_KNOWLEDGE_INJECTION | The agent invokes external parametric memory or introduces invented/unverified facts, entities, titles, or dates during reasoning, deduction, or summary evaluation to fill factual gaps or verify claims, violating constra | UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJECTION |
| `SP_04` | domain | QUERY_SEARCH_TERM_INJECTION | The agent introduces ungrounded external world knowledge, unverified entities, or unauthorized search terms into a generated query string, violating constraints that mandate deriving query concepts strictly from the prov | UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJECTION |
| `SP_05` | domain | HALLUCINATED_RETRIEVED_DOCUMENT_ACCOUNTING | The agent explicitly lists document titles under structured tracking fields (such as 'Retrieved required evidence documents') that were never actually present in the retrieved passage context. | UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJECTION |
| `SP_06` | general | MISSING_TERMINAL_COMPLETION_MARKER | The model fails to output a required system boundary or terminal signal (such as `[[ ## completed ## ]]` or an explicit end marker) at the termination of its response. | MISSING_REQUIRED_OUTPUT_FIELD_OR_MARKER |
| `SP_07` | general | OMITTED_EVIDENCE_CATEGORIZATION_SECTION | The model fails to output mandatory explicit evidence lists or section headers (e.g., 'Retrieved required evidence documents' or 'Missing required evidence documents') in its reasoning or summary fields. | MISSING_REQUIRED_OUTPUT_FIELD_OR_MARKER |
| `SP_08` | general | OMITTED_MULTI_HOP_REASONING_MAP | The model fails to map out the required multi-step/multi-hop verification chain in its reasoning field. | MISSING_REQUIRED_OUTPUT_FIELD_OR_MARKER |
| `SP_09` | domain | PREMATURE_EVIDENCE_COMPLETION_IN_REASONING | The model determines during reasoning or evidence evaluation that no further evidence documents are missing or required, or asserts that passages lack information without using internal knowledge to deduce missing bridge | PREMATURE_RETRIEVAL_TERMINATION_OR_REFUSAL |
| `SP_10` | domain | NULL_OR_TERMINATION_TOKEN_QUERY_EMISSION | The model emits a concise null or refusal token ('None', 'N/A', 'None required', 'None needed') in the search query field instead of formulating an active keyword query required to retrieve missing evidence. | PREMATURE_RETRIEVAL_TERMINATION_OR_REFUSAL |
| `SP_11` | domain | CONVERSATIONAL_EXPLANATION_IN_QUERY_FIELD | The model populates the search query field with conversational text, commentary, or meta-text explanatory sentences (e.g., 'No query needed; the claim is verified by the provided summaries.') instead of formulating searc | PREMATURE_RETRIEVAL_TERMINATION_OR_REFUSAL |
| `SP_12` | domain | FALSE_PREMISE_RULE_MISAPPLICATION_ON_VERIFIED_CLAIM | The model outputs 'none' in the search query field because the claim was confirmed or verified as true in reasoning, violating the explicit prompt instruction that 'none' should only be emitted when a claim is thoroughly | PREMATURE_RETRIEVAL_TERMINATION_OR_REFUSAL |
| `SP_13` | domain | PASSAGE_TEXT_MISCONSTRUCTION_OR_HALLUCINATION | The program misinterprets, misreads, or hallucinates statements, entities, or grammatical relationships directly within the provided text passages or claim text. | EVIDENCE_MISCONSTRUCTION_OR_LOGICAL_FALLACY |
| `SP_14` | domain | INVALID_VERDICT_LOGICAL_INFERENCE | The program draws a logically sound-defying truth verdict from the current evidence state, such as equating missing evidence with proof of falsity, declaring a claim supported despite acknowledging unverified elements, o | EVIDENCE_MISCONSTRUCTION_OR_LOGICAL_FALLACY |
| `SP_15` | domain | RETRIEVAL_STATE_AND_EVIDENCE_MISTRACKING | The program fails to accurately track whether required evidence documents are retrieved, missing, or already verified in prior hops/context. | EVIDENCE_MISCONSTRUCTION_OR_LOGICAL_FALLACY |
| `SP_16` | domain | UNMAPPED_REASONING_TRAJECTORY | The program fails to structure or map out required multi-hop verification steps or mandatory trajectory steps within its reasoning field. | EVIDENCE_MISCONSTRUCTION_OR_LOGICAL_FALLACY |
| `SP_17` | general | MALFORMED_STRUCTURED_LIST_OR_SORTING_DEFECT | The agent produces structured list elements that violate specific formatting rules—such as failing to sort document titles strictly alphabetically, using plain-text prose instead of bracketed arrays, using non-standard k |  |
| `SP_18` | general | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | The agent drops key entities, essential claim details, or required context constraints from the input text when constructing the search query, emitting an over-truncated or under-constrained query string. |  |

`taxonomy.json` is the file the judge is pointed at, copied verbatim. Each code
carries a full definition, when to use it, when not to, and the evidence it
rests on.
