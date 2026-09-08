# Base failure amplitude on the judged samples, against gold

Computed 2026-09-07. Amplitude A(c) = mean number of distinct codes the panel assigned per judged
trace (lower is better), from the judged sample of each judging pool (12 candidates × 50 tasks ×
repeat 0): hover `map-3` (tax-18) and `map-1` (tax-7), ifbench `map-1` (tax-1), hotpotqa `map-1`
(tax-1). Compared by Kendall tau-b with gold candidate means on the judged tasks, the whole judging
pool, and the generalization pool. Gold is the target only.

| file | what it is |
|---|---|
| `scripts/amplitude_rank.py` | the computation; writes `results.json` |
| `results.json` | amplitudes and every tau, p and rho |

Headline: amplitude carries no ranking signal on hover (tau +0.02 against the generalization gold,
where gold itself agrees across pools at +0.76), and points the wrong way on hotpotqa (−0.42): the
two bare-instruction candidates have the lowest amplitude because they have almost no clauses to
breach. Per code, hover's vocabulary splits into codes that fire more on worse candidates
(conversational queries, parametric knowledge injection, tau +0.6) and codes that fire more on
better ones (hallucinated document accounting, retrieval-state mistracking, claim-constraint
omission, tau −0.5 to −0.7), because only candidates whose instructions demand evidence-tracking
sections can fail them. A plain sum cancels the two. Hotpotqa's format code is additionally
contaminated by the harness's field markers (see `data/hotpotqa/taxonomies/tax-2`).
