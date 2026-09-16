# The scoring formulas

Six formulas are reported: gold (the reference) and five trace methods. Three read the
per-trace code sets (amplitude, incidence, combinations) and are reported on every
benchmark; two read *where* in the trace each code fired (step-amplitude, containment) and
are reported on hover, whose program has four steps — on livecodebench's one-step program
they reduce to amplitude, and the panel judge used for hover's optimizer candidates records
no steps. Each turns one candidate's judged traces into one number, from the judge's
mapping and nothing else; the candidates are then ranked by that number. None has a
parameter. The measure that compares them is in §8.

## 1. What the judge provides

The judge reads every trace of candidate *c* on the judged task set *𝒯* (|𝒯| = *T*, the
same tasks for every candidate) holding a taxonomy with code set *M*. For each trace it
records a set of failure points; each point carries a step and one or more codes. From
those points:

| symbol | definition |
|---|---|
| codes(c,t) ⊆ M | the distinct codes that fired anywhere in *c*'s trace on task *t* |
| k(c,t) = \|codes(c,t)\| | how many distinct codes fired on that trace |
| S(t) | the steps (turns) of the trace on *t*; the last one is the terminal step |
| codes(c,t,s) ⊆ codes(c,t) | the codes that fired at step *s* of that trace |
| down(s) ⊆ S(t) | the steps that consume step *s*'s output, directly or through the harness — every later step in a linear pipeline |
| g(c,t) ∈ {0,1} | the gold outcome of *c* on *t* (pass = 1) — read only by the reference and by the measure, never by a trace method |

A code cited several times in one trace still enters codes(c,t) once, so a repetitive judge
cannot inflate a candidate. A judged trace with no point contributes k = 0. A trace that was
not judged contributes nothing — it is absent from the sum and *T* excludes it — rather
than contributing 0, because "not judged" is not "no failure found".

## 2. Gold — the reference, not a competitor

A_gold(c) = (1/T) · Σ_{t∈𝒯} g(c,t)                     higher is better

where
- *c* — the candidate being scored (one model, or one instruction set);
- *𝒯* — the set of judged tasks, the same for every candidate; *t* ranges over it;
- *T* = |𝒯| — how many judged tasks *c* has, the divisor that makes the score a per-task mean;
- g(c,t) — the benchmark's gold outcome of *c* on task *t*: 1 if the run passed (every hidden
  test passed / all three titles retrieved), 0 otherwise.

The pass rate on the judged tasks. It reads outcomes, so it can never be part of a
trace-based claim; it is reported because it says what scoring these same tasks — the thing
the trace methods are trying to replace — predicts about the large set.

## 3. Amplitude — how much goes wrong

A_amp(c) = (1/T) · Σ_{t∈𝒯} k(c,t)                       lower is better

where
- *c*, *𝒯*, *t*, *T* — as above;
- codes(c,t) — the set of *distinct* failure codes the judge assigned anywhere in *c*'s trace
  on task *t* (a code cited twice in one trace is in the set once);
- k(c,t) = |codes(c,t)| — the size of that set: how many different failure codes fired on
  that trace, 0 when the judge found nothing.

The mean number of distinct failure codes per judged trace. Equivalently, writing
r_m(c) = (1/T)·Σ_t 1[m ∈ codes(c,t)] for the share of *c*'s judged traces on which code *m*
fired,

A_amp(c) = Σ_{m∈M} r_m(c)

where
- *M* — the taxonomy's set of codes; *m* ranges over it;
- r_m(c) = (1/T)·Σ_t 1[m ∈ codes(c,t)] — the firing rate of code *m* for candidate *c*: the
  share of *c*'s judged traces on which *m* fired; 1[·] is the indicator, 1 when the condition
  inside holds and 0 otherwise.

— the sum of the per-code firing rates. The two readings are the same number: counting codes
task by task and counting tasks code by code cannot be told apart at this level. Amplitude
does not know where a code fired, what it fired with, or whether it cost the outcome.

