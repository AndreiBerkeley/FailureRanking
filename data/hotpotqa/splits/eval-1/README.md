# eval-1 — the evaluation split

Two portions of tasks the optimizer never saw, disjoint from each other and
from `gepa-1`; together they are the artifact's entire test set.

| portion | tasks | role |
|---|---:|---|
| `sample` | 100 | the set a candidate is read closely on |
| `domain` | 200 | the held-out set the sample is supposed to speak for |

Copied without reordering from `benchmarks/hotpotqa/splits/split-1`, where the
portions were called `measurement` and `generalization`. Nothing about `domain`
may be used to build an instrument or a formula; it is only ever the target.
