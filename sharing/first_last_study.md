# The first-and-last failure-instance study

Run on 2026-09-28 and regenerated here on the four main experiments (LiveCodeBench on its 50-task judged split).
The question: does a trace's *first* and *last* failure instance carry the ranking signal, so that a score can
ignore everything between them? Every score below is computed per candidate from its own traces, then compared
with the generalization set exactly as in `formulas.md` (Kendall tau-b, ties dropped; top-1). Exploratory: none
of these formulas is a recorded method, and Part B's rules were chosen on Models·HoVer.

## Inputs and the two preparation steps

For candidate *c* on judged task *t* the judge left a list of failure instances
`P(c,t) = [(s_i, M_i, r_i)]`: the turn `s_i`, the set of codes `M_i`, and the recovery verdict `r_i`
(`r_i = 1` if corrected or contained, `0` if unrecovered). `F` is the experiment's set of formatting codes:

| experiment | formatting codes removed |
|---|---|
| GEPA candidates · HoVer | `SP_09` Omission of Mandatory Output Completion Marker, `SP_10` Omission of Required Output Sections or Headers, `SP_13` Non-Compliance with Required Element Formatting Rules |
| Models · HoVer (judged set b) | `SP_04` OUTPUT_SCHEMA_DELIMITER_MISMATCH, `SP_08` UNREQUESTED_CONTAINER_OR_WRAPPER_STRUCTURE, `SP_09` MISSING_OR_MALFORMED_OUTPUT_TERMINATION, `SP_10` MALFORMED_SECTION_OR_FIELD_DELIMITER, `SP_11` OMISSION_OF_REQUIRED_OUTPUT_FIELD |
| Models · Terminal-Bench 2.0 | `SP_01` output_placed_in_reasoning_block, `SP_02` missing_required_schema_field, `SP_03` malformed_output_syntax_or_formatting |
| Models · LiveCodeBench | none |

**Step 1, remove formatting.** For every instance keep `M_i' = M_i \ F`; drop the instance if `M_i'` is empty.
An instance no code fit keeps its pseudo-code `(uncoded)`, which is never in `F`.

    P'(c,t) = [ (s_i, M_i \ F, r_i)  for every i with M_i \ F ≠ ∅ ]

**Step 2, take the endpoints.** Order `P'(c,t)` by turn, and within a turn by the judge's listing order. The
first element is `first(c,t)`, the last is `last(c,t)`. A trace with one instance has `first = last`. A trace
with none has no endpoints and contributes 0 to every score.

## Part A: endpoints against every instance

Each row is a share of the T judged tasks (lower is better):

1. incidence, every instance: `(1/T) Σ_t 1[P(c,t) ≠ ∅]`
2. incidence, formatting removed: `(1/T) Σ_t 1[P'(c,t) ≠ ∅]`. This is also the endpoint flag without recovery,
   because a trace has endpoints exactly when `P'(c,t)` is non-empty.
3. unrecovered incidence, every instance: `(1/T) Σ_t 1[∃ i ∈ P(c,t): r_i = 0]`
4. unrecovered incidence, formatting removed: the same on `P'(c,t)`. Taking endpoints of the unrecovered
   instances gives the same flag.
5. first & last, recovery checked on the endpoints: `(1/T) Σ_t 1[r(first(c,t)) = 0 or r(last(c,t)) = 0]`. Only
   the two endpoints' verdicts are read; an unrecovered instance in the middle does not count.

Tau-b against the generalization set; `·1` = the formula's top candidate is the generalization set's top.

| | GEPA·HoVer (12×50) | Models·HoVer (9×50) | Models·TB (7×19) | Models·LCB (9×50) | **mean** |
|---|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.785* | *+0.444* | *+0.579* | *+0.765* | *+0.643* |
| incidence, every instance (no recovery) | -0.409 | +0.333 | +0.647 | +0.771 | +0.336 |
| incidence, formatting removed (no recovery) | -0.544 | +0.515 | +0.867 | +0.771 | +0.402 |
| unrecovered incidence, every instance | +0.828 ·1 | +0.543 | +1.000 ·1 | +0.771 | +0.785 |
| unrecovered incidence, formatting removed | +0.797 ·1 | +0.543 | +1.000 ·1 | +0.771 | +0.778 |
| first & last, recovery checked on the two endpoints | +0.841 | +0.529 | +1.000 ·1 | +0.771 | +0.786 |

