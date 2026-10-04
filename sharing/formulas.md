# Formulas

How a candidate's judged traces become a score, and how scores are compared with the generalization set.
Every formula is computed per candidate from that candidate's own traces; candidates are ranked only after
every candidate has a score. Each formula is written as numbered steps from the judge's records to the number.

## Inputs

The judge reads every trace of candidate *c* on the judged task set 𝒯 (|𝒯| = T, the same tasks for every
candidate) with a taxonomy whose code set is M. For each trace it records a list of **failure instances**.
Instance *i* on candidate *c*'s trace for task *t* is a triple

    (s_i, M_i, r_i)      s_i = the step (turn) it sits on
                         M_i ⊆ M = the codes it carries (an instance no code fit carries the pseudo-code "(uncoded)")
                         r_i = 1 if the recovery reader marked it corrected or contained, 0 if unrecovered

*Corrected*: a later step replaced the wrong thing and the output does not carry it. *Contained*: the output
does not carry it and nothing corrected it. An instance the reader could not settle counts as unrecovered:
missing evidence is not recovery.

Derived sets used below:

| symbol | definition |
|---|---|
| `codes(c,t)` | `⋃_i M_i` over the trace's instances: each code once, however often it was cited |
| `codes(c,t,s)` | `⋃ M_i` over the instances at step *s* |
| `s_last(t)` | the trace's final step |
| `rate(c,m)` | `(1/T) Σ_t 1[m ∈ codes(c,t)]`, the share of judged tasks on which code *m* fired |
| `g(c,t) ∈ {0,1}` | the gold outcome (1 = pass); read only by the reference row and by the measure |

A judged trace with no instance gives empty sets and contributes 0. A trace that could not be judged is left
out of every sum and of T: "not judged" is not "no failure found".

**Two inputs, same formulas.** Every baseline is computed twice: on **every instance**, and on
**unrecovered instances only** (every instance with `r_i = 1` deleted before step 1 of the formula). Nothing
else changes between the two.

**Instances no code fit.** `results.md` reports each baseline both ways: *every kept instance* keeps
`(uncoded)` as a code of its own; *coded instances only* deletes those instances first. The profile formulas
(breadth, worst mode, patterns) read codes and use the coded-only form. `best_methods.md` and
`compared_scoring.md` use *every kept instance*.

## The reference: gold on the judged tasks

1. For each task, read the gold outcome `g(c,t)`.
2. `G(c) = (1/T) Σ_t g(c,t)`, the pass rate on the judged tasks. Higher is better.

It is not a trace method. Its agreement with the generalization set is **the bar**: the judged tasks' own
outcomes are the cheapest predictor of the larger set, and a trace formula has to match or beat them.

## Baseline formulas (lower is better)

### Per-task flags

**Incidence.**

1. For each task, flag it if anything failed: `f(c,t) = 1[codes(c,t) ≠ ∅]`.
2. `I(c) = (1/T) Σ_t f(c,t)`: the share of tasks on which anything failed.

On unrecovered instances this is **unrecovered incidence**: the share of tasks whose trace has at least one
failure the program never recovered from.

**Last-turn incidence.**

1. Find the trace's final step `s_last(t)`.
2. Flag the task if a code fired there: `f(c,t) = 1[codes(c,t,s_last(t)) ≠ ∅]`.
3. `I_last(c) = (1/T) Σ_t f(c,t)`: the share of tasks with something still wrong at the final step, after which
   nothing could fix it.

### Counts

**Amplitude.**

1. For each task, count the distinct codes: `k(c,t) = |codes(c,t)|`.
2. `A(c) = (1/T) Σ_t k(c,t)`. Equivalently `A(c) = Σ_m rate(c,m)`.

**Step-amplitude.**

1. For each task, collect the (step, code) pairs that fired: `U(c,t) = {(s,m) : m ∈ codes(c,t,s)}`.
2. `A_step(c) = (1/T) Σ_t |U(c,t)|`: a code counts once for every step it fires at.

