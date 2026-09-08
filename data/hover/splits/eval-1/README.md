# eval-1 — the evaluation split

Two portions of tasks the optimizer never saw, disjoint from each other and
from `gepa-1`:

| portion | tasks | role |
|---|---:|---|
| `sample` | 50 | the small set a candidate is read closely on: every trace judged |
| `domain` | 500 | the large held-out set the sample is supposed to speak for |

The question the project asks is whether what is read on `sample` holds on
`domain`. Nothing about `domain` may be used to build an instrument or a
formula; it is only ever the target.

Copied without reordering from `benchmarks/hover/splits/split-3`, where the
portions were called `judging` and `generalization`. Same seed and protocol as
that split. A further 350 tasks from the same draw remain unused there.
