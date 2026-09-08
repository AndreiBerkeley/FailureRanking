# Audit of the observation pass on 10 failed traces

2026-09-02. Ten traces drawn uniformly (seed 0) from the 150 sample-2 traces
that failed gold. Each was read in full by an independent auditor against the
system prompts actually in the trace, failure points listed before the
recorded findings were revealed, then matched. Bundles (trace, gold, recorded
findings, mapping records) are in the session scratchpad `audit/`; the
auditors' full reports are in the session task transcripts. Gold was used only
to select failed traces and to name the outcome-linked failure point; it
touched no scoring path.

## Per trace

| trace | cand | recorded | found | matched | missed | spurious | miscoded | outcome-linked captured |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0cd2c788 | 1 | 0 | 6 | 0 | 6 | 0 | 0 | no |
| a8792535 | 1 | 6 | 7 | 5 | 2 | 0 | 0 | yes |
| 7015b004 | 6 | 2 | 7 | 2 | 5 | 0 | 0 | no |
| d0cbff42 | 1 | 1 | 7 | 1 | 6 | 0 | 0 | no |
| c8941c8d | 0 | 1 | 7 | 0 | 7 | 1 | 0 | no |
| b9d8e350 | 3 | 3 | 9 | 3 | 6 | 1 | 1 | yes |
| 9cdaf4e3 | 11 | 1 | 8 | 1 | 7 | 1 | 0 | no |
| dba8feb6 | 10 | 1 | 8 | 1 | 7 | 0 | 0 | no |
| 7bcea934 | 5 | 1 | 5 | 1 | 4 | 0 | 0 | no |
| b3471529 | 8 | 1 | 9 | 0 | 9 | 1 | 0 | no |
| **total** | | **17** | **73** | **14** | **59** | **4** | **1** | **2 / 10** |

Recall of the observation pass on these traces ≈ 14/73. Precision of what it
did record ≈ 13/17. Trace 0cd2c788 was also read by the session itself; the
three material points (missing completion marker at turn 4, self-contradicting
retrieved list at turn 4, Apple Inc. dropped from the summary at turn 11 after
the reasoning named it) are confirmed from the text.

## Where the misses fall

Query-generator turns were skipped in 6 of 10 traces; the second summarizer in
most. The pass typically records one thing on the first summarizer and stops.
Four traces omit the `[[ ## completed ## ]]` marker at a turn; none was
recorded, although MISSING_REQUIRED_OUTPUT_FIELD_OR_MARKER names it.

Of the 59 missed points, roughly 50 are describable by an existing code:

| mechanism | fitting code | ~n |
|---|---|---:|
| fact asserted that is in no input | UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJECTION | 10 |
| misreported retrieval state, unverified treated as verified, contradicts own inputs, claim misread | EVIDENCE_MISCONSTRUCTION_OR_LOGICAL_FALLACY | 18 |
| completion marker or mandated list header absent | MISSING_REQUIRED_OUTPUT_FIELD_OR_MARKER | 5 |
| descriptions or prose where titles required, non-normalised titles | MALFORMED_STRUCTURED_LIST_OR_SORTING_DEFECT | 6 |
| claim descriptor dropped from query | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | 5 |
| quoted questions / Boolean operators in query | DISALLOWED_QUERY_SYNTAX_OR_STYLE | 3 |
| `none` emitted with a missing document in hand | PREMATURE_RETRIEVAL_TERMINATION_OR_REFUSAL | 1 |

Two mechanisms have no code and both recur:

1. **Query aimed at an already-settled need, or repeated unreformulated after
   a hop that returned nothing.** ~6 instances (0cd2c788 t14, d0cbff42 t14,
   b9d8e350 t7 and t14, dba8feb6 t7, 7bcea934 t7).
2. **Bridge entity present in the input, or named in the agent's own
   reasoning, dropped from the summary handed downstream.** ~4 instances
   (0cd2c788 t11, d0cbff42 t11, b9d8e350 t4, b3471529 t4 as a pseudo-document
   replacing the title). Each was the outcome-linked failure of its trace.
   The eleven loose "trajectory not mapped out" findings from gap discovery
   belong here too.

## Systemic defects found on the way

1. **Contract header is one candidate's prompts for all.** `contracts.extract`
   takes the first trace in filename order per agent and stops; that is
   candidate 4. 273 of 300 traces in both the generation and gap runs were
   judged with 2–4 of 4 agents described by another candidate's instructions.
   Consequences seen: "should have used internal knowledge" findings on
   candidates whose prompts never say it; query-style findings citing clauses
   the candidate never received; conformance charges filed against the wrong
   agent. 3 of the 4 spurious findings above are this.
2. **Mapper joins by finding text.** `gaps.py` rebuilds trace attribution with
   `by_text[what_happened]`; 19 finding texts occur in more than one trace, so
   26 of 379 records carry the wrong trace_id. Per-code totals are unaffected;
   per-trace and per-candidate profiles are off by ~7%.
