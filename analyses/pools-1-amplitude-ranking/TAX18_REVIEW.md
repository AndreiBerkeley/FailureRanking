# tax-18 read code by code: which are written at the wrong level

2026-09-07. Each of HoVer's 18 codes read against the rule that a code must name a mechanism every
candidate could exhibit, with its firing counts from `map-3` and the correlation of its rate with
candidate instruction length. Nothing edited; this is the proposal.

## Verdicts

| group | codes | firings | share |
|---|---|---:|---:|
| A: instruction detector — can only fire where a candidate's instructions define the artifact | SP_01, SP_02, SP_05, SP_07, SP_08, SP_10, SP_11, SP_12, SP_16, SP_17 | 1,106 | 68% |
| B: mechanism is universal but the wording ties it to a clause, or contradicts one | SP_04, SP_09, SP_15, SP_18 | 208 | 13% |
| C: already general | SP_03, SP_13, SP_14 | 151 | 9% |
| D: measures the harness's output protocol, not the candidate's work | SP_06 | 150 | 9% |

Worst case is SP_12, which names one candidate's clause verbatim: "violating the explicit prompt
instruction that 'none' should only be emitted when a claim is thoroughly falsified by a false
premise". Three of twelve candidates have that instruction.

## Three structural defects found alongside

1. **SP_08 and SP_16 are the same code.** Both read "fails to map out the required multi-hop
   verification steps in its reasoning field", one filed general and one domain. They fire on
   exactly the same 27 traces, never one without the other, so every one of those traces is
   counted twice by any formula that sums codes.
2. **SP_03 and SP_09 contradict each other**, and both fire on 29 traces. SP_03 penalises invoking
   internal knowledge; SP_09 penalises concluding evidence is missing "without using internal
   knowledge to deduce missing bridge entities". The taxonomy asks for a behaviour and forbids it.
3. **Three cross-references point at codes that do not exist.** SP_17 sends the reader to
   `MISSING_REQUIRED_OUTPUT_FIELD_OR_MARKER`, SP_18 to `UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJECTION`
   and `DISALLOWED_QUERY_SYNTAX_OR_STYLE`. All three are tax-7 parent names that the split did not
   rewrite, so a reader following a boundary lands nowhere.

Also worth noting: SP_03 and SP_04 are one mechanism (an ungrounded assertion) split by which
output field it appeared in, which the framework's own rule forbids: "the same mechanism in a
different output is the same failure and stays one code; the occurrence records which agent."

## Proposed rewrite (tax-20)

| do | to | why |
|---|---|---|
| re-level | SP_01, SP_02, SP_17 → one code: the output takes a form its own instructions specify against | the three enumerate one candidate's format rules |
| re-level | SP_07, SP_08, SP_16 → one code: the output omits a section its own instructions require | ditto, and SP_08/SP_16 are duplicates |
| re-level | SP_10, SP_11, SP_12 → one code: a field carries content of a kind it is not for | all three are "the query field holds something that is not a query" |
| merge | SP_05 into SP_03 | "claims a document was retrieved that was not" is an ungrounded assertion |
| merge | SP_04 into SP_03 | same mechanism, different output field |
| edit | SP_09 | drop "without using internal knowledge to deduce missing bridge entities" |
| edit | SP_15, SP_18 | state them against what the input establishes and what retrieval needed, not against a tracking field or a fixed query recipe |
| keep | SP_13, SP_14 | already general |
| decide | SP_06 | the completion marker is the harness's protocol; arguably environment, not candidate |
| fix | the three stale cross-references | |

18 codes become about 8. **The mapping cannot be reinterpreted under the new codes**: the counts in
`map-3` were produced against the old wording, so the rewrite needs a rejudge of the 600 traces,
roughly $40, before any score is recomputed.

## Honest expectation

Re-levelling removes the 68% of firings that measure contract style. It is not guaranteed to raise
the ranking: scoring the three already-general codes alone reaches tau +0.17 against the
generalization gold, against +0.02 for all eighteen and a +0.78 ceiling. The case for the rewrite is
that the instrument stops reading the candidates' construction, which METHODOLOGY.md holds
inadmissible, not that a better number is assured.
