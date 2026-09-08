# pools-1 — the master partition of HotpotQA tasks

Three pools. Every later study draws its tasks from inside the pool made for
its purpose, uses as many or as few as it needs, and never crosses pools.

| pool | tasks | kept from existing splits | newly drawn |
|---|---:|---:|---:|
| `taxonomy` | 200 | 200 | 0 |
| `judging` | 150 | 100 | 50 |
| `generalization` | 400 | 200 | 200 |

**How it was built.** Tasks already captured keep their roles: the optimizer's 200 tasks (`gepa-1`) are the whole `taxonomy` pool, the 100 `eval-1` sample tasks are in `judging`, the 200 `eval-1` domain tasks in `generalization`; the 250 snapshot records the optimizer never saw filled the rest, so nothing is left over. Newly
drawn tasks come from a seeded draw (seed 2026) stratified by question level and type, so
each pool's fill has the same mix as the reservoir it came from.

| pool | easy/bridge | easy/comparison | hard/bridge | hard/comparison | medium/bridge | medium/comparison |
|---|---|---|---|---|---|---|
| taxonomy | 30 | 9 | 28 | 10 | 101 | 22 |
| judging | 20 | 5 | 17 | 5 | 85 | 18 |
| generalization | 56 | 15 | 44 | 16 | 224 | 45 |

**Rules.** Pool sizes are ceilings, not prescriptions. Tasks the optimizer saw
are only ever in `taxonomy`; `judging` and `generalization` contain none.
`generalization` is only ever a target: nothing about it may be used to build
an instrument or a formula. The older splits `gepa-1` and `eval-1` remain as
the record of what was run; `pools-1` contains them.
