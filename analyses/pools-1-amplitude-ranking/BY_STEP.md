# Firings by step (HoVer, tax-10, map-5)

2026-09-08. The judge records carry `votes_by_turn`: per code, how many of the two readers placed
it on each agent turn. So every firing can be split by the step it occurred in, with one caveat
measured first.

## Caveat: readers agree on presence, not on place

| code | both readers, anywhere in the trace | both readers, same turn | any reader, any turn |
|---|---:|---:|---:|
| Unsupported Assertion | 245 | 180 | 251 |
| Missing Closing Marker | 194 | 195 | 250 |
| Work State Misjudged | 219 | 69 | 158 |
| Output Form Breach | 183 | **3** | 30 |
| Misdirected Next Step | 182 | 68 | 173 |
| Missing Required Part | 156 | 55 | 83 |

Output Form Breach is agreed present in 183 traces and agreed on a turn in 3: the readers see it
and disagree about where, or do not place it at all. A by-step analysis therefore covers the
well-placed codes and under-represents the rest. Location agreement is a measurement-confidence
quantity in its own right (component 6) that the gate's kappa, which is per trace, does not see.

## Step-level amplitude against the generalization gold

| step | both readers, same turn | any reader | vs instruction length |
|---|---:|---:|---:|
| summarize1 | **+0.56** (p=.012) | +0.26 | +0.56 |
| create_query_hop2 | +0.28 | +0.44 (p=.053) | +0.09 |
| summarize2 | **−0.58** (p=.009) | **−0.54** (p=.018) | **−0.68** |
| create_query_hop3 | **+0.48** (p=.037) | +0.41 (p=.073) | +0.57 |

Three steps individually reach significance and one is significantly inverted; summing the four
gives the +0.06 of the whole. The inversion at summarize2 is robust to the counting rule. Its
strongest cells are Missing Closing Marker (90 firings, −0.46), Unsupported Assertion (52, −0.32)
and Work State Misjudged (23, −0.44), all firing more on the better candidates. The same closing
marker code at summarize1 (105 firings) runs +0.51: one code, opposite sign by step.

## But every step tracks instruction length as tightly as it tracks gold

The right-hand column is the problem. summarize1 +0.56 on both, summarize2 −0.58 and −0.68,
hop3 +0.48 and +0.57. On HoVer gold and instruction length are correlated at +0.81 on the judged
tasks, so with twelve candidates no step-level or code-level number can be separated from length.
Splitting by step exposes structure that the sum hides, and it still cannot say whether that
structure is about quality or about how much the instructions say.

The way out is a candidate set where instruction length is constant: the same prompt run by
different models, which is the set agreed on 2026-09-07 and being captured under
`data/hover/traces/_incoming/models-1-taxonomy`. There, exposure is identical across candidates
by construction, and any step or code signal that survives is execution, not construction.
