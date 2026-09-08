# Are the judge's firings correct? A hand audit of 30 HoVer cases

Sampled 2026-09-07 from `data/hover/mappings/map-3` (tax-18), stratified across codes, taking only
firings where both readers agreed (vote 2). Each case was read against that turn's own instructions,
input and output: `hover_firing_audit_cases.txt` holds the 30 cases in full, produced by
`scripts/` + `new_pipeline.judge.judge.render_turns`. Verdicts are mine, not a model's.

| code | cases | the observation is factually right | breaches a clause the candidate actually had |
|---|---:|---:|---:|
| SP_02 disallowed query syntax | 6 | 6 | 0 clearly, 2 arguably |
| SP_01 conversational query | 4 | 4 | 1 of 4 |
| SP_07 omitted evidence section | 4 | 4 | 2 clearly, 2 prose-vs-header quibbles |
| SP_06 missing completion marker | 4 | 4 | 4 |
| SP_17 malformed list | 4 | 3 | unclear; 1 wrong (the list was correctly formatted) |
| SP_13 passage misconstruction | 3 | 2 | n/a (always possible) |
| SP_14 invalid verdict inference | 2 | 2 | n/a |
| SP_18 claim constraint omitted from query | 3 | 3 | 0 — the contract *required* the narrow query |

**Headline.** The judge is accurate about what is in the text: 28 of 30 observations are literally
true of the output. The error is in the second half of the contract rule. On the two most-fired codes
the clause being breached often does not exist in that candidate's instructions, and on SP_18 the
code penalises exactly what the instructions demanded ("Avoid Overloading Queries with Multiple
Entities"), which is why its rate runs backwards against gold (tau -0.60).

## Why it happens

**1. The taxonomy, primarily.** A code's `when_to_use` presupposes the constraint rather than
requiring it: "Use when the query contains disallowed quotation marks" tells a reader to fire on the
quotation marks. Nothing asks whether they were disallowed for this candidate. Measured on the 12
HoVer candidates (map-3):

| code | fires where the candidate's contract HAS the clause | where it does NOT |
|---|---:|---:|
| SP_01 conversational query | 18% of traces (8 candidates) | 56% (4 candidates) |
| SP_02 disallowed syntax | 56% (5 candidates) | 81% (7 candidates) |

Both fire *more* where no clause exists, because a candidate never told to write keyword queries
writes questions. The observation is right; calling it a breach is not.

**2. The framework requires it.** The preamble forbids a code from naming an agent or a candidate,
so a code induced from one candidate's clause becomes a rule applied to all twelve. On these
benchmarks the candidates ARE their instructions, so that erases the only thing that made the code
conditional. `GENERATION_v2.md`'s open question is the mirror image of this.

**3. Consequence: most codes are instruction-length proxies.** Instruction length correlates with
gold on HoVer (tau +0.64, GEPA made the good candidates verbose). Per-code rate against gold, and
against instruction length:

| code | vs gold | vs instruction length |
|---|---:|---:|
| SP_01 conversational query | +0.63 | **+0.69** |
| SP_05 hallucinated doc accounting | −0.68 | **−0.78** |
| SP_15 retrieval-state mistracking | −0.64 | **−0.73** |
| SP_18 claim constraint omitted | −0.60 | **−0.73** |
| SP_03 parametric knowledge injection | +0.62 | +0.30 |

Every strong code except SP_03 is explained better by instruction length than by quality. SP_03 is
the only one with signal of its own.

**4. The judge has a real but unquantified defect too.** It batches five traces per call and does
not group them by candidate: 120 of 120 batches in the ifbench and hotpotqa mappings mixed 3–5
candidates, each with different instructions, in one prompt. Generation forbids exactly this
(`generation/run.py`: "mixing candidates in a batch means judging some traces against rules they
never had"). Whether this inflates firing is untested: the offline check on hotpotqa has no
contrast (11 of 12 candidates carry rich instructions). The decisive test is a rejudge at
`--traces-per-call 1` on the four bare HoVer candidates, 200 traces, roughly $25.
