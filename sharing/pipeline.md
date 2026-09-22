# The pipeline: generation, splits, recovery

Three parts of the method that the result tables take for granted. A *failure mode* is a
code in the taxonomy; a *failure instance* is one occurrence of a mode in one trace — a
turn, a quoted evidence span, and the mode(s) it exhibits. The judge records instances;
recovery gives each instance a verdict; the formulas count instances or the tasks they sit on.

## 1. How taxonomy generation works

**What goes in.** A corpus of traces (the candidates' recorded executions, rendered as
turns: what each agent was told, received and produced) and the benchmark's
`structure.json`: the agents, how they hand off, and the *success rule* — how the program's
output is scored (for HoVer: on retrieved document titles, three per task; for
Terminal-Bench: on hidden tests over the container's final state). No outcome is ever in
view. Outcomes are used once, before any model call, to compose the corpora (below).

**Four rules the taxonomy must obey.** An agent is judged against its own instructions and
its own input (*contract*). A code names *how* a failure worked, never what it cost
(*mechanism, not consequence*). A new code only when the mechanism differs
(*specialisation*). A code's *column* is general (the mistake is at the edges of the agent's
work: reading its input, forming its output) or domain (in the middle: the reasoning
itself).

**The draft: six stages, one model** (Gemini 3.6 Flash on the current runs).

| stage | what it does |
|---|---|
| 1 field analysis | reads a sample of traces and states what solving this kind of task requires — the yardstick "what should this step have produced" |
| 2 observation | per trace and per turn, in batches: *2a* what the step needed to produce and what it produced instead, quoted; *2b* whether the step's output conforms to its own instructions. Almost no rules here on purpose: this stage only writes down what happened |
| 3 abstraction | groups the observations into recurring mechanisms, names each, assigns its column, and states its consequence pathway (how one occurrence changes the final output). A mechanism with no pathway is dropped |
| 4 applicability | per (mode, agent): can this mode occur for this agent, and is it the same mechanism there |
| 5 consolidation | one canonical taxonomy with stable ids, definitions, when-to-use / when-not-to-use |
| 6 rule validation | every code checked against the four rules; the verdict is derived from the checks, not asserted |

Discovery is separated from filtering deliberately: an earlier version applied the rules
during observation and the model then only wrote down what was unimpeachable — about a
fifth of the vocabulary. A mode never written down cannot be corrected later.

**Refinement round.** The judge (below) reads a second, task-disjoint corpus holding the
draft. From its records — how often each code fired, where readers disagreed, which
problems the taxonomy-free reader described that a code fitted well or only by stretching,
and which fitted nothing — a panel of four reviewers each fills a per-code checklist; the
checklists are merged; a final call decides merges, splits and additions. Verdicts are
derived from the checklist by code, so a check and a verdict cannot contradict.

**Gate.** On a third corpus, never shown to the refiner: four independent readers holding
the taxonomy plus one reader holding none, no discussion. Two numbers: Fleiss' kappa over
(trace, code) pairs, and coverage — the share of the taxonomy-free reader's problems that
some code fits well. The draft is gated once before refinement (the baseline) and once
after. Pass is kappa ≥ 0.75 and coverage ≥ 0.70; the taxonomy ships with its gate numbers
either way. A code the taxonomy-free reader independently confirms on fewer than 30% of the
traces the panel assigned it to is retired.

**Follow-ups on fresh traces.** *Gap test*: fresh traces are observed without the taxonomy
in view and every finding is mapped to a code or to "none", with the codes ruled out and
why. *Granularity*: a code carrying many findings is offered a split; accepted only when the
parts occur independently across traces. *Proposals*: findings no code fits well are grouped
by mechanism, a code is proposed for every group of at least three, validated by stage 6,
and admitted with the next stable id. Every change is append-only with provenance.

On the current runs a taxonomy costs $28–42 and takes 2–2.5 hours; the draft is the cheap
part ($7–11), the refinement judge and the two gates are most of the rest.

## 2. How the tasks are split

Every benchmark has one seeded, task-disjoint master partition, and nothing crosses it:

