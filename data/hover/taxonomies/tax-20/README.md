# tax-20 — 10 failure modes for the HoVer program

`tax-19`'s 18 codes re-levelled by hand on 2026-09-07 so that every code names a mechanism any
candidate could exhibit. 4 general, 6 domain. The number is an artifact id, not a count of
anything; this one happens to hold 10 codes.

**Why.** A code-by-code review of `tax-18` (`analyses/pools-1-amplitude-ranking/TAX18_REVIEW.md`)
found 10 of its 18 codes could only fire where a candidate's own instructions happened to define the
artifact being breached: "the query contains disallowed quotation marks" fires on a candidate whose
instructions never mentioned quotation marks, and cannot fire on one never told how to write queries.
Those 10 carried 68% of all firings, and their rates tracked instruction length rather than quality.
A code written that way reads the candidate's *construction*, which `METHODOLOGY.md` holds
inadmissible, rather than its *execution*.

**The rule applied.** The general fields (definition, use when, do not use when) hold for every
candidate and name no particular token, section title or format rule. The specifics live in each
code's `evidence`, mined from `map-3`: real occurrences with the trace, agent and turn. Every code
carries between two and four. Program vocabulary declared in `program/structure.json` is not
candidate-specific and is used freely.

**Three defects fixed on the way.** `SP_08` and `SP_16` were the same code filed in two columns and
fired on identical trace sets, double-counting 27 traces. `SP_03` and `SP_09` contradicted each
other, one penalising the use of internal knowledge and the other its absence, and both fired on 29
traces. Three cross-references pointed at `tax-7` parent names that no longer existed.

| id | column | name | definition | from |
|---|---|---|---|---|
| `RL_01` | general | **Output Form Breach** | The agent emits an output whose form departs from what its own instructions require of it: the structure, syntax, ordering or composition of a field it produced. | SP_01, SP_02, SP_17 |
| `RL_02` | general | **Missing Required Part** | The agent's output omits a part that its own instructions require it to produce: a named section, a list, or an account of its working that those instructions call for. | SP_07, SP_08, SP_16 |
| `RL_03` | general | **Wrong Content In Field** | The agent puts into a field a different kind of thing than the field is declared to carry: a refusal, a remark, an explanation, or a conclusion where the field is for something else. | SP_10, SP_11, SP_12 |
| `RL_04` | domain | **Unsupported Assertion** | The agent states something its own input does not contain or support: an invented fact, entity, title or date, or a claim that material is present in what it was given when it is not. | SP_03, SP_04, SP_05 |
| `RL_05` | domain | **Premature Completion** | The agent concludes that what it holds is sufficient, or that nothing further is required, while something the task turns on is still unestablished by that material. | SP_09 |
| `RL_06` | domain | **Input Misreading** | The agent misinterprets, misreads or misattributes a statement, entity or grammatical relationship that is present in the material it was given. | SP_13 |
| `RL_07` | domain | **Unlicensed Conclusion** | The agent reaches a conclusion that does not follow from the state of the evidence it has itself described: treating an absence as disproof, settling a matter while acknowledging an unverified part, or asserting a conflict its material does not contain. | SP_14 |
| `RL_08` | domain | **Work State Misjudged** | The agent misjudges what its own inputs establish about the state of the work so far: what has already been obtained, what is still outstanding, or what an earlier step established. | SP_15 |
| `RL_09` | domain | **Misdirected Next Step** | The agent produces the action meant to carry the work forward, and that action cannot obtain what its own account says is still outstanding: it targets what is already established, or drops the detail that identifies the outstanding item. | SP_18 |
| `RL_10` | general | **Missing Closing Marker** | The agent's output ends without the terminal marker that the prompt instructs it to close with. | SP_06 |

## What became of each tax-19 code

| from | to | operation | why |
|---|---|---|---|
| SP_01, SP_02, SP_17 | `RL_01` | merge | the three enumerated one candidate's query- and list-format rules; the mechanism is a departure from whatever form the agent's own instructions require |
| SP_07, SP_08, SP_16 | `RL_02` | merge | SP_08 and SP_16 fired on identical trace sets, and all three named sections only some candidates are told to produce |
| SP_10, SP_11, SP_12 | `RL_03` | merge | all three are 'the field holds something the field is not for', separated only by which token was used |
| SP_03, SP_04, SP_05 | `RL_04` | merge | one mechanism split by which output field it appeared in, which the framework's attribute-not-specialise rule forbids |
| SP_09 | `RL_05` | edit | dropped 'without using internal knowledge to deduce missing bridge entities', which contradicted SP_03 |
| SP_13 | `RL_06` | edit | kept; already general |
| SP_14 | `RL_07` | edit | kept; already general |
| SP_15 | `RL_08` | edit | restated against what the input establishes rather than against a tracking field only some candidates have |
| SP_18 | `RL_09` | edit | restated against what the work still needed rather than against including every claim detail, which some contracts forbid |
| SP_06 | `RL_10` | edit | kept, with the source of the requirement stated in the code |

## Before it can be used

The counts in `map-3` were produced against `tax-18`'s wording and **cannot be reinterpreted** under
these codes. A score under `tax-20` needs a fresh judging pass over the 600 traces, roughly $40.
