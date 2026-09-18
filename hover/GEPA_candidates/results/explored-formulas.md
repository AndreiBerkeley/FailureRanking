# Formulas explored on the GEPA set (2026-09-18) — what was tried and the best it reached

All on the current instrument: pointjudge-1-tax15 (600 traces, 3,043 points) with
recovery-2-tax15. Tau-b vs gold-gen (500 tasks), ties dropped, 12 candidates. Every number
here comes from an offline computation over the recorded mapping and recovery run; no gold
enters any score. The reference points: gold-50 vs gold-gen **+0.785**; unrecovered
incidence **+0.828**; last-turn incidence **+0.833**.

## 1. Recovery-weighted (code, step) units — `recovery-weighted_recovery-2-tax15.md`

w_u(c) = 1 − (recovered_u / appeared_u)^γ per unit u = (code, turn); A(c) = (1/T) Σ_u w_u · appeared_u.
Per-candidate and pooled recovery shares, γ ∈ {1, 2, 3}. **Best +0.18** (per-candidate, γ=1);
pooled −0.52 at every γ. Larger γ moves the score toward raw amplitude (−0.42): on this set
the recovered points carry no information the unrecovered ones do not.

## 2. Per-task units other than the plain flag

One number per task, mean over the 50 tasks:

| unit | tau |
|---|---:|
| any unrecovered point (incidence) | +0.828 |
| pattern-as-one-unit, weight 1 (a task with {A,B,C} counts as one ABC) | +0.828 (identical) |
| pattern-as-one-unit, weight = rarity of the pattern | +0.818 |
| pattern-as-one-unit, weight = its size (distinct-code amplitude) | +0.143 |
| unrecovered point on the last turn | +0.833 |
| unrecovered point on a query turn | +0.778 |
| unrecovered point carrying a query code (SP_04/08/11/14) | +0.806 |
| unrecovered point on a summary turn | −0.172 |
| earliest failing turn, mean over flagged tasks | +0.394 |
| number of distinct patterns (method 7) | +0.344 |

Every per-task flag lands at +0.78–0.83; anything that re-introduces size or code
composition drops.

## 3. Why the count- and code-weighted methods fail here

Amplitude = incidence × (unrecovered points per flagged task); that second factor has tau
**−0.24** on its own: the best candidate gets 4.6 unrecovered points per failed task, the
worst three 2.6–3.0, because the judge writes one point per violated instruction clause and
the GEPA-optimised instructions have more clauses. Turns hit per flagged task −0.08, distinct
codes 0.00. The share of a candidate's points in form codes has tau −0.63, in doc-status
(SP_06) −0.58, in query codes +0.67: code composition is a class signature that points the
wrong way for half the codes, so any weighting by code identity averages a +0.7 camp against
a −0.5 camp.

## 4. Failure-mode-centric aggregations

Per-mode unrecovered incidence per candidate, combined across modes: equal-weight mean
+0.14; Copeland across modes +0.16; Borda +0.18; weighted by pooled non-recovery +0.15;
ratio-to-pooled-mean −0.03; noisy-OR of weighted rates +0.12; worst mode −0.13. **Best
+0.18.** Per-mode taus split into two camps (SP_11 +0.81, SP_08 +0.63, SP_07 +0.59 vs
SP_12 −0.71, SP_13 −0.49, SP_14 −0.37, SP_06 −0.33).

## 5. Blame (Shapley) decomposition

One unit of blame per flagged task, split among its unrecovered points (equal split is the
Shapley value under "any unrecovered point sinks the task"; root-cause and turn-decay splits
also computed). Candidate total = incidence by construction; the per-mode blame profile is
the diagnostic: SP_06 26–34% of all blame, SP_14 15–19%, SP_08 9–17%, SP_11 10–13%; the two
most frequent codes (SP_02, SP_05) 2–9% because they are almost always recovered; form codes
≈ 3% together. Reweighting a candidate's blame by pooled mode influence: **−0.21**; by
pooled non-recovery: +0.61.

## 6. Profile risk: candidate's mode frequencies × mode consequence

Expected unrecovered incidence from the profile. Pooled consequence (noisy-OR −0.58, with
significant pair adjustments −0.64, exact-pattern rates −0.39; leave-one-candidate-out
−0.55 … −0.73). Candidate's own per-mode consequence: noisy-OR +0.06, max over the task's
modes +0.61. **Best +0.61.** The modes on a task are facets of one failure and recover
jointly (SP_06 recovers 69% alone, 36% next to SP_14; SP_11 63% alone, 6% next to SP_14; 14
of 54 pairs with ≥ 15 co-occurrences shift a member's recovery beyond binomial noise), so
independence over-counts risk for verbose candidates.

Context bases (code × turn, × co-occurring query codes, × number of other codes, × full
co-occurring set): the non-recovery of a unit stays candidate-dependent in every basis
(chi²/df across candidates 1.7–2.2, where 1 is homogeneous); the profile score stays negative
in all of them (−0.30 … −0.76). Recovery is a property of the candidate, not of the code.

## 7. Split-half transfer of the profile

40 random halves of the 50 tasks: per-type recovery learned on half A (per candidate),
applied to half B's appearances, vs the plain flag on A. Flag on A **+0.563**; profile A→B
+0.315 (family-set types) / +0.412 (root-family types). The profile's factors rest on 1–22
tasks per type per candidate and transfer worse than the collapsed number.

## 8. Recovery audit (hand-read, no gold)

Before the success rule (recovery-1 on the panel mapping, and set b on models): 10 of 100
recovered verdicts wrong, all of one kind — "the information is in a passage" while the
entity's own page was missing. After (recovery-2): 60 recovered read, 2 wrong (a false
"nothing is missing" claim whose consequence was the missed page); 20 unrecovered read, 0
wrong.

## Summary

| family | best tau vs gold-gen | where |
|---|---:|---|
| per-task flags (incidence, last-turn) | **+0.83** | §2 |
| profile risk with the candidate's own rates | +0.61 | §6 |
| containment (count form) | +0.35 | run_baselines |
| mode-centric aggregations | +0.18 | §4 |
| recovery-weighted units | +0.18 | §1 |
| amplitude, step-amplitude | +0.19 | run_baselines |
| pooled-consequence profiles, blame reweighting | ≤ 0 | §5–6 |