| pool | used for | outcomes read? |
|---|---|---|
| **taxonomy** (T tasks) | the generator's corpora | for stratification only, before any model call |
| **judging** (J) | the traces the judge and recovery reader read; scores are computed here | after the fact, to check calibration (`compared_scoring.md`) |
| **generalization** (G) | the target the rankings are validated against | after the fact, as the target only |

### What each pool needs to be worth having

**Judging: 20 tasks is the floor, 50 the target.** A score is a share of J tasks, so J fixes
the pass-rate gap between two candidates the ranking can get right (90% of the time):

    δ = √(0.8 / J)        J = 10 → 0.28,  20 → 0.20,  50 → 0.13,  100 → 0.09

At 10 tasks δ is wider than the whole spread of any candidate set we have (GEPA 20 points,
models 14, Terminal-Bench 33): the ranking is noise. At 20 it separates the top from the
bottom and little else; at 50 it resolves 13-point gaps and matches what the judged tasks'
own outcomes achieve. The sweep in `results_ablation.md` agrees: at k = 10, draws of the
unrecovered-incidence tau go negative on both HoVer sets; k = 20 is the first size where every
draw is positive; k = 50 reaches the gold bar.

**Generation: 15 tasks is the floor, 40 the target.** A mechanism becomes a code only when
it recurs — a proposal needs three findings, a split four, and a mode seen on one task is a
task specific. A mode present on a share q of tasks is expected on T·q of them, so to see it
on three tasks:

    T ≥ 3 / q             q = 0.2 (one task in five) → 15,   q = 0.075 → 40

Our one comparison points the same way: HoVer's taxonomy, built on 40 tasks, left 5.5% of the
judge's instances without a code; Terminal-Bench's, built on 16 pseudo-tasks over about ten
real ones, left 21%, and the missing modes were frequent ones. Traces: at least 64, every
candidate contributing at least 3 failing traces, at most 4 traces per task so the corpus
spans tasks rather than candidates; the generator reads at most 160 traces (40 tasks), so a
larger pool is never read.

**Generalization: at least 18 × J.** Outcomes cost nothing, so the target takes every task
the other two do not need, and its floor is the compression rule: the ranking is read on at
most ~5% of the tasks it is claimed for. That is also what keeps the target from being the
bottleneck — at 18 J its resolution is finer than the judged score's.

### The sizes, from N

    N = min(|dataset|, 1000)
    T = clamp(4% N, T_min, 40)         T_min = 15 (and ≥ 64 traces at ≤ 4 per task)
    J = clamp(5% N, 20, 100)
    G = N − T − J,  required G ≥ 18 J   (ρ = J / G ≈ 5.5%)
    δ = √(0.8 / J)                      reported with every result, never chosen after the fact

| N | T | J | G | ρ | δ |
|---:|---:|---:|---:|---:|---:|
| 1000 | 40 | 50 | 910 | 5.5% | 0.13 |
| 700 | 28 | 35 | 637 | 5.5% | 0.15 |
| 500 | 20 | 25 | 455 | 5.5% | 0.18 |
| 400 | 16 | 20 | 364 | 5.5% | 0.20 |

Generation stays smaller than judging at every N. The rule is satisfiable from
**N ≈ 400** (15 + 20 + 360).

### When judging and generation share tasks

Below N ≈ 400 the three pools do not fit. Then:

- **with reruns (r ≥ 2 runs per task)** — the judged tasks serve both purposes, as on
  Terminal-Bench: run 0 is judged; runs 1…r−1 are the generator's corpora, each (task, run)
  a pseudo-task to the planner. One rerun of 20 judged tasks already meets T_min
  ((r − 1)·J ≥ 15). The judge never reads a trace the codes were written from and the
  generator never reads an outcome, so nothing leaks; the shared thing is the tasks, which
  the generalization set does not contain.
- **without reruns** — no compliant design exists: generation and judging would read the
  same traces, so the codes would be fitted to the traces they are then counted on and
  coverage on the judged set would be inflated by construction. Capture a second run of the
  judged tasks (M·J candidate runs, cheaper than judging them) or run the study as a declared
  exception with its actual ρ.

### The four experiments against the rule

