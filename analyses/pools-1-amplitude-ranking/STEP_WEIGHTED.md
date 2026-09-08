# Weighting a firing by the step it happened at (HoVer)

2026-09-08. `scripts/step_weighted.py`. Outcome-free scoring; gold read only to validate against
the 500-task generalization pool.

## The structural argument, stated before computing

`forward()` returns `retrieved_docs = hop1_docs + hop2_docs + hop3_docs`, and the metric is 1.0 only
if every gold supporting title is somewhere in that union. Neither summary enters the output. Hop 1
is retrieved from the raw claim, so it is not a candidate act. **Only `create_query_hop2` and
`create_query_hop3` produce anything that reaches the output**; the summarizers reach it only through
those queries. So a firing at a query step is a failure in the act that determines the answer, and a
firing at a summarizer is a failure in an intermediate that may or may not propagate.

## Result

Kendall tau-b against gold on the generalization pool; 95% CI is a bootstrap over the judged traces.

| weighting | map-5 / tax-10 placed | map-5 / tax-10 any | map-3 / tax-18 placed | map-3 / tax-18 any |
|---|---:|---:|---:|---:|
| all four steps equal | +0.50 | +0.45 | +0.41 | +0.47 |
| **queries only** | **+0.71** | **+0.87** | **+0.58** | **+0.73** |
| queries 1.5×, summarizers 1× | +0.60 | +0.61 | +0.45 | +0.52 |
| summarizers only | +0.09 | −0.02 | −0.32 | −0.23 |
| hop3 only (the terminal act) | +0.48 | +0.41 | +0.23 | +0.34 |

Query-multiplier sweep, summarizers held at 1×, all four configurations **monotone increasing**:

| multiplier | 0× | 0.5× | 1× | 1.5× | 2× | 3× | 5× |
|---|---:|---:|---:|---:|---:|---:|---:|
| map-5 placed | +0.09 | +0.33 | +0.50 | +0.60 | +0.69 | +0.72 | +0.75 |
| map-5 any | −0.02 | +0.33 | +0.45 | +0.61 | +0.64 | +0.70 | +0.76 |

So 1.5× is not a special value: the score improves the more the summarizers are discounted, and
the limit is dropping them entirely. Summarizer firings carry nothing on tax-10 and are actively
misleading on tax-18.

## Reference points on the same target

| | tau-b |
|---|---:|
| **queries-only amplitude, tax-10, any reader** | **+0.87** |
| gold on the whole 500-task judging pool | +0.76 |
| gold on the same 50 judged tasks | +0.78 |
| gold on 100 judged tasks | +0.72 |
| instruction word count | +0.64 |
| equal-weight placed amplitude | +0.50 |
| base amplitude (no steps) | +0.06 |

The queries-only score predicts the generalization ranking at least as well as gold on the same 50
tasks does, from trace evidence alone.

## What is not yet established

Twelve candidates give tau a standard error near 0.25, so +0.87 and +0.78 are not distinguishable.
Many weightings have been tried today, and although the query/summarizer split was argued from the
program's data flow before this computation, per-step correlations had already been looked at
earlier in the session, so this is not a clean pre-registration.

The honest test is `map-6`: tax-10 judged on the second, disjoint 50-task block, currently running.
The weighting is now fixed and the block is untouched. Gold on that block predicts the target at
+0.35, so the comparison to make there is the queries-only score against +0.35, not against +0.78.