**Damped PIE** (β = 0.5, a fixed constant kept as a recorded baseline).

1. `k = |codes(c,t)|`.
2. Inclusion-exclusion over the task's codes, a subset of size *j* weighted `β^(j−1)`, has the closed form
   `d(c,t) = (1 − (1−β)^k) / β`. With β = 0.5 a task with 1, 2, 3, 4 codes contributes 1, 1.5, 1.75, 1.875.
3. `D(c) = (1/T) Σ_t d(c,t)`. At β → 0 this is amplitude, at β = 1 incidence.

**Containment** (the propagation discount).

1. Take the (step, code) pairs `U(c,t)` and the set of steps that fired, `S(c,t) = {s : (s,m) ∈ U(c,t)}`.
2. A pair `(s,m)` is **contained** when later steps exist (`s < s_last(t)`) and no code fired at any of them
   (no `s' ∈ S(c,t)` with `s' > s`). The last step is never contained.
3. `A_con(c) = (1/T) Σ_t |{(s,m) ∈ U(c,t) : not contained}|`: step-amplitude minus the firings the program's own
   later steps ran clean after.

### Profile shape

| formula | steps |
|---|---|
| **breadth** | 1. compute `rate(c,m)` for every code; 2. `B(c) = |{m : rate(c,m) > 0}|`, how many codes the candidate ever triggers |
| **worst mode** | 1. compute `rate(c,m)`; 2. `W(c) = max_m rate(c,m)` |
| **patterns** | 1. collect the non-empty code sets `codes(c,t)`; 2. `P(c)` = how many distinct sets there are |

## Recovery-dependent formulas

These use the verdicts as a quantity, not only as a filter.

**Recovery-weighted amplitude** (γ ∈ {1, 2, 3}, fixed constants kept as recorded baselines).

1. A unit is a (step, code) pair `u = (s,m)`. On task *t* the unit is **recovered** only if every instance
   carrying it was: `rec_u(c,t) = ∧ { r_i : s_i = s, m ∈ M_i }`.
2. Over the candidate's tasks: `appeared_u(c)` = tasks on which *u* fired, `recovered_u(c)` = those on which it
   was recovered.
3. Recovery share `ρ_u(c) = recovered_u(c) / appeared_u(c)`. If *u* appeared on fewer than 3 tasks, use the
   candidate's overall share `Σ_u recovered_u / Σ_u appeared_u` instead.
4. Weight `w_u(c) = 1 − ρ_u(c)^γ`: a unit the candidate always recovers from weighs 0, one it never recovers
   from weighs 1.
5. `A_rw(c) = (1/T) Σ_u w_u(c) · appeared_u(c)`.

A pooled variant (one weight per unit for every candidate) was ≤ −0.5 on GEPA·HoVer and is not reported.

**Profile risk** (unrecovered incidence predicted from the profile).

1. For each code *m*: `app(m)` = the candidate's instances carrying *m*, `unr(m)` = those left unrecovered.
2. Consequence `q_c(m) = unr(m) / app(m)`, the candidate's own share of *m*-instances left unrecovered.
3. Task risk: the largest consequence among the codes on the task, `ρ(c,t) = max_{m ∈ codes(c,t)} q_c(m)`
   (0 for a task with no code).
4. `R(c) = (1/T) Σ_t ρ(c,t)`.

A noisy-OR combination, `1 − Π_m (1 − q_c(m))`, did worse: modes on the same task recover jointly (on GEPA·HoVer
SP_06 recovers 69% of the time alone and 36% next to SP_14), so treating them as independent risks over-counts
candidates whose traces carry many codes.