| benchmark | N | T | J | G | ρ | δ | status |
|---|---:|---:|---:|---:|---:|---:|---|
| HoVer, GEPA candidates | 1000 | 40 | 50 | 500 | 10% | 0.13 | G short of 18 J: ~410 more generalization tasks to run (12 candidates, outcomes only) |
| HoVer, models | 1000 | 40 | 50 (two disjoint sets) | 500 | 10% | 0.13 | same, 9 models |
| LiveCodeBench | 1000 | 40 | 150 judged; 50 is the compliant reading | 755 | 6.6% at J = 50 | 0.13 | the 100 unjudged judging-pool tasks can join G (855, 5.8%) |
| Terminal-Bench 2.0 | 89 | reruns 1–4 of the judged tasks | 20 (run 0) | 69 (run 0) | 29% | 0.20 | below N ≈ 400: the merged design, reported as an exception |

The GEPA-candidate split has one extra rule: the tasks the optimizer saw are only ever in the
taxonomy pool; the judged 50 and the generalization 500 are the pre-existing evaluation
sample and domain, never seen by the optimizer. LiveCodeBench's pools were drawn 50 easy +
50 medium + 50 hard each; Terminal-Bench's judged 20 by four strata of the frontier models'
mean pass rate (outcomes for stratification only).

**Inside the taxonomy pool** the planner deals tasks into four disjoint corpora:
generation (4 traces per task, failing traces first, candidate-balanced, every candidate
contributing at least 3 failing traces), refinement (4 per task), gate (60 traces over at
least 15 tasks), and the gap test's fresh traces (one failing trace per task). Failure-bearing
tasks are shared out first so each corpus carries failures; leftovers are unused.

## 3. How the recovery pass works

**Where it sits.** The judge reads each trace in five calls — a reader with the taxonomy
in view and a reader without it each list failure instances, then assign modes to their own
frozen list; a decider validates and merges the two lists on the evidence. Its output is one
instance list per trace: turn, evidence span, problem, modes (or none, when nothing fits —
such instances are kept, not dropped). The judge is deliberately blind to whether an instance
mattered; if it were not, it would under-report the harmless ones and the rates would lose
their meaning.

**What recovery asks.** For each instance, *does the final output still carry it?* A
separate reader (Claude Sonnet 5), one call per trace, receives the whole trace, the final
output it contains, the judge's instances with the **modes hidden**, and the same success
rule the judge saw. For every instance it answers four questions, each with a verbatim
quote:

1. **effect** — the artifact the instance produced, quoted from its own turn;
2. **consumed** — later turns whose input contains that artifact;
3. **events** — later turns that corrected it, or demonstrably received it and did not use it;
4. **output** — is the effect visible in the final output; and, where the harm is an
   absence, is the missing thing present in the output anyway.

The reader states no verdict. Code checks every quote against the section it claims to
come from (exact, or a contiguous match of ≥ 85% of the quote), checks that consumed and
event turns come after the instance, drops any claim that fails and records why, and then
applies a fixed rule:

| the evidence says | verdict |
|---|---|
| what the instance cost is absent from the output, or its effect is visible there, or the output cannot settle it | **unrecovered** |
| the output does not carry it and a correction event stands | corrected |
| the output does not carry it and nothing corrected it — nothing downstream used it, or it was used and the output was fine regardless, or the need was supplied by another path | contained |

Recovered = corrected ∪ contained. Missing evidence never becomes recovery: a claim whose
quote is not in the trace is dropped, and an instance the output cannot settle stays
unrecovered. (Runs made before 2026-09-22 recorded five finer verdicts; they map onto these
three without any instance changing side.)

**Why the success rule matters here.** "The output contains it" has to mean what the task
is scored on. On HoVer that is the document's own title line; a passage elsewhere that
mentions the entity does not supply it. Before the rule was in the reader's prompt, a hand
audit found 10 of 100 recovered verdicts wrong, all of that one kind; after, 2 of 60. The
Models·HoVer recovery run predates the rule, which is why its scores read 20 points too
optimistic in `compared_scoring.md`.

**What it produces.** The judge's instance list with a verdict and its evidence on every
instance; the judge's own record is untouched. The *unrecovered-only* input used in the
result tables is that list with the recovered instances removed. On the three runs so far,
58–83% of instances were recovered; the share of traces flagged fell from 93–98% to 30–59%.
