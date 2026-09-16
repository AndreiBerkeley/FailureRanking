# Methodology

## 1. The question and the design

A **candidate** is a system that solves tasks: a model behind a fixed prompt, or a set of
instructions run by a fixed model. Its **gold** on a task is the benchmark's own pass/fail.
The question is whether a judge reading the candidate's *traces* on a small task set can rank
candidates as well as their gold on that set — with both measured against gold on a large,
disjoint task set that neither saw.

Every benchmark is split once into three task-disjoint pools, and nothing crosses pools:

| pool | used for | what may read gold |
|---|---:|---|
| taxonomy | inducing the failure-mode taxonomy | only the corpus composer, to include failing traces |
| judging | the judge reads every candidate's trace on a subset | nothing on the scoring path; gold-50 is computed afterwards for comparison |
| generalization | the validation target: gold only, never judged | the comparison only |

Candidate scores are computed one candidate at a time from that candidate's own judged
traces; ranking happens afterwards.

## 2. Benchmarks and programs

**LiveCodeBench** (release_v6, 1,055 problems; AtCoder 602, LeetCode 444, Codeforces 9;
easy/medium/hard 322/383/350). The program is one model call: system prompt "You are an
expert Python programmer…", user prompt = problem statement + the official format block
(starter-code or stdin variant) — verbatim in `livecodebench/program/prompt.md`. The first
```` ```python ```` fence of the reply is executed against the hidden tests through the
upstream LiveCodeBench runner; gold = every test passed. Split `pools-1`: taxonomy 150
(50/50/50 by difficulty), judging 150 (50/50/50), generalization 755, seed 2026.

**HoVer** (multi-hop claim verification). The program is a four-module DSPy pipeline —
summarise hop-1 passages → write hop-2 query → summarise → write hop-3 query — with three
retrievals performed by the harness between modules (`hover/program/structure.json`). Gold =
all three supporting Wikipedia titles retrieved. Split `pools-1`: taxonomy 600, judging 500,
generalization 4,984; each candidate set uses its own 500-task generalization portion.

## 3. Candidate sets

| set | benchmark | candidates | what varies |
|---|---|---:|---|
| `models-1` | livecodebench, hover | 9 | the solver model; prompt/instructions fixed. gemini-3.1-flash-lite, claude-haiku-4.5, gpt-5.4-nano, deepseek-v4-flash, glm-5.3-flash, mistral-small-2603, minimax-m3, mimo-v2.5, seed-2.0-mini, all via OpenRouter |
| `pool-3` | hover | 12 | the four module instructions, proposed by a GEPA optimizer run; 8 accepted at even intervals over validation score + 4 rejected; model fixed (gemini-3.1-flash-lite) |

A candidate id is the hash of what defines it (`{prompt, solver_model}` or the instruction
texts), so traces, outcomes and mappings all key on the same identity.

## 4. Capture

One run per (candidate, task), repeat 0. LiveCodeBench: temperature 0, 16,000 output tokens,
reasoning off where the endpoint allows (else minimal, else default — probed per model and
recorded), `openai/gpt-5.4-nano` at temperature 1.0 as the endpoint requires. Traces are
stored in the judge's view — system / user / assistant messages plus metadata — and the
gold is scored separately into `outcomes` beside them. A reply that hits the token cap or
has no fence is a trace like any other and scores 0. HoVer captures follow the same rule
with the DSPy turn structure preserved (each module's instructions, input and output).

## 5. Taxonomy generation

The taxonomy is an instrument, induced from the taxonomy pool by `code/new_pipeline` under
a prompt document (`GENERATION_v2.md` for hover, `GENERATION_v3.md` for livecodebench) with
gemini-3.6-flash at every LLM stage:

| stage | what it does |
|---|---|
| 0 | program structure (supplied) and each agent's contract, extracted from its instructions |
| 1 | field analysis: what solving the task requires |
| 2 | observation: per trace and turn, what went wrong, quoted; v3 asks what was *expected* first |
| 3 | abstraction: recurring mechanisms; v3 adds a consequence pathway per mechanism |
| 4–5 | applicability per agent; consolidation into codes with stable ids |
| 6 | rule validation: every code against the rules (mechanism not symptom, program-neutral, …) |
| 7 | refinement round: the draft rewritten against the judge's reading of a second corpus |
| 8 | interannotation gate on a third corpus: pooled kappa across 4 readers (target 0.75) and open-reader coverage (floor 0.70) |
| gap test | 50 fresh traces read blind; findings that fit no code are reported |
| granularity | codes whose parts occur apart are split |

Corpus sizes: 160 traces / 40 tasks for generation, 160 for refinement, 60 traces / 15
tasks for the gate, 50 for the gap test — all from the taxonomy pool, failing traces
preferred by the composer. The generation run directory is archived beside each taxonomy.

Hand amendments are disclosed in each taxonomy's README: hover tax-14 → tax-15 added one
code for the family the judge could not place (51 points); livecodebench tax-1 → tax-2
added three codes for its 22 unplaced points (see §7 on how those were used).

## 6. The judge

**Failure points (`code/new_pipeline/pointjudge`)**, used for `models-1` on both benchmarks.
A failure point is a step plus a verbatim evidence span (or a named absence). Per trace:
reader A reads with the taxonomy in view and lists points, then assigns modes; reader B
reads with no taxonomy and does the same; a decider validates both lists against the trace,
merges points whose evidence agrees, settles spans and modes, and may answer "none fits".
Readers gemini-3.6-flash, decider claude-sonnet-5, thinking high, temperature 0, five calls
per trace. The mapping records every point with its turn, agent, evidence, codes and which
readers found it; the per-trace code map counts each code once per distinct step. Gold never
enters a prompt; the judge is told nothing about outcomes.

**Panel judge (`code/new_pipeline/judge`)**, used for `pool-3`: two annotators
(gemini-3.6-flash, thinking high) each read the trace with the taxonomy and name the codes
per trace; a code counts when both agree. An open reader (gemini-3.1-pro-preview) reads with
no taxonomy and its problems are mapped to codes afterwards. The mapping records the codes
that fired per trace and which source supplied each.

## 7. From mapping to ranking

Each method in `methods/README.md` turns one candidate's judged traces into one number; the
candidates are then ranked. Reported: gold (the reference), amplitude, incidence,
combinations, and — on hover, whose program has four steps — step-amplitude and
containment. All read the mapping and nothing else.

Two mappings carry hand work and are labelled as such: hover `pointjudge-1-sp15` lifts the
new code's points from a single-reader pass onto the two-reader mapping; livecodebench
`pointjudge-1-tax2` assigns the 22 points the decider could not place to tax-2 codes by
hand, without a re-judge (the re-judge with tax-2 in view is `pointjudge-2`).

## 8. The measure

Kendall tau-b between two rankings of the candidates, computed over the candidate pairs
ordered in both rankings — a pair tied in either is dropped, so a gold-50 with tied
candidates is compared on fewer pairs. One comparison per method: the method's ranking vs
gold-gen, the pass rate on the generalization pool. The gold row is gold-50 (the judged
tasks' own pass rate) vs gold-gen: how well scoring the judged tasks themselves predicts the
large set, the bar. Top-1: is the method's best candidate gold-gen's best. Stability: ten
uniform random draws of 50 from each 100- or 150-task judged set, each scored the same way.

## 9. Judged sets

| set | tasks | how drawn | gold read in the draw |
|---|---:|---|---|
| lcb `judging-50-1` | 50 | seeded within difficulty, 16/17/17 easy/medium/hard | no (easy under-weighted because the taxonomy pool showed 39/50 easy tasks solved by all) |
| lcb `judging-100-1` | 100 | the rest of the judging pool | no |
| hover `models-1-judged-50` | 50 | seeded random | no |
| hover `models-1-judged-50-b` | 50 | 500 seeded draws, kept the one with the fewest candidate pairs tied on gold-50 | **yes** (judging-pool outcomes only; the generalization gold was not read) |
| hover `eval-1/sample` | 50 | the evaluation sample | no |
| hover `judging-sample-2` | 50 | stratified by mean candidate score into four quartiles | **yes** (judging-pool outcomes) |

## 10. Runs and cost

| run | traces | cost | time |
|---|---:|---:|---:|
| lcb capture, three pools | 1,350 + 1,350 + 6,795 | $2.61 + $2.69 + $13.47 | 40 + 78 + 134 min |
| lcb taxonomy generation (v3, run-1) | 160 + 160 + 60 + 50 | ≈ $11 | 50 min |
| lcb judge, 50 tasks (`pointjudge-1`) | 450 | $11.10 reader + ≈ $10 decider | 22 min |
| lcb judge, 150 tasks (`pointjudge-2`) | 1,350 | $38.99 reader + ≈ $43 decider | 76 min |
| hover judge, 50 tasks (`pointjudge-1`, `pointjudge-3`) | 450 each | ≈ $41 reader + ≈ $68 decider each | 90–150 min |
| hover panel judge, 50 tasks (`map-5`, `map-6`) | 600 each | — | — |
