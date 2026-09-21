# Formulas

How a candidate's judged traces become a score, and how scores are compared. Every formula is
evaluated per candidate, independently; ranking happens only after every candidate has a score.

## Inputs

The judge reads every trace of candidate *c* on the judged task set 𝒯 (|𝒯| = T, the same tasks
for every candidate) holding a taxonomy with code set M. For each trace it records a set of
**failure points**; each point carries the step (turn) it sits on and one or more codes. The
recovery reader then gives every point one verdict: *unrecovered*, or recovered (*corrected*,
*contained*, *made irrelevant*), or *unassessable*.

| symbol | meaning |
|---|---|
| codes(c,t) ⊆ M | the distinct codes that fired anywhere in *c*'s trace on task *t*; a code cited several times counts once |
| codes(c,t,s) | the codes that fired at step *s* of that trace |
| s_last(t) | the trace's final step |
| rate(c,m) | share of judged tasks on which code *m* fired for *c* |
| g(c,t) ∈ {0,1} | the gold outcome (pass = 1); never read by a trace formula, only by the reference and the measure |

A judged trace with no point contributes an empty set. A trace that could not be judged is
left out of the sum and of T — "not judged" is not "no failure found".

**Two inputs, same formulas.** Every formula below is run twice:

- **all points** — the judge's mapping as recorded;
- **unrecovered only** — the same mapping with every point the recovery reader marked
  corrected, contained or made irrelevant deleted (unassessable points stay, since missing
  evidence is not recovery).

Nothing else changes between the two settings.

## The reference

**Gold** — pass rate on the judged tasks, higher is better: `G(c) = (1/T) Σ_t g(c,t)`.
Not a trace method. Its agreement with the generalization set ("gold-judged vs gold-gen") is
the bar: the judged tasks' own outcomes are the cheapest possible predictor of the larger set,
and a trace formula has to match or beat them to be worth anything.

## The baseline formulas (lower is better)

**Per-task flags** — one bit per task, then averaged. Repetition inside a trace cannot inflate them.

| formula | definition | reads as |
|---|---|---|
| **incidence** | `I(c) = (1/T) Σ_t 1[codes(c,t) ≠ ∅]` | share of tasks on which anything failed |
| **last-turn incidence** | `I_last(c) = (1/T) Σ_t 1[codes(c,t,s_last(t)) ≠ ∅]` | share of tasks on which something was still wrong at the final step — nothing ran afterwards that could fix it |

**Counts** — how much went wrong.

| formula | definition | reads as |
|---|---|---|
| **amplitude** | `A(c) = (1/T) Σ_t \|codes(c,t)\|` | distinct codes per task |
| **step-amplitude** | `A_step(c) = (1/T) Σ_t \|{(s,m) : m ∈ codes(c,t,s)}\|` | a code counted once per step it fires at |
| **damped PIE** (β = 0.5) | `D(c) = (1/T) Σ_t (1 − (1−β)^k) / β` with k = \|codes(c,t)\| | inclusion-exclusion over the task's codes with the subset of size j weighted β^(j−1): a task with 1, 2, 3, 4 codes contributes 1, 1.5, 1.75, 1.88. At β = 0 it is amplitude, at β = 1 it is incidence; β = 0.5 is the middle of a direction that was flat when swept |
| **containment** (the propagation discount) | `A_con(c) = (1/T) Σ_t \|{(s,m) firings not contained}\|` — a firing at step *s* is *contained* when later steps exist and no code fired at any of them | step-amplitude minus the firings the program's own later steps ran clean after; the last step is never contained. A failure that propagated (something downstream also failed) keeps full weight, one that did not is dropped |

**Profile shape** — what kind of failures, not how many.

| formula | definition | reads as |
|---|---|---|
| **breadth** | `B(c) = \|{m ∈ M : rate(c,m) > 0}\|` | how many distinct codes the candidate ever triggers |
| **worst mode** | `W(c) = max_m rate(c,m)` | the rate of its single most frequent code |
| **patterns** | `P(c) = \|{codes(c,t) : t ∈ 𝒯, codes(c,t) ≠ ∅}\|` | number of distinct code-sets it produced across tasks |