3. **Work and conformance passes double-count the same event** when both
   record it (a8792535 t14 `N/A`).
4. **Findings with null quotes, wrong turn indices, or wrong agent** (c8941c8d:
   a real `none` at turn 7 filed against hop 3 with a non-verbatim quote).

## Fixes applied after the audit (2026-09-02)

1. `contracts.extract_all` extracts one contract set per candidate; batches are
   grouped by candidate and each conformance batch is shown the contract set of
   its own candidate (`run.py`, `gaps.py`). Stages 3 and 4 receive every
   distinct instruction set per agent, labelled with the candidates that share
   it (`contracts.render_all`).
2. `judge.map_open` returns an `index` on every detail and `gaps.py` joins by
   it, not by finding text.
3. Traces are rendered as delineated turns (`taxonomy2/render.py`): each turn
   carries its agent, its own instructions, its input, and its output;
   environment and harness blocks are marked as not turns.
4. Both observation prompts (GENERATION_v2.md, 2a and 2b) require exactly one
   entry per turn, with a `checked` account when findings are empty; the
   runners reject a response that omits a turn or leaves one silent, the same
   way they reject a missing trace. Findings carry `turn` and `agent`.

Every earlier output under `runs/taxgen-v4/` (taxonomy, gaps, this audit) was
produced BEFORE these fixes and stands as the record of the defective pass.
Re-runs go to new directories; a re-run into an old directory would reuse its
saved observation files.

## Pilots of the fixed pass on the same ten traces (2026-09-02)

Matched = auditor failure points the pass recorded (mechanism and turn agree).
Outcome = traces whose outcome-linked failure point was recorded.

| pass | flags | recorded | matched /73 | spurious | outcome /10 | work thinking tok/call | prompt tok/call | dir |
|---|---|---:|---:|---:|---:|---:|---:|---|
| original (pre-fix) | — | 17 | 14 | 4 | 2 | not logged | ~11,500 | hover-gaps |
| per-turn accounting, whole trace | — | 17 | 19 | 0 | 3 | 2,937 | 11,571 | pilot-10 |
| one turn per call | `--per-turn-work` | 22 | ~20 | 0 | 3 | 1,233 | 2,493 | pilot-10-turns |
| one turn per call, thinking HIGH | `--per-turn-work --thinking HIGH` | 26 | ~21 | 0 | 3 | 1,719 | 2,493 | pilot-10-turns-high |
| + step ledger in the output | `--per-turn-work --work-ledger --thinking HIGH` | 27 | ~23 | 0 | 2–3 | 2,549 | 2,541 | pilot-10-ledger |
| same, model gemini-3.1-pro-preview | `... --model gemini-3.1-pro-preview` | 46 | ~31 | ~0 | 5 | 1,894 | 2,541 | pilot-10-pro |

Precision went to 100% with the contract fix and per-turn accounting; recall
moved from 19% to 29% across the three levers. Thinking level HIGH raised
thinking tokens by ~40%, not several-fold: the model treats the task as easy
and the default was already dynamic. Two traces (c8941c8d, 7bcea934) stay at
zero findings in every pass; in c8941c8d the reader misreads "as well as" the
same way the agent did. The two summary-handoff drops (Apple Inc., Money
Monster) are missed by every pass.

