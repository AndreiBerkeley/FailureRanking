# The scoring formulas

Four formulas are reported. Each turns one candidate's judged traces into one number, from
the judge's mapping and nothing else; the candidates are then ranked by that number. None
has a parameter. The formulas are compared to each other and to gold by the measure in §5.

## 1. What the judge provides

The judge reads every trace of candidate *c* on the judged task set *𝒯* (|𝒯| = *T*, the
same tasks for every candidate) holding a taxonomy with code set *M*. For each trace it
records a set of failure points; each point carries a step and one or more codes. From
those points:

| symbol | definition |
|---|---|
| codes(c,t) ⊆ M | the distinct codes that fired anywhere in *c*'s trace on task *t* |
| k(c,t) = \|codes(c,t)\| | how many distinct codes fired on that trace |
| g(c,t) ∈ {0,1} | the gold outcome of *c* on *t* (pass = 1) — read only by the reference and by the measure, never by a trace method |

A code cited several times in one trace still enters codes(c,t) once, so a repetitive judge
cannot inflate a candidate. A judged trace with no point contributes k = 0. A trace that was
not judged contributes nothing — it is absent from the sum and *T* excludes it — rather
than contributing 0, because "not judged" is not "no failure found".

## 2. Gold — the reference, not a competitor

A_gold(c) = (1/T) · Σ_{t∈𝒯} g(c,t)                     higher is better

The pass rate on the judged tasks. It reads outcomes, so it can never be part of a
trace-based claim; it is reported because it says what scoring these same tasks — the thing
the trace methods are trying to replace — predicts about the large set.

## 3. Amplitude — how much goes wrong

A_amp(c) = (1/T) · Σ_{t∈𝒯} k(c,t)                       lower is better

The mean number of distinct failure codes per judged trace. Equivalently, writing
r_m(c) = (1/T)·Σ_t 1[m ∈ codes(c,t)] for the share of *c*'s judged traces on which code *m*
fired,

A_amp(c) = Σ_{m∈M} r_m(c)

— the sum of the per-code firing rates. The two readings are the same number: counting codes
task by task and counting tasks code by code cannot be told apart at this level. Amplitude
does not know where a code fired, what it fired with, or whether it cost the outcome.

## 4. Incidence — did the task fail at all

A_inc(c) = (1/T) · Σ_{t∈𝒯} 1[ k(c,t) > 0 ]              lower is better

The share of judged traces on which anything fired. One per failing trace however much
went wrong on it, so a candidate that ruins a few tasks is separated from one that lightly
marks many — which amplitude adds into the same total. A_inc(c) ≤ A_amp(c) always, with
equality only when no trace ever carries two codes.

## 5. Combinations — failures that arrive together cost more

A_comb(c) = (1/T) · Σ_{t∈𝒯} ( 2^{k(c,t)} − 1 )          lower is better

A trace showing *k* codes contributes the number of its non-empty code subsets, 2^k − 1:
one code → 1, two → 3, three → 7. Three codes on one trace therefore cost 7 where the same
three codes spread over three traces cost 3. This is the crudest reading of "co-occurring
failures are worse than the same failures apart" that is not already amplitude: it is
exponential in the per-trace count and has no strength parameter. Counting each code
separately instead would give amplitude exactly, since Σ_t k(c,t) is linear in the counts.

## 6. From scores to rankings, and the measure

**Ranking.** Candidates are sorted by the score: descending for gold, ascending for the
three trace methods (fewer, rarer, less-clustered failures rank higher). Two candidates with
equal scores are tied.

**Kendall tau-b, tied pairs dropped.** For two rankings *R₁*, *R₂* of the same *n*
candidates, consider every unordered candidate pair {a, b} (n(n−1)/2 pairs: 36 for nine
candidates, 66 for twelve). A pair is *concordant* if both rankings order a and b the same
way, *discordant* if they order them oppositely, and *dropped* if either ranking ties them.
With C concordant and D discordant pairs,

τ = (C − D) / (C + D)

so τ = +1 is perfect agreement on every ordered pair, −1 perfect reversal, 0 no relation.
Dropping tied pairs rather than counting them as half-right is what makes a tied gold-50
visible: it is compared on fewer pairs, and the pair count is stated where it matters.

**The three comparisons.** For every method, τ is computed against two gold rankings:

| column | R₁ | R₂ |
|---|---|---|
| judge vs gold-50 | the method's ranking from the judged traces | A_gold on the same judged tasks |
| judge vs gold-gen | the method's ranking | pass rate on the generalization tasks (disjoint, never judged) |
| gold-50 vs gold-gen | A_gold on the judged tasks | pass rate on the generalization tasks |

The third column does not depend on the method. It is the bar: how well scoring the judged
tasks themselves predicts the large set. A trace method that beats it is extracting more
about the candidate from *T* traces than *T* outcomes carry.

**Top-1.** Whether the method's first-ranked candidate is the first-ranked candidate under
gold-gen.

## 7. Worked example

Nine candidates, 50 judged tasks. Candidate *c* has points on 21 of its 50 traces: 15 traces
with one code, 5 with two, 1 with three. Then

- k sums to 15·1 + 5·2 + 1·3 = 28, so A_amp = 28/50 = 0.56;
- 21 traces carry anything, so A_inc = 21/50 = 0.42;
- subsets sum to 15·1 + 5·3 + 1·7 = 37, so A_comb = 37/50 = 0.74.

Rank all nine by each score (ascending), rank them by gold-50 and by gold-gen (descending),
and count concordant / discordant pairs over the 36 candidate pairs, dropping any pair that
is tied in either ranking being compared. If amplitude orders 34 of 35 untied pairs the way
gold-gen does, τ = (34 − 1)/35 = +0.943.

## 8. What was run but is not reported here

`code/BASELINES.md` lists eleven parameter-free entries; `code/methods_scripts/run_baselines.py`
computes all of them. Breadth, worst-mode and distinct-patterns are dominated by or redundant
with the four above; step-amplitude and containment need per-step firings and coincide with
amplitude on a one-step program; recovery reads gold and is therefore not a trace-only method.
Their rows remain in the raw tables in each `results/` directory.