A point the judge kept but no code fit (`uncoded`) is handled two ways, and `results.md` reports
both: *every kept point* treats it as one more failure with its own pseudo-code; *coded points
only* drops it. The profile formulas read codes, so they have the coded-only form only.

## Recovery-dependent formulas

These use the recovery verdicts as a quantity rather than as a filter. Their numbers are in
`results.md`, Table 2 of each experiment.

**Recovery-weighted amplitude.** Each unit u = (code, step) is weighted by how rarely the
candidate recovers from it: `w_u(c) = 1 − (recovered_u(c) / appeared_u(c))^γ`, and
`A_rw(c) = (1/T) Σ_u w_u(c) · appeared_u(c)`, γ ∈ {1, 2, 3}. A unit fired on a task counts as
recovered on that task only if every point carrying it was; a unit seen on fewer than 3 tasks
takes the candidate's overall recovery share. A mode the candidate usually recovers from counts
less instead of not at all. (A *pooled* variant, one weight per unit for every candidate, was
≤ −0.5 on GEPA·HoVer and is not reported: a mode's fatality is not shared across candidates.)

**Profile risk.** Unrecovered incidence *predicted* from the profile instead of read per task:
each mode gets a consequence `q_c(m)` = the share of the candidate's points carrying *m* that
were left unrecovered; a task's risk is `max_m q_c(m)` over the modes that fired on it (a
noisy-OR combination, `1 − Π_m (1 − q_c(m))`, did worse); the score is the mean task risk.
It loses to the plain flag because modes on the same task recover jointly — on GEPA·HoVer
SP_06 recovers 69% alone and 36% next to SP_14 — so treating them as separate risks
over-counts verbose candidates.

**Gold-discounted incidence ("literal").** Not outcome-free: it reads the judged tasks' gold.
A task flagged with an unrecovered point counts 1 if the candidate failed it and *w* = 0.5 if
it passed it; an unflagged task counts 0 either way:
`I_g(c) = (1/T) Σ_{t flagged} [ 1 if g(c,t) = 0 else w ]`. It sits within noise of the plain
flag on every set tried, and spends gold to get there.

## From scores to a measure

Every formula gives one number per candidate; the candidates are ranked by it (ascending —
lower is better; gold descending). Rankings are compared with the ranking by pass rate on a
**target task set**: the *generalization set* (tasks disjoint from the judged ones, whose
outcomes no formula ever read — the real test) or the *judged set's own gold* (a same-task
check). Four quantities are reported for each:

**Kendall tau-b, ties dropped.** Take every pair of candidates (a, b). A pair is *resolved*
when the formula gives a and b different scores *and* the target gives them different pass
rates; otherwise it is dropped. A resolved pair is *concordant* if the formula and the target
order it the same way, *discordant* otherwise.

    tau = (concordant − discordant) / (concordant + discordant)

+1: the formula orders every resolved pair like the target; −1: every one reversed; 0: no
relation. Dropping ties is why a formula that scores many candidates identically (incidence
on all points, where almost every trace has a point) can show a tau built on few pairs.

**Resolved pairs.** concordant + discordant — how many of the n(n−1)/2 candidate pairs the tau
actually rests on (66 for 12 candidates, 36 for 9, 21 for 7). Read the tau against it: +0.6
on 8 pairs is two pairs from +0.1.

**Top-1.** Whether the candidate the formula ranks first is the one the target ranks first
(yes/no). Ties in the formula are broken by candidate id, so a formula that ties everyone
gets an arbitrary answer — the resolved-pairs column shows when that is happening.

**Top-3.** How many of the three candidates the formula ranks best are among the three the
target ranks best: 0/3 to 3/3. With 7 candidates 3/3 is easy (three of seven), with 12 it
is not.

For the gold row, "vs judged gold" is +1.000 / yes by construction, and its "vs gen gold"
columns are the bar: what the judged tasks' own outcomes achieve as a predictor of the
generalization set.