**Gold-discounted incidence** (not outcome-free: it reads the judged tasks' gold; w = 0.5).

1. Flag the task if it has an unrecovered instance.
2. A flagged task counts 1 if the candidate failed it (`g(c,t) = 0`) and *w* if it passed; an unflagged task 0.
3. `I_g(c) = (1/T) Σ_{t flagged} [1 if g(c,t) = 0 else w]`.

It sits within noise of the plain flag on every set tried, and spends gold to get there. It is never a
candidate for the best method.

## From scores to a measure

Every formula gives one number per candidate. Candidates are ranked by it (ascending: lower is better; gold
descending) and the ranking is compared with the ranking by pass rate on a **target**: the generalization set
(tasks disjoint from the judged ones, whose outcomes no formula reads) or, as a same-task check, the judged
set's own gold.

**Kendall tau-b with tied pairs dropped.**

1. Take every pair of candidates (a, b): `n(n−1)/2` pairs for n candidates.
2. Drop the pair if the formula gives a and b the same score, or the target gives them the same pass rate.
3. A remaining (**resolved**) pair is **concordant** if the formula and the target order it the same way,
   **discordant** otherwise.
4. `tau = (concordant − discordant) / (concordant + discordant)`.

+1: every resolved pair ordered like the target; −1: every one reversed; 0: no relation.

**Resolved pairs** = concordant + discordant: how many of the `n(n−1)/2` pairs the tau rests on (66 for 12
candidates, 36 for 9, 21 for 7). +0.6 on 8 pairs is two pairs from +0.1.

**Top-1.** Whether the candidate the formula ranks first is the one the target ranks first. Ties in the formula
are broken by candidate id, so a formula that ties many candidates gets an arbitrary answer; the resolved-pairs
column shows when that happens.

**Top-3.** How many of the formula's best three are among the target's best three, 0/3 to 3/3. With 7
candidates 3/3 is easy, with 12 it is not.

For the gold row, "vs judged gold" is +1.000 by construction, and "vs gen gold" is the bar.

## Reading a score as a solve rate

Incidence, last-turn incidence (on either input) and profile risk are shares of judged tasks, so `1 − score`
is the share of judged tasks the traces say were solved. It can be checked as a number, not only as an order:

1. For each candidate, the reading `1 − score(c)` and the actual solve rate `solved(c)` on the target.
2. Absolute gap `|(1 − score(c)) − solved(c)|`.
3. `distance = (100/n) Σ_c |(1 − score(c)) − solved(c)|`, in percentage points.

The reference row applies the same steps to the judged tasks' own pass rate against the generalization set,
`(100/n) Σ_c |G(c) − solved_gen(c)|`: the part of the gap that comes from which tasks were drawn. Counting
formulas and the profile-shape formulas are not on this scale and are not read this way. Per-candidate numbers
are in `compared_scoring.md`.

## Choosing the best method

`best_methods.md` names one formula per input by a rule fixed before the table was read:

1. For each formula and each of the five main experiments, compute tau against the generalization set.
2. Average the five taus.
3. In each input (every instance / unrecovered instances plus the recovery-dependent formulas), the formula
   with the highest average is the best. Gold-discounted incidence is excluded because it reads gold.

The choice is made on the same experiments it is reported on, so the winning mean is optimistic by roughly
its gap to the next row. LiveCodeBench's 150-task run is shown beside the five and enters neither the mean nor
the choice.

## SWE-bench conventions

- **Instrument.** RedoAdamast's single-pass judge (one call per trace, taxonomy fixed) and its recovery reader, both
  on Gemini 3.8 Flash; the other four experiments use a two-reader-plus-decider judge and a Claude Sonnet 5 reader.
- **The output is the submitted patch.** The reader's quotes about the output are checked against the patch that
  follows the last turn (`code/recheck_recovery_output.py`, run on the reader's stored answers, no new model call).
- **One trace read with medium reasoning.** Its answer ran past the output limit twice at the default high setting.
- **One run per model per task** in every set, as everywhere else.

## Studies beyond the baselines

- `first_last_study.md` (the first four experiments): scores that read only each trace's first and last failure instance, fixed mode
  filters (pooled across candidates or per candidate), a 75-cell grid of data-estimated weights with a
  leave-one-experiment-out check, and one entropy-weighted setup without recovery.
- `results_ablation.md`: how the agreement moves with which and how many judged tasks are read, and with the
  generalization set's size.