The ledger doubled thinking again and produced catches no earlier pass had
(a8792535's false "retrieved: Michael York"; 7015b004 now complete at 7/7),
but lost others that pilot B had (b9d8e350 fell from 4 findings to 1;
9cdaf4e3 lost Agatha Christie). Run-to-run variance at temperature 0 is
large: the UNION of matched points across the four fixed-pass pilots is about
30 of 73 (41%), against 21–23 for any single pass. Two conclusions: a single
reader pass is not a reliable measurement at this model, and the reader's
own comprehension is the ceiling (c8941c8d: the ledger shows the reader
misreading "as well as" exactly as the agent did, in every pass).

Pilot D (Gemini 3.1 Pro, same flags) matched ~31 of 73 in ONE pass, about
the union of all four Flash passes, at the same thinking budget (~1,900
tokens per turn). It broke the comprehension ceiling: it named the "as well
as" misparse on c8941c8d and the `none` query at the right turn, the
pseudo-document that lost The Jungle Book on b3471529, and Agatha Christie
missing on 9cdaf4e3. Outcome-linked failure captured in 5 of 10. Still
missed: the two summary-handoff drops (Apple Inc., Money Monster) and
7bcea934 entirely. Cost of the pilot ~$2.3; six 429s, all recovered.
Decision: the observation reader is Gemini 3.1 Pro with per-turn calls, the
ledger, and thinking HIGH.

## Judge pilot on the same ten traces (2026-09-02, `runs/taxgen-v4/pilot-10-judge`)

The measurement judge after its fixes (no elision, delineated turns, per-turn
accounting in panel and open reader, index join), on Gemini 3.1 Pro with
thinking HIGH, panel of 4 at threshold 2, open reader on, current 7-code
taxonomy. 10/10 judged, 0 failed, 50 code occurrences, all 7 codes fired,
60 calls, 15.4 min at 2 workers, 17 HTTP 429s all recovered on retry.

Audited points covered by a code fired at the right turn (panel vote or open
mapping), by the session's reading of the auditors' lists:

| trace | covered / audited | outcome-linked captured |
|---|---:|---|
| 0cd2c788 | 3 / 6 | no (Apple Inc. handoff drop) |
| 7015b004 | 6 / 7 | yes |
| 7bcea934 | 2 / 5 | no |
| 9cdaf4e3 | 5 / 8 | partial (wrong missing doc named, Agatha Christie not) |
| a8792535 | 6 / 7 | yes |
| b3471529 | 4 / 9 | yes (pseudo-document, via open reader) |
| b9d8e350 | 6 / 9 | yes |
| c8941c8d | 3 / 7 | yes (`none` query, FM_004, 4/4 votes) |
| d0cbff42 | 3 / 7 | no (Money Monster handoff drop) |
| dba8feb6 | 4 / 8 | partial |
| **total** | **~42 / 73** | **5–6 / 10** |

Against the single Pro observation pass (31/73) the panel-plus-open union
covers more, and precision stays high: nearly every panel vote was 4/4, and
the codes not in the auditors' lists (FM_001 on queries wrapped in quotation
marks) are correct by the code's definition. The two no-code mechanisms
surfaced as open-reader problems and were recorded as unmapped stretches
("query almost identical to turn 2", "album omitted from the retrieved
list"), which is the gap signal working as designed. Still missed by every
instrument: the summary-handoff drops.

Cost at full scale (600 judging traces, 3,600 calls): ~36M prompt tokens and
~14M output including thinking, roughly $240 on Pro at $2/$12 per million.
Panel votes were unanimous almost everywhere, so a panel of 3 loses little
and saves a sixth.

## Cheap judge configuration on the same ten traces (`pilot-10-judge-cheap`)

Panel of 2 on gemini-3.6-flash, 5 traces per call; open reader and mapping on
gemini-3.1-pro-preview, 5 traces per call; thinking HIGH. 10/10 judged in 3.7
min, 8 calls, 0 rate-limit retries, 40 code occurrences.

Covered ~28 of 73 audited points (session's scoring) against 42 for the Pro
panel one trace per call. The Flash panel missed unanimous Pro-panel catches:
the completion markers on 0cd2c788 and 9cdaf4e3 (FM_003), the "English actor"
knowledge injection on a8792535 (FM_002), most FM_005 instances. The Pro open
reader stayed strong even batched: it still named the "as well as" misparse
and the `none` query on c8941c8d and the pseudo-document on b3471529.
Outcome-linked captured ~3/10. Six open-reader findings were spurious
("produced a `reasoning` field despite the instruction naming only `query`":
the field is declared under "Your output fields"); they landed as uncovered,
so they did not enter any score, but they would inflate a gap count. The
judge's layout note now states that emitting a declared output field is not a
deviation.

Conclusion: Flash is not adequate for the panel. The untested middle option
is a Pro panel batched 5 traces per call (~$110, ~2 h for the judging set).

## Pro panel batched 5 traces per call (`pilot-10-judge-pro5`)

Panel of 2 and open reader both on gemini-3.1-pro-preview, 5 traces per call,
thinking HIGH. 10/10 judged in 5.4 min, 8 calls, 1 rate-limit retry, 37 code
occurrences, 0 unmapped, 0 spurious (the layout-note fix removed the
"reasoning field" false positives).

Covered ~29 of 73 (session's scoring), outcome-linked ~3–4/10. Batching cost
the Pro panel what it cost Flash: markers and evidence-misconstruction
instances that were unanimous at one trace per call went missing, and the
open reader lost the "as well as" misparse and the pseudo-document it had
found before. Thinking per call was ~9,000 tokens for five traces, i.e.
~1,800 per trace against ~3,500 at one trace per call.

| judge configuration | covered /73 | outcome /10 | calls for 600 traces | cost | wall-clock |
|---|---:|---:|---:|---:|---:|
| Pro, panel 4, 1 trace/call | ~42 | 5–6 | 3,600 | ~$240 | ~15 h |
| Pro, panel 2, 1 trace/call (inferred from unanimity) | ~42 | 5–6 | 2,400 | ~$160 | ~10 h |
| Pro, panel 2, 5 traces/call | ~29 | 3–4 | ~480 | ~$110 | ~2 h |
| Flash panel 2 + Pro open, 5 traces/call | ~28 | ~3 | ~480 | ~$40 | <1 h |

Conclusion: recall is bought with per-trace attention, not with the panel
size. One trace per call on Pro is the configuration; the panel can be 2.
