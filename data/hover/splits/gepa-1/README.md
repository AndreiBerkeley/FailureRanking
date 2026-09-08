# gepa-1 — the split the optimizer ran on

Train 400 and validation 150 task ids, frozen before the
optimizer run `gepa-1` and consumed by it. Copied without reordering from
`benchmarks/hover/splits/split-2` (its `train` and `validation` portions).

Every candidate in the registry was proposed and accepted or rejected on these
tasks. They are therefore forbidden for any scoring that claims to be free of
optimizer influence; they remain the right place to induce a taxonomy and to
study the candidates' own behaviour.