## 4. Incidence — did the task fail at all

A_inc(c) = (1/T) · Σ_{t∈𝒯} 1[ k(c,t) > 0 ]              lower is better

where
- *c*, *𝒯*, *t*, *T*, k(c,t) — as above;
- 1[k(c,t) > 0] — the indicator: 1 if at least one code fired on *c*'s trace for task *t*,
  0 if the judge found nothing; so the sum counts the traces on which anything fired.

The share of judged traces on which anything fired. One per failing trace however much
went wrong on it, so a candidate that ruins a few tasks is separated from one that lightly
marks many — which amplitude adds into the same total. A_inc(c) ≤ A_amp(c) always, with
equality only when no trace ever carries two codes.

## 5. Combinations — failures that arrive together cost more

A_comb(c) = (1/T) · Σ_{t∈𝒯} ( 2^{k(c,t)} − 1 )          lower is better

where
- *c*, *𝒯*, *t*, *T*, k(c,t) — as above;
- 2^{k(c,t)} − 1 — the number of non-empty subsets of the codes that fired on that trace:
  0 codes → 0, one → 1, two → 3, three → 7, four → 15.

A trace showing *k* codes contributes the number of its non-empty code subsets, 2^k − 1:
one code → 1, two → 3, three → 7. Three codes on one trace therefore cost 7 where the same
three codes spread over three traces cost 3. This is the crudest reading of "co-occurring
failures are worse than the same failures apart" that is not already amplitude: it is
exponential in the per-trace count and has no strength parameter. Counting each code
separately instead would give amplitude exactly, since Σ_t k(c,t) is linear in the counts.

## 6. Step-amplitude — how many (step, code) firings

A_step(c) = (1/T) · Σ_{t∈𝒯} Σ_{s∈S(t)} |codes(c,t,s)|         lower is better

where
- *c*, *𝒯*, *t*, *T* — as above;
- S(t) — the steps of the trace on task *t*: the program's turns in order (hover: the four
  module calls summarize1, create_query_hop2, summarize2, create_query_hop3); *s* ranges over it;
- codes(c,t,s) — the distinct codes the judge placed *at step s* of *c*'s trace on *t*; the
  union over *s* is codes(c,t), and |codes(c,t,s)| is how many fired at that step.

Amplitude counted per step instead of per trace: a code that fired at two different steps
of one trace counts twice here and once in A_amp. A_step(c) ≥ A_amp(c) always, with equality
when no code ever fires at more than one step of a trace — which is forced on a one-step
program, where A_step = A_amp exactly. On hover's four-module pipeline the two differ by
however often the same code recurs across modules.

## 7. Containment-discounted amplitude — did anything follow it

A firing at step *s* of the trace on *t* is **contained** when down(s) is non-empty and no
code fired at any step in down(s) on that trace: something ran after the failure and ran
clean. A firing at the terminal step is never contained, because nothing ran afterwards and
observing no downstream failure says nothing.

A_con(c) = (1/T) · Σ_{t∈𝒯} |{ (s,m) : m ∈ codes(c,t,s), (s,t) not contained }|     lower is better

where
- *c*, *𝒯*, *t*, *T*, S(t), *s*, codes(c,t,s) — as above;
- (s,m) — one firing: code *m* at step *s* of the trace on *t*; the set collects every firing
  in the trace, and |·| counts them;
- down(s) — the steps that consume step *s*'s output, directly or through the harness; on a
  linear pipeline, every step after *s*; empty for the terminal step;
- "(s,t) not contained" — the firing is kept unless down(s) is non-empty *and* no code fired
  at any step in down(s) on that trace, i.e. unless something ran after step *s* and ran clean.

