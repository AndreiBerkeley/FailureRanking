# How ranking quality is measured

Every number in this package answers one question: **when a scoring method
orders the twelve candidates, how close is that order to the truth?**

## The metric

Kendall's tau-b. Take every pair of candidates, 66 pairs for twelve
candidates. For each pair, ask whether the scoring method and the truth agree
on which of the two is better. Then

```
tau = (agreements - disagreements) / (number of comparable pairs)
```

- **+1.0** every pair ordered correctly
- **0.0** no better than a coin flip
- **-1.0** every pair ordered backwards

Ties matter here, because several candidates have identical or near-identical
true scores. The "-b" variant excludes tied pairs from the denominator, so a
tie neither helps nor hurts. Concretely, the best configuration against the
held-out target scores **53 pairs concordant, 7 discordant, and 6 tied**, giving
tau = (53 - 7) / 60 ≈ +0.73.

Every reported figure ships with its concordant, discordant and tied counts in
`experiments/results.json`, so any tau in this package can be read back as
actual pair counts rather than taken on faith.

Tau is used rather than a correlation of scores because only the *order*
matters. A method that assigns strange-looking numbers in a consistent order is
a good ranker; the numbers themselves are on an arbitrary scale.

Two other figures appear in the results:

- **Top-1 hit** — did the method's best candidate match the true best? Reported
  tie-aware: it counts as a hit if the tied-best groups share a candidate. This
  is reported separately because picking the single winner is a different task
  from ordering the field, and a method can be good at one and poor at the
  other.
- **average tau** — the mean of the two targets below, used only to rank
  configurations that must do well at both.

## The two truths

There is no single ground-truth ranking, because "better" can mean two
different things. Both are computed from the evaluator's scores, and neither is
visible to any scoring path.

**Cross-seed target.** Each candidate's mean score over **repeats 1 to 4** of
the 50 evidence tasks. This asks: *if we re-ran these same tasks, would the
ranking hold?* It tests stability against execution randomness. Scoring reads
only repeat 0, so the four other executions are unseen.

**Held-out target.** Each candidate's mean score over the **250 tasks** never
used for anything else, at repeat 0. This asks: *does the ranking transfer to
different tasks?* It tests generalisation beyond the evaluated sample.

The two targets are themselves only moderately related to each other
(tau = +0.67). That is not an error; stability and transfer are genuinely
different properties. It also sets a ceiling on how well any single ranking can
do against both at once.

## What the evidence budget is

Every method scored here reads the same thing: the judge's findings on **repeat
0 of the 50 evidence tasks**. The outcome-only baseline reads the evaluator's
scores on exactly those same 50 tasks. Neither sees more data than the other,
so the comparison is at an equal budget and no method has an information
advantage.

Configurations using a gold feedback module additionally read the *outcomes* of
those same 50 tasks. Those are labelled `scenario_1: true` throughout and are
never compared as if they were gold-free.

## Reading the headline numbers

The comparison in the README:

| ranking from the same 50 tasks | cross-seed | held-out |
| --- | :-: | :-: |
| the evaluator's own success rate | +0.53 | +0.41 |
| failure evidence, simplest useful method | +0.85 | +0.73 |

In pair terms, out of 66 candidate pairs:

| | cross-seed | held-out |
| --- | --- | --- |
| outcome success rate | 44 right, 12 wrong, 10 tied | 40 right, 15 wrong, 11 tied |
| failure evidence | 58 right, 4 wrong, 4 tied | 53 right, 7 wrong, 6 tied |

The failure-based method gets 14 more pairs right on the cross-seed target and
13 more on the held-out target, while also leaving fewer pairs unresolved.

The reason outcome counting does comparatively poorly is not that outcomes are
wrong, but that 50 binary results is a coarse instrument. The candidates' true
success rates lie within 0.16 of each other, and 50 coin-flip-like observations
per candidate cannot resolve differences that fine. The failure evidence
aggregates roughly 2,000 findings over the same 50 tasks, which is simply more
signal about the same executions.

## What these numbers do not support

**Twelve candidates is a small field.** With 66 pairs, a single pair flipping
changes tau by about 0.03. Differences smaller than roughly 0.1 between two
scoring configurations should not be read as one being better.

**Both targets carry their own noise.** Each is a mean of binary outcomes: the
held-out target averages 250 of them per candidate, the cross-seed target 200.
The standard error of each candidate's target value is about 0.03, while the
average spacing between adjacent candidates is about 0.015. Many pairs are
therefore statistical ties *in the truth itself*.

Concretely: for the best configuration, **every remaining ordering
disagreement is between candidates whose true scores differ by less than the
noise in the truth**. There is no identified pair that the method reliably gets
wrong. The remaining gap to +1.0 is not headroom for a better formula; it is
the resolution limit of this testbed.

**Selection inflation.** The results file contains 1,890 configurations. The
best of that many, evaluated on the same targets used to choose it, is
optimistically biased. The claims worth taking seriously are the ones that hold
across families of configurations rather than any single cell, and the
outcome-versus-failure-evidence gap, which is far larger than the noise.

**Single benchmark, single judge.** Everything here is one retrieval task
family, one taxonomy, and one judge. The pipeline is built to be portable and
takes any judge output in the documented format, but portability is a design
property, not yet a measured result.

## Reproducing

```bash
cd experiments
python run_all.py
```

Recomputes the baselines, the full configuration grid, and every reported
figure from the shipped files. The script also asserts that two of the five
reference baselines exactly match their equivalent module configurations, so a
silent drift between the two implementations would fail the run rather than
produce quiet mismatches.
