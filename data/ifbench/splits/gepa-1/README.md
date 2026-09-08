# gepa-1 — the split the optimizer ran on

Train 100 and validation 100 task ids, drawn with seed 0 and a proportional
stratified protocol from the artifact's own train and validation pools, frozen
before the optimizer run `gepa-1` and consumed by it. Copied without reordering
from `benchmarks/ifbench/splits/split-1`.

Every candidate in the registry was proposed and scored on these tasks. They are
forbidden for any scoring that claims to be free of optimizer influence; the
taxonomy-induction corpus was drawn from the train portion on purpose.