Instances removed as formatting: GEPA·HoVer 158 of 3043; Models·HoVer 299 of 1560; Models·TB 103 of 1094; Models·LCB 0 of 175.

## Part B: fixed mode filters

A filter removes some modes from the endpoints, then the score is the share of tasks with an endpoint left.

1. For each position `p ∈ {first, last}` count how often each mode appears there:
   `n_p(m) = Σ_t 1[m ∈ M(p(c,t))]`, either **across candidates** (summed over every candidate, one count per
   mode) or **per candidate** (each candidate's own counts).
2. Choose the modes to drop at that position, `D_p`:
   *top k*: the k modes with the largest `n_p(m)`;
   *mean + k SD*: every mode with `n_p(m) > μ_p + k·σ_p`, where `μ_p` and `σ_p` are the mean and population
   standard deviation of the counts `{n_p(m)}` over the modes seen at that position.
3. Score: `(1/T) Σ_t 1[ ∃ p: M(p(c,t)) \ D_p ≠ ∅ (and, with recovery, r(p(c,t)) = 0) ]`.

Three inputs: **no recovery** (endpoints of `P'`); **recovery after** (same endpoints, an endpoint counts only
if it is unrecovered); **recovery first** (endpoints of the unrecovered instances of `P'`). † marks a tie at the
top-k cut-off (for per-candidate rules, in at least one candidate), where the dropped set is partly arbitrary.
Resolved pairs are shown when fewer than 85% of the pairs are resolved.

**No recovery**

| rule | GEPA·HoVer | Models·HoVer | Models·TB | Models·LCB | mean, 3 untuned | mean, all 4 |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.785* | *+0.444* | *+0.579* | *+0.765* | | |
| no filter | -0.544 | +0.515 | +0.867 (15/21) | +0.771 | +0.365 | +0.402 |
| across candidates: drop the top 1 mode | +0.158 | +0.543 | +0.700 | +0.647 ·1 | +0.502 | +0.512 |
| across candidates: drop the top 2 modes | -0.593 | +0.657 ·1 | +0.556 | +0.588 | +0.184 | +0.302 |
| across candidates: drop the top 3 modes | +0.302 | +0.471 | -0.125 (16/21) | +0.600 (30/36) | +0.259 | +0.312 |
| across candidates: drop modes above mean + 1 SD | +0.397 | +0.412 | +0.556 | +0.588 ·1 | +0.514 | +0.488 |
| across candidates: drop modes above mean + 1.5 SD | -0.593 | +0.394 | +0.882 (17/21) | +0.647 ·1 | +0.312 | +0.333 |
| per candidate: drop the top 1 mode | +0.143 † | +0.588 | +0.647 (17/21) † | +0.697 † | +0.496 | +0.519 |
| per candidate: drop the top 2 modes | +0.161 † | +0.543 | +0.556 † | +0.697 † | +0.471 | +0.489 |
| per candidate: drop modes above mean + 1 SD | +0.048 | +0.257 | +0.300 | +0.697 | +0.348 | +0.325 |
| per candidate: drop modes above mean + 1.5 SD | +0.079 | +0.294 | +0.867 (15/21) | +0.697 | +0.548 | +0.484 |

**Recovery after: an endpoint counts only if unrecovered**

| rule | GEPA·HoVer | Models·HoVer | Models·TB | Models·LCB | mean, 3 untuned | mean, all 4 |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.785* | *+0.444* | *+0.579* | *+0.765* | | |
| no filter | +0.841 | +0.529 | +1.000 ·1 | +0.771 | +0.871 | +0.786 |
| across candidates: drop the top 1 mode | +0.714 | +0.471 ·1 | +0.600 | +0.588 ·1 | +0.634 | +0.593 |
| across candidates: drop the top 2 modes | +0.123 | +0.758 ·1 | +0.067 (15/21) | +0.588 | +0.259 | +0.384 |
| across candidates: drop the top 3 modes | +0.390 | +0.562 ·1 | -0.857 (14/21) | +0.655 (29/36) | +0.063 | +0.188 |
| across candidates: drop modes above mean + 1 SD | +0.279 | +0.706 ·1 | +0.067 (15/21) | +0.600 ·1 | +0.315 | +0.413 |
| across candidates: drop modes above mean + 1.5 SD | +0.123 | +0.818 ·1 | +0.176 (17/21) | +0.588 ·1 | +0.296 | +0.426 |
| per candidate: drop the top 1 mode | +0.567 † | +0.882 ·1 | +0.700 † | +0.697 † | +0.655 | +0.711 |
| per candidate: drop the top 2 modes | +0.344 † | +0.724 ·1 (29/36) | +0.067 (15/21) † | +0.697 † | +0.369 | +0.458 |
| per candidate: drop modes above mean + 1 SD | +0.424 | +0.724 ·1 (29/36) | +0.684 | +0.697 | +0.602 | +0.632 |
| per candidate: drop modes above mean + 1.5 SD | +0.705 | +0.657 ·1 | +0.900 | +0.697 | +0.767 | +0.740 |

**Recovery first: endpoints of the unrecovered instances**

| rule | GEPA·HoVer | Models·HoVer | Models·TB | Models·LCB | mean, 3 untuned | mean, all 4 |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.785* | *+0.444* | *+0.579* | *+0.765* | | |
| no filter | +0.797 ·1 | +0.543 | +1.000 ·1 | +0.771 | +0.856 | +0.778 |
| across candidates: drop the top 1 mode | +0.774 ·1 | +0.824 | +0.882 ·1 (17/21) | +0.588 ·1 | +0.748 | +0.767 |
| across candidates: drop the top 2 modes | +0.810 ·1 | +0.600 | +0.412 (17/21) | +0.588 | +0.603 | +0.602 |
| across candidates: drop the top 3 modes | +0.587 ·1 | +0.429 ·1 | +0.000 (14/21) | +0.655 (29/36) | +0.414 | +0.418 |
| across candidates: drop modes above mean + 1 SD | +0.587 ·1 | +0.600 | +0.412 (17/21) | +0.588 | +0.529 | +0.547 |
| across candidates: drop modes above mean + 1.5 SD | +0.806 ·1 | +0.600 | +1.000 ·1 | +0.588 ·1 | +0.798 | +0.749 |
| per candidate: drop the top 1 mode | +0.733 ·1 † | +0.697 ·1 † | +0.889 ·1 † | +0.697 † | +0.773 | +0.754 |
| per candidate: drop the top 2 modes | +0.900 ·1 † | +0.647 | +0.467 (15/21) † | +0.697 † | +0.688 | +0.678 |
| per candidate: drop modes above mean + 1 SD | +0.661 | +0.647 ·1 | +0.444 | +0.697 | +0.601 | +0.612 |
| per candidate: drop modes above mean + 1.5 SD | +0.585 ·1 (53/66) | +0.714 | +1.000 ·1 | +0.697 | +0.761 | +0.749 |

The rules were picked by looking at Models·HoVer, so the column that tests them is the mean over the other three.

## Part C: a grid in which every weight is estimated from the data

A task's value combines its endpoints' modes through three choices; the score is the mean task value,
`S(c) = (1/T) Σ_t V(c,t)`. All 5 × 5 × 3 = 75 combinations were run.

**Endpoint occurrences.** For position `p` and mode `m`, `o_c(m,p)` is how many of *c*'s tasks have `m` at that
endpoint, `u_c(m,p)` how many of those endpoints were unrecovered, and `N_c(p) = Σ_m o_c(m,p)`.

**Shrinkage used below (empirical Bayes, beta-binomial method of moments).** Given groups g with counts
`(k_g, n_g)`:

1. pooled rate `p₀ = Σ_g k_g / Σ_g n_g`, with `N = Σ_g n_g` and G groups;
2. observed spread `v = Σ_g (n_g/N)·(k_g/n_g − p₀)²`;
3. spread beyond binomial noise `τ² = v − p₀(1−p₀)·G/N`;
4. if `τ² ≤ 0` every group gets `p₀`; otherwise `α = max(0, p₀(1−p₀)/τ² − 1)`;
5. shrunk rate `(k_g + α·p₀) / (n_g + α)`.

No constant is set by hand: α comes from the data.

**Recovery weight `q` (5 arms).** An unrecovered endpoint has weight 1. A recovered endpoint has weight
`q = ` the consequence rate of its (mode, position), the share of such endpoints left unrecovered:

| arm | recovered endpoint weighs |
|---|---|
| no recovery | 1 (verdicts ignored) |
| recovery-weighted, own | `q_c(m,p)`: c's own rate `u_c/o_c`, shrunk across c's modes at that position |
| recovery-weighted, pooled | `q(m,p) = Σ_c u_c(m,p) / Σ_c o_c(m,p)`, one rate for every candidate |
| recovery-weighted, combined | c's rate shrunk toward the pooled rate across candidates |
| unrecovered instances only | endpoints are taken from the unrecovered instances, so every endpoint weighs 1 |

**Mode weight `w` (5 levels).**

| level | `w_c(m,p)` |
|---|---|
| none | 1 |
| rarity, own | `−ln( o_c(m,p) / N_c(p) )` |
| rarity, pooled | `−ln( Σ_c o_c(m,p) / Σ_c N_c(p) )` |
| rarity, combined | `−ln` of c's share shrunk across candidates |
| spread across candidates | `σ/μ` of the per-task rates `o_c(m,p)/T` over candidates, the same for every candidate |

**Combiner (3 levels).** With `v = w·q` for each (endpoint, mode) pair of the task:
*max*: `V = max v`; *sum over modes*: `V = Σ_m max_p v(m,p)` (a mode at both endpoints counts once);
*sum over endpoints*: `V = Σ v` (a one-instance trace counted once).

**Leave one experiment out.** For each experiment, pick the cell with the best mean tau on the other three and
report its tau on the held-out one. This is the only honest estimate of how a cell chosen from this grid would do
on a new experiment.

**Each factor level, averaged over the other two factors** (mean tau over the four experiments; in brackets the
lowest tau any cell with that level reaches on any experiment)

| factor | level | mean tau | worst case |
|---|---|---:|---:|
| recovery weight | no recovery | +0.432 | -0.544 |
| recovery weight | recovery-weighted, own | +0.605 | +0.182 |
| recovery weight | recovery-weighted, pooled | +0.552 | +0.000 |
| recovery weight | recovery-weighted, combined | +0.590 | +0.303 |
| recovery weight | unrecovered instances only | +0.744 | +0.389 |
| mode weight | none | +0.603 | -0.544 |
| mode weight | rarity, own | +0.595 | -0.030 |
| mode weight | rarity, pooled | +0.598 | +0.091 |
| mode weight | rarity, combined | +0.587 | -0.030 |
| mode weight | spread across candidates | +0.540 | -0.242 |
| combiner | max | +0.572 | -0.544 |
| combiner | sum over modes | +0.568 | -0.091 |
| combiner | sum over endpoints | +0.614 | -0.152 |

**The twelve best cells by mean tau** (`·1` = top-1 correct)

| recovery weight | mode weight | combiner | GEPA·HoVer | Models·HoVer | Models·TB | Models·LCB | mean |
|---|---|---|---:|---:|---:|---:|---:|
| unrecovered instances only | rarity, combined | sum over endpoints | +0.667 | +0.722 | +0.905 | +0.833 | +0.782 |
| unrecovered instances only | none | max | +0.797 ·1 | +0.543 | +1.000 ·1 | +0.771 | +0.778 |
| unrecovered instances only | rarity, pooled | sum over endpoints | +0.667 | +0.778 | +0.905 | +0.722 | +0.768 |
| unrecovered instances only | rarity, own | sum over endpoints | +0.727 | +0.667 | +0.810 | +0.833 | +0.759 |
| unrecovered instances only | rarity, pooled | sum over modes | +0.727 ·1 | +0.667 | +0.810 | +0.833 | +0.759 |
| unrecovered instances only | none | sum over endpoints | +0.688 | +0.833 | +0.714 | +0.778 | +0.753 |
| unrecovered instances only | spread across candidates | sum over endpoints | +0.697 | +0.778 | +0.810 | +0.722 | +0.752 |
| unrecovered instances only | rarity, combined | sum over modes | +0.636 | +0.722 | +0.810 | +0.833 | +0.750 |
| unrecovered instances only | rarity, own | max | +0.879 ·1 | +0.500 | +0.714 | +0.889 | +0.745 |
| unrecovered instances only | none | sum over modes | +0.419 | +0.833 | +0.900 | +0.829 | +0.745 |
| recovery-weighted, own | none | max | +0.636 | +0.556 | +1.000 ·1 | +0.771 | +0.741 |
| unrecovered instances only | rarity, pooled | max | +0.636 ·1 | +0.611 | +0.810 | +0.889 | +0.736 |

**Reference cells**

| recovery weight | mode weight | combiner | GEPA·HoVer | Models·HoVer | Models·TB | Models·LCB | mean |
|---|---|---|---:|---:|---:|---:|---:|
| unrecovered instances only | none | max | +0.797 ·1 | +0.543 | +1.000 ·1 | +0.771 | +0.778 |
| no recovery | none | max | -0.544 | +0.515 | +0.867 | +0.771 | +0.402 |
| no recovery | none | sum over modes | -0.062 ·1 | +0.543 | +0.529 | +0.882 | +0.473 |
| unrecovered instances only | none | sum over modes | +0.419 | +0.833 | +0.900 | +0.829 | +0.745 |

*unrecovered instances only · none · max* is the unrecovered incidence of Part A row 4; *no recovery · none · max* is row 2.

**Leave one experiment out**

| held out | cell chosen on the other three | its mean there | tau on the held-out experiment | bar |
|---|---|---:|---:|---:|
| GEPA candidates · HoVer | unrecovered instances only · none · sum over modes | +0.854 | +0.419 | +0.785 |
| Models · HoVer (judged set b) | unrecovered instances only · none · max | +0.856 | +0.543 | +0.444 |
| Models · Terminal-Bench 2.0 | unrecovered instances only · none · sum over endpoints | +0.766 | +0.714 | +0.579 |
| Models · LiveCodeBench | unrecovered instances only · rarity, pooled · sum over endpoints | +0.783 | +0.722 | +0.765 |
| **mean** | | | **+0.600** | +0.643 |

## Part D: Setup 1, rarity-weighted endpoint modes without recovery

1. `P'(c,t)` as above (step 1) and its endpoints (step 2).
2. Endpoint modes `E(c,t) = M(first(c,t)) ∪ M(last(c,t))`.
3. Mode counts `n_c(m) = Σ_t 1[m ∈ E(c,t)]`, total `N_c = Σ_m n_c(m)`, shares `π_c(m) = n_c(m)/N_c`.
4. Weight `w_c(m) = −ln π_c(m)`: a mode common for this candidate weighs little, a rare one weighs more.
5. Task value `V(c,t) = Σ_{m ∈ E(c,t)} w_c(m)`; score `S(c) = (1/T) Σ_t V(c,t)`.

Summing step 5 over tasks gives `S(c) = (N_c/T) · H(π_c)`, with `H(π) = −Σ_m π(m) ln π(m)` the entropy of the
candidate's endpoint-mode distribution: the score is the number of endpoint modes per task times how evenly they
spread. The script checks the identity on every candidate.

| experiment | candidates × judged tasks | tau vs generalization | top-1 | resolved pairs | bar |
|---|---|---:|---|---:|---:|
| GEPA candidates · HoVer | 12 × 50 | +0.121 | no | 66 of 66 | +0.785 |
| Models · HoVer (judged set b) | 9 × 50 | +0.444 | no | 36 of 36 | +0.444 |
| Models · Terminal-Bench 2.0 | 7 × 19 | +0.333 | no | 21 of 21 | +0.579 |
| Models · LiveCodeBench | 9 × 50 | +0.833 | no | 36 of 36 | +0.765 |
| **mean** | | **+0.433** | 0 of 4 | | +0.643 |

Generated by `scripts/first_last_study.py` from the recorded judge and recovery runs; no model call.
