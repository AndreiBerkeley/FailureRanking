# 2026-09-profile-stability — does the sample's failure profile hold on the domain?

**Checkpoint served.** Checkpoint 1, proof of existence: is there evidence of a
relationship between a candidate's failure-mode distribution on a sample of
tasks and its distribution across the domain.

**Status.** In progress. Not yet entered in the methodology record.

**Question.** For each of twelve candidates, the judge read every trace on the
50-task sample and about a third of the traces on the 500-task domain, under
two taxonomies. Is the distribution of failure codes on the sample the same
object as the distribution on the domain, once the movement that task sampling
alone would cause is accounted for?

**Reasoning.** "Stays the same" is not a claim until it is measured against a
floor. A code firing 0.1 times per trace produces about five hits across a
candidate's 50 traces, and that count moves between task samples for reasons
that have nothing to do with the candidate. So every comparison here is read
against a noise floor built from the domain itself: each candidate's domain
tasks are split a thousand times into 50 versus the rest, and the spread of the
resulting profiles is the band a real difference has to clear. Two taxonomies
are compared on the same traces so that granularity is a variable, not a fixed
choice. Only judge outputs are read; no gold enters this analysis.

**What was done.** Four mappings from `data/hover/mappings/`: for `tax-7`,
`map-1` (sample, 600 traces, complete) against `map-2` (domain, 2,136 traces
judged of 6,000, spread evenly over candidates); for `tax-18`, `map-3` against
`map-4` (2,187 of 6,000). For each taxonomy, five measurements: whether each
code can reproduce itself across random halves of the sample at all; whether
each code's firing rate agrees between sample and domain and orders the
candidates the same way; whether each candidate's whole profile, as shares,
sits inside the sampling floor; whether a candidate's sample profile is nearer
its own domain profile than any other candidate's; and whether that identity
rests on one frequent code or on the shape. Full tables: `results/tax-7/`,
`results/tax-18/`.

**Result.**

| | tax-7 (7 codes) | tax-18 (18 codes) |
|---|---:|---:|
| candidates whose whole profile sits inside the sampling floor | 11 of 12 | 12 of 12 |
| codes whose sample-to-domain gap exceeds the floor | 0 of 7 | 0 of 18 |
| sample profile is nearest its own domain profile | 9 of 12 (75%) | 12 of 12 (100%) |
| the same test with a 50-task subsample of the domain (ceiling) | 96.5% | 99.4% |
| chance | 8.3% | 8.3% |
| own domain profile ranked first or second, out of 12 | 12 of 12 | 12 of 12 |
| median rank correlation across candidates, per code | +0.648 | +0.742 |
| identity carried by the most frequent code alone | 8.3% | 16.7% |
| identity with the most frequent code removed (shares) | 58.3% | 83.3% |

The three frequent codes of `tax-7` (over 0.25 firings per trace) order the
candidates almost identically on sample and domain: rank correlations +0.865,
+0.918 and +0.944, and each reproduces itself across halves of the sample at
about +0.85. The four rare codes do not: two of them cannot reproduce
themselves even within the sample (+0.225 and −0.368), so they have no
stability to lose, and their weak transfer (+0.28 to +0.65) is a sampling fact,
not a transfer fact. Under `tax-18`, 14 of 18 codes exceed +0.6 across
candidates; the two that do not fire fewer than 0.05 times per trace.

**What it settles.** On this benchmark, with these instruments and this one
sample, the failure profile read on 50 tasks is the same object as the profile
on the domain. Whole-profile shape agrees within sampling noise for all but one
candidate; every candidate's sample profile is closest or second-closest to its
own domain profile; frequent codes transfer their rates and their ordering of
candidates; and the identity is distributed across the vocabulary rather than
carried by one code. The finer taxonomy transfers better, not worse. This is the
existence evidence checkpoint 1 asks for.

**What it does not settle.** The domain mapping is a third of the domain, so
the domain profiles carry their own sampling error; the floor accounts for
this only partly. One benchmark, one sample draw: the variance of these numbers
across different 50-task samples is unmeasured, and one draw of 50 can land
anywhere in that variance. The same judge configuration read sample and domain,
so a judge bias shared by both cancels here and is not detected. Both sides are
single runs, so run-to-run noise is folded into the floor rather than
separated from task noise. Rare codes, below roughly 0.15 firings per trace, do
not reproduce themselves within 50 traces; whatever they carry needs more traces
or a coarser grouping. And the gap between the identity rate and its ceiling
under `tax-7`, 75 percent against 96.5, is real transfer loss that the
whole-profile test does not resolve.

**Where the evidence lives.** This directory. `provenance.json` names the four
mappings and two taxonomies by path and hash, the script by hash, and the seed.
`scripts/stability.py` reproduces `results/` from `data/` alone. An earlier
run of the same statistics against the raw judge outputs is in
`results/hover/profile-stability`; the deterministic quantities here (identity,
per-code rank correlation, per-profile distance) reproduce it exactly.