Every step-amplitude firing contributes 1 unless it was contained, when it contributes 0.
It is the gold-free counterpart of asking whether a failure cost the outcome: instead of
reading the outcome, it reads whether the program's own later steps carried the trouble
forward. Parameter-free by construction — any graded discount by how many downstream steps
stayed clean would introduce a strength parameter. A_con(c) ≤ A_step(c) always. On a
one-step program every firing is terminal, so A_con = A_step = A_amp.

The tension to note: dropping contained firings discards evidence, against the rule that a
formula should weigh everything. It is a conditional drop decided by the trace, not a
selection of steps decided in advance, but it is the only entry here that has it.

## 8. From scores to rankings, and the measure

**Ranking.** Candidates are sorted by the score: descending for gold, ascending for the
trace methods (fewer, rarer, less-clustered failures rank higher). Two candidates with
equal scores are tied.

**Kendall tau-b, tied pairs dropped.** For two rankings *R₁*, *R₂* of the same *n*
candidates, consider every unordered candidate pair {a, b} (n(n−1)/2 pairs: 36 for nine
candidates, 66 for twelve). A pair is *concordant* if both rankings order a and b the same
way, *discordant* if they order them oppositely, and *dropped* if either ranking ties them.
With C concordant and D discordant pairs,

τ = (C − D) / (C + D)

where
- *R₁*, *R₂* — the two rankings being compared (a method's ranking of the candidates, and
  the gold-gen ranking); *n* — the number of candidates (9 or 12);
- {a, b} — one unordered pair of candidates; there are n(n−1)/2 of them;
- *C* — the number of pairs both rankings order the same way (concordant);
- *D* — the number of pairs they order oppositely (discordant);
- pairs tied in either ranking are in neither count, so C + D is the number of pairs the
  comparison is actually made on, and it is reported when it is less than n(n−1)/2.

so τ = +1 is perfect agreement on every ordered pair, −1 perfect reversal, 0 no relation.
Dropping tied pairs rather than counting them as half-right is what makes a tied gold-50
visible: it is compared on fewer pairs, and the pair count is stated where it matters.

**The comparison.** For every method, τ is computed between the method's ranking (from the
judged traces) and the ranking by pass rate on the generalization tasks — disjoint from the
judged tasks and never judged. The *gold* row of every table is the same comparison for the
judged tasks' own pass rate, so it is the bar: how well scoring the judged tasks themselves
predicts the large set. A trace method above the gold row is extracting more about the
candidate from *T* traces than *T* outcomes carry.

**Top-1.** Whether the method's first-ranked candidate is the first-ranked candidate under
gold-gen.

## 9. Worked example

Nine candidates, 50 judged tasks. Candidate *c* has points on 21 of its 50 traces: 15 traces
with one code, 5 with two, 1 with three. Then

- k sums to 15·1 + 5·2 + 1·3 = 28, so A_amp = 28/50 = 0.56;
- 21 traces carry anything, so A_inc = 21/50 = 0.42;
- subsets sum to 15·1 + 5·3 + 1·7 = 37, so A_comb = 37/50 = 0.74;
- if, on a four-step program, 4 of the 28 code firings recur at a second step, there are 32
  (step, code) firings, so A_step = 32/50 = 0.64; if 3 of those 32 sit at a non-terminal step
  with every later step clean, they are contained and A_con = 29/50 = 0.58.

Rank all nine by each score (ascending), rank them by gold-gen (descending), and count
concordant / discordant pairs over the 36 candidate pairs, dropping any pair tied in either
ranking. If amplitude orders 34 of 35 untied pairs the way gold-gen does,
τ = (34 − 1)/35 = +0.943.

## 10. What was run but is not reported here

`code/BASELINES.md` lists eleven parameter-free entries; `code/methods_scripts/run_baselines.py`
computes all of them. Breadth, worst-mode and distinct-patterns are dominated by or redundant
with the ones above; recovery reads gold and is therefore not a trace-only method. Their rows
remain in the raw tables in each `results/` directory.
