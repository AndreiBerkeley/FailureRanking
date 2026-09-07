# Results

Every figure here is produced by `run_all.py` from the files shipped in this
package. Read `../METHOD.md` first if you have not: it explains what tau means
and what these numbers can support.

Two targets throughout, neither visible to any scoring path:

- **cross-seed** — the ranking when the same 50 tasks are re-run on four fresh seeds
- **held-out** — the ranking on 250 tasks used for nothing else

## The comparison that motivates the work

| ranking built from the same 50 tasks | cross-seed | held-out |
| --- | :-: | :-: |
| the evaluator's own success rate | +0.525 | +0.413 |
| failure evidence, best configuration | **+0.851** | **+0.731** |

Same tasks, same evidence budget. Counting *how often each candidate succeeded*
is a substantially worse predictor of future behaviour than counting *what went
wrong along the way*.

## The five reference baselines

These are the starting points: methods that count failure modes with no
weighting, no filtering, and no learned parameters. All five are gold-free.

| baseline | cross-seed | held-out | what it counts |
| --- | :-: | :-: | --- |
| base amplitude | +0.752 | +0.661 | distinct failure modes per task, averaged |
| pair expansion | +0.762 | +0.608 | modes plus one unit per co-occurring pair |
| persistent pairs | +0.782 | +0.646 | modes plus pairs weighted by how often the candidate repeats them |
| full combinations | +0.782 | +0.646 | the same, extended to groups of size two through six |
| order normalized | +0.750 | +0.678 | groups again, but each group size capped at one unit per task |

**base amplitude** is the simplest thing that could work: count how many
different kinds of failure the judge found on each task, average over tasks.
It already beats outcome counting by a wide margin on both targets, which is
the core finding of this work in its plainest form.

**pair expansion** adds a unit for every pair of failure modes appearing
together, on the theory that two problems at once is worse than two problems
apart. It buys a little on cross-seed and loses on transfer, because it charges
the same amount for a one-off coincidence as for a chronic pattern.

**persistent pairs** fixes exactly that by weighting each pair by how often
that candidate repeats it, so a signature costs much more than a coincidence.
It gives the best cross-seed result of the five.

**full combinations** extends the same idea from pairs to groups of every size.
It scores identically to persistent pairs, and that is the finding: no group
larger than a pair recurs often enough in this data to change any ordering, so
the extra machinery buys nothing.

**order normalized** caps each group size at one unit per task, preventing a
task with many failure modes from dominating through sheer combinatorics. It is
the best of the five at transferring to unseen tasks, which is the first hint
that limiting how much a single bad task can contribute matters more than
counting more structure.

## The best configurations

From 1,890 configurations of the module grid, reduced to 930 that produce
distinct rankings.

| purpose | configuration | cross-seed | held-out |
| --- | --- | :-: | :-: |
| best overall, and best gold-free | `unique / none / ol_gate_likely / - / uncapped_sum` | **+0.851** | +0.731 |
| best on transfer | `unique / pairs / ol_gate_likely / - / uncapped_sum` | +0.740 | **+0.778** |
| best at picking the single winner | `flagged / none / ol_ordinal / gold_fused / max` | +0.813 | +0.741 |

**`unique / none / ol_gate_likely / - / uncapped_sum`** is base amplitude with
one change: before counting, discard the failures the judge itself rated as
unlikely to have affected the answer. That single filter moves cross-seed from
+0.752 to +0.851 and transfer from +0.661 to +0.731. It uses no outcomes, no
tuned parameters, and no co-occurrence structure. It is both the best-performing
and the simplest-to-explain method in the package.

Why it works: automated judges over-report, and they over-report *unevenly*.
Better candidates fail in smaller ways, so a larger share of their flagged
failures never mattered. Counting everything compresses the field; counting only
consequential failures spreads it back out along real quality differences.

**`unique / pairs / ol_gate_likely / - / uncapped_sum`** adds co-occurrence
pairs on top of the same filter. Pairs describe *how* a candidate breaks down
rather than *how much*, and that signature transfers to new tasks better,
reaching +0.778 on the held-out target. It gives up cross-seed performance to
get there, which is why no single configuration wins both.

**`flagged / none / ol_ordinal / gold_fused / max`** is the only configuration
that identifies the true best candidate on both targets. It differs in every
module: it tracks whether a failure mode recurred within a task, uses the
judge's consequence ratings as graded weights rather than a hard filter, learns
from training outcomes how often each candidate survives each pattern, and
charges each task only for its worst known problem. It reads training outcomes,
so it is a scenario-1 method, and the results file marks it as such.

Note the interaction: the hard gate and the gold module do not combine well,
because deleting evidence starves the survival estimates the gold module needs.
The graded weight keeps the evidence alive at reduced volume, which is why the
top-choice configuration uses `ol_ordinal` rather than `ol_gate_likely`.

## What each module contributes

For every module, the best configuration that uses it. This shows what each
choice is worth at its best, not on average.

