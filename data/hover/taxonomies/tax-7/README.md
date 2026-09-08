# tax-7 — 7 failure modes for the HoVer program

Seven failure modes induced from the traces of `cap-1` by the taxonomy
generator, with no result of any run in view. A *column* says where in the
program the mistake belongs: `general` failures can occur in any module,
`domain` failures are specific to what this program does. Every code names an
action of the candidate, not a topic of the task.

The generator read a fixed sample of 300 traces from `cap-1`, drawn
task-first so that the vocabulary is bounded by task diversity rather than by
trace count: 100 distinct tasks, all 300 traces
verified present in `cap-1` by id; the list is
`../runs/taxgen-1/induction_sample_trace_ids.txt`. Its stage outputs, prompts,
raw responses and log are in `../runs/taxgen-1/`.

| id | column | name | definition |
|---|---|---|---|
| `FM_001` | general | DISALLOWED_QUERY_SYNTAX_OR_STYLE | The agent includes prohibited formatting elements in emitted search queries, such as quotation marks, complex Boolean operators (AND, OR), conversational question phrasing, or full web URLs, violating explicit input-outp |
| `FM_002` | domain | UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJECTION | The agent invokes external parametric knowledge or invents non-present facts, names, years, or titles during reasoning, query generation, or summary creation, violating constraints against external knowledge hallucinatio |
| `FM_003` | general | MISSING_REQUIRED_OUTPUT_FIELD_OR_MARKER | The agent fails to include mandatory structural fields, section headers, or required system completion markers (e.g., [[ ## completed ## ]] or explicit evidence categorization blocks) when emitting its output. |
| `FM_004` | domain | PREMATURE_RETRIEVAL_TERMINATION_OR_REFUSAL | The agent decides during reasoning that retrieval is complete or unnecessary, emitting 'None', 'None required', 'N/A', or refusal commentary instead of forming a query, breaking the required multi-hop document retrieval  |
| `FM_005` | domain | EVIDENCE_MISCONSTRUCTION_OR_LOGICAL_FALLACY | The agent makes logical errors during evidence analysis—such as treating absent evidence as proof of falsity (argument from ignorance), misinterpreting coreferences/superlatives, hallucinating what a retrieved document s |
| `FM_006` | general | MALFORMED_STRUCTURED_LIST_OR_SORTING_DEFECT | The agent produces structured list elements that violate specific formatting rules—such as failing to sort document titles strictly alphabetically, using plain-text prose instead of bracketed arrays, using non-standard k |
| `FM_007` | general | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | The agent drops key entities, essential claim details, or required context constraints from the input text when constructing the search query, emitting an over-truncated or under-constrained query string. |

`taxonomy.json` is the file the judge is pointed at, copied verbatim. Each code
carries a full definition, when to use it, when not to, and the evidence it
rests on.
