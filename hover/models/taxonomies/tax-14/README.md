# tax-14 — 14 failure modes for the hover program (models-1)

Induced from the `models-1` candidate set: nine solver models running one fixed instruction
set (cand-019's four one-line docstrings), so every candidate has an identical contract and
any difference in failures is the model.

Generated on 2026-09-09 by `new_pipeline` from the `pools-1` taxonomy pool: 6 general
and 8 domain codes. The draft came from stages 1–6 of `GENERATION_v2.md` on
160 traces over 40 tasks; one refinement round
rewrote it against the judge's reading of 160 traces on 40 other tasks;
the interannotation gate measured draft and result on 60 traces of 15 further tasks
with four readers and the open reader; the gap test read 50 fresh traces. No outcome
was in view at any stage; outcomes were used only to compose the corpora.

Refinement verdicts: {"keep": 3, "edit": 5}. Granularity: {"examined": 9, "left_alone": {"PREMATURE_TASK_EXECUTION_HALTING": 1}}.
Gap test: 441 findings, verdicts {"stretch": 82, "loose": 154, "covered": 110, "uncovered": 95}, fitness {"median": 60, "min": 0, "max": 96, "below_good": 298, "below_loose": 144}.

| gate | codes | pooled kappa | coverage | traces judged | result |
|---|---:|---:|---:|---:|---|
| baseline | 8 | 0.514 | 0.735 | 60 | fail |
| round_1 | 8 | 0.565 | 0.857 | 60 | fail |
| round_2 | 10 | 0.557 | 0.877 | 60 | fail |

The full run record, with every prompt, raw model output, judge record and gate file, is in
`../runs/new_pipeline-models-1/`. Ids are the `SP_` namespace assigned when the granularity splits were applied,
with the refinement round's `R1_` ids and the draft's ids recorded in `taxonomy.json` provenance.

| id | column | name | definition |
|---|---|---|---|
| `SP_01` | domain | UNGROUNDED_EXTERNAL_KNOWLEDGE_INCLUSION | The agent introduces external facts, entities, dates, or assertions that are not present in the supplied input passages or context during reasoning or summary generation. |
| `SP_02` | domain | MISREADING_OR_MISINTERPRETING_INPUT_MATERIAL | The agent misinterprets, reverses, or distorts factual statements, relationships, negations, or entities explicitly supplied in the input material. |
| `SP_03` | general | FUNCTIONAL_OUTPUT_TYPE_MISMATCH | The agent populates an output field with content whose functional or semantic type fails to match the designated role for that execution step (e.g., placing verdict labels, status statements, booleans, or meta-evaluation |
| `SP_04` | general | OUTPUT_SCHEMA_DELIMITER_MISMATCH | The agent emits its output in a structural container the execution harness cannot parse — a JSON object with invented keys, a language-native dictionary, or prose where the harness expects its delimited field blocks — so |
| `SP_05` | domain | REDUNDANT_NEXT_HOP_QUERY_GENERATION | The agent constructs search queries that repeat facts, entities, or relationships already established in earlier retrieval hops, or copies full claim text and prior reasoning into the query field instead of isolating the |
| `SP_06` | domain | META_OR_EVALUATIVE_QUERY_GENERATION | The agent formulates queries that ask meta-level, evaluative, or rhetorical questions (e.g., asking whether summaries agree, asking if a claim is true, or asking for explanations) rather than generating an information-re |
| `SP_07` | domain | FLAWED_PREMISE_OR_MISCONSTRAINED_QUERY_GENERATION | The agent constructs search queries that bake in unverified or hallucinated premises, target incorrect entities, or omit necessary search constraints needed to retrieve the missing evidence. |
| `SP_08` | general | UNREQUESTED_CONTAINER_OR_WRAPPER_STRUCTURE | The agent emits output enclosed within an unrequested data container or wrapper, such as a dictionary or object schema, rather than following the top-level structural format required by its instructions. |
| `SP_09` | general | MISSING_OR_MALFORMED_OUTPUT_TERMINATION | The agent's output ends without the terminator the execution harness needs to close the field block, or ends with a truncated or corrupted one, so the harness cannot tell the output is complete. |
| `SP_10` | general | MALFORMED_SECTION_OR_FIELD_DELIMITER | The agent emits the harness's section or field markers with corrupted syntax — wrong enclosing characters, missing hashes, or blocks in an order the harness cannot follow — so a field is misread or lost. |
| `SP_11` | general | OMISSION_OF_REQUIRED_OUTPUT_FIELD | The agent's output omits one of the fields its signature declares — the field the harness expects for that step is simply absent from the emission. |
| `SP_12` | domain | PREMATURE_TASK_EXECUTION_HALTING | The agent makes a domain-level decision to halt or terminate task execution prematurely before completing the required reasoning or task steps. |
| `SP_13` | domain | UNCRITICAL_PROPAGATION_OF_PRIOR_CONTEXT | The agent uncritically accepts, carries forward, or relies upon unverified assumptions, assertions, or conclusions from prior execution turns as established facts, using them as premises for downstream queries or conclus |
| `SP_14` | domain | IGNORING_OR_DISREGARDING_PRIOR_CONTEXT | The agent fails to incorporate, reconcile, or account for explicit context, facts, or evidence established in prior execution turns, treating available prior context as absent or evaluating the current turn in isolation. |

## Hand amendments, 2026-09-09

Four codes described the DSPy harness's output format as a breach of the agent's instructions. The shared instruction set for this candidate set is four one-line docstrings ('Given the fields X, produce the fields Y.') and mandates no terminator, delimiter or schema, so those codes cited a contract that does not exist and would have fired on almost every trace. They now name harness-parse failures, and each says explicitly that using the harness's own markers is required rather than a deviation — the correction already applied to hover/tax-19.

| code | field | reason |
|---|---|---|
| `SP_04` | definition | the shared instructions are four one-line docstrings and require no format at all; the delimiters are the DSPy harness's own, so this is a harness-parse failure, not a breach of the agent's contract |
| `SP_04` | when_to_use | same |
| `SP_04` | when_not_to_use | prevents the tax-18 error, where the harness's own markers were read as candidate failures |
| `SP_09` | name | 'required termination element' implied a clause that the bare instruction set does not contain |
| `SP_09` | definition | restated as a harness-parse failure; the instructions mandate no terminator |
| `SP_09` | when_to_use | same |
| `SP_09` | when_not_to_use | boundary against SP_04/SP_08 and against reading the harness format as a contract |
| `SP_10` | definition | 'required by instructions' and 'instructed format' name clauses that do not exist in the shared prompt |
| `SP_10` | when_to_use | same |
| `SP_10` | when_not_to_use | same |
| `SP_11` | definition | 'contractually required… mandated by its instructions' overstated a bare docstring; the fields come from the signature the harness declares |
| `SP_11` | when_to_use | same |
| `SP_11` | when_not_to_use | boundary against SP_04 and SP_12, and states that declared fields are required |
| `SP_08` | when_not_to_use | 'required by its instructions' softened; boundary to SP_10 made explicit |

## Correction to the hand amendments, 2026-09-09

**The premise of the amendment table above is false, and the table stays as written
because it is the record of what was executed.** This section is the amendment to it.

The table asserts that the shared instruction set "mandates no terminator, delimiter or
schema" and that the `[[ ## ... ## ]]` markers are "the DSPy harness's own", so a code
citing them cites "a contract that does not exist". Checked against the traces, that is
wrong. Every turn carries a system message stating the full format contract, including
the terminator, and closing with "In adhering to this structure, your objective is:"
before the docstring. Verbatim, from `pool_judging/000be347d9b4d42d92d74325.json`,
`messages[2]`:

```
Your input fields are:
1. `claim` (str):
2. `passages` (str):
Your output fields are:
1. `reasoning` (str):
2. `summary` (str):
All interactions will be structured in the following way, with the appropriate values filled in.

[[ ## claim ## ]]
{claim}
...
[[ ## completed ## ]]
In adhering to this structure, your objective is:
        Given the fields `claim`, `passages`, produce the fields `summary`.
```

The four one-line docstrings are the *objective*; the format spec is delivered alongside
them in the same system message, every turn. The agent's contract is both.

Measured over a 60-trace sample of `pool_judging`: 241 system messages, 4.0 per trace,
240 of them (99.6%) carrying the terminator spec. So `SP_04`, `SP_09`, `SP_10` and `SP_11`
name genuine breaches of stated instructions, not harness-parse artefacts. The amendment
was a correction the codes did not need.

### What the amendment nevertheless got right, for a different reason

The one system message in 241 without the terminator spec is not an omission — it is
DSPy's JSONAdapter, which states a *different* contract:

```
Outputs will be a JSON object with the following fields.

{
  "reasoning": "{reasoning}",
  "summary": "{summary}"
}
```

Across the full 4,500-trace pool, 100 traces (2.2%) contain at least one such turn,
106 turns in all. On those turns a JSON object is the required output and delimited
field blocks would be the deviation — the exact inversion of the rule everywhere else.
So the boundary clauses the amendment added are still worth having, but the reason is
per-turn contract variation, not the absence of a format contract.

### Consequences, not yet applied

1. No wording is changed here. Any rewording of `SP_04`/`SP_08`/`SP_09`/`SP_10`/`SP_11`
   is a new artifact, `tax-15`, beside this one; `taxonomy.json` is untouched.
2. `judge-4`'s first run (`runs/new_pipeline/hover-models/pointjudge-1`) reads tax-14
   as it stands and is unaffected by this note.
3. Open: a judge should be told which contract governs the turn it is reading. Until it
   is, format-code firings on the 2.2% of traces with a JSONAdapter turn are suspect in
   both directions.