| stage | module | cross-seed | held-out | in configuration |
| --- | --- | :-: | :-: | --- |
| counting | `unique` | +0.851 | +0.731 | `unique/none/ol_gate_likely/-/uncapped_sum` |
| | `flagged` | +0.813 | +0.741 | `flagged/none/ol_ordinal/gold_fused/max` |
| | `total` | +0.782 | +0.678 | `total/groups_only/ol_gate_likely/gold_linear/capped_sum` |
| relationships | `none` | +0.851 | +0.731 | `unique/none/ol_gate_likely/-/uncapped_sum` |
| | `pairs` | +0.740 | +0.778 | `unique/pairs/ol_gate_likely/-/uncapped_sum` |
| | `ordered_pairs` | +0.782 | +0.709 | `flagged/ordered_pairs/ol_ordinal/gold_linear/max` |
| | `groups` | +0.813 | +0.678 | `unique/groups/-/gold_fused/noisy_or` |
| | `groups_only` | +0.844 | +0.646 | `unique/groups_only/ol_ordinal/gold_convex/capped_sum` |
| | `signatures` | +0.492 | +0.496 | `total/signatures/ol_gate_likely/-/max` |
| trust | `ol_gate_likely` | +0.851 | +0.731 | `unique/none/ol_gate_likely/-/uncapped_sum` |
| | `ol_ordinal` | +0.813 | +0.741 | `flagged/none/ol_ordinal/gold_fused/max` |
| | *(skipped)* | +0.813 | +0.678 | `unique/groups/-/gold_fused/noisy_or` |
| feedback | *(skipped)* | +0.851 | +0.731 | `unique/none/ol_gate_likely/-/uncapped_sum` |
| | `gold_fused` | +0.813 | +0.741 | `flagged/none/ol_ordinal/gold_fused/max` |
| | `recovery_convex` | +0.844 | +0.709 | `flagged/none/ol_gate_likely/recovery_convex/uncapped_sum` |
| | `gold_linear` | +0.782 | +0.741 | `flagged/none/ol_ordinal/gold_linear/max` |
| | `gold_convex` | +0.844 | +0.646 | `unique/groups_only/ol_ordinal/gold_convex/capped_sum` |
| | `gold_shrunk` | +0.750 | +0.678 | `flagged/groups/-/gold_shrunk/max` |
| formula | `uncapped_sum` | +0.851 | +0.731 | `unique/none/ol_gate_likely/-/uncapped_sum` |
| | `max` | +0.813 | +0.741 | `flagged/none/ol_ordinal/gold_fused/max` |
| | `noisy_or` | +0.813 | +0.678 | `unique/groups/-/gold_fused/noisy_or` |
| | `capped_sum` | +0.844 | +0.646 | `unique/groups_only/ol_ordinal/gold_convex/capped_sum` |
| | `pie_signed` | +0.657 | +0.552 | `unique/groups/ol_ordinal/gold_linear/pie_signed` |

Reading this table:

- **Trust is the most valuable stage.** Its best configurations beat the best
  configuration that skips it on both targets. It is also the cheapest: it uses
  information the judge already produced.
- **`unique` counting dominates.** Carrying repetition (`total`) consistently
  does worse, which suggests within-task repetition here reflects the judge's
  behaviour more than the candidate's.
- **Relationship structure trades cross-seed for transfer.** `none` wins the
  former, `pairs` the latter, and `signatures` fails outright because a task's
  exact failure profile is nearly unique and so almost never recurs.
- **Feedback is not free.** The best configuration overall uses no feedback at
  all. Feedback earns its place for a specific job, picking the single winner,
  and gold-based modules cost you the gold-free property to get it.
- **Recovery information is close to neutral here.** Its best configurations
  match nearly identical ones without it. That is a statement about the recovery
  labels available in this data, not about recovery as an idea.
- **`pie_signed` is a documented negative result.** Inclusion-exclusion is the
  principled way to handle overlapping evidence, but it needs the complete
  combination series to behave; truncated at the sizes available here it inverts
  orderings. It is kept in the package rather than hidden.

## Cross-check

`run_all.py` asserts that two of the five baselines, implemented directly,
match their equivalent module configurations to floating-point precision:

| baseline | module configuration | max difference |
| --- | --- | :-: |
| base amplitude | `unique/none/-/-/uncapped_sum` | 2.2e-16 |
| pair expansion | `unique/pairs/-/-/uncapped_sum` | 4.4e-16 |

The other three baselines price co-occurrences by per-candidate recurrence,
which no module exposes, so they are implemented directly only. If the two
implementations ever diverge, the run fails rather than reporting quietly
inconsistent numbers.

## Caveats

Twelve candidates, 66 pairs. A single pair flipping moves tau by about 0.03,
so differences below roughly 0.1 between configurations here are not
meaningful. The comparison against outcome-only ranking is far larger than that
and is the claim worth carrying; the fine ordering of the top configurations is
not. `../METHOD.md` sets this out in full.
