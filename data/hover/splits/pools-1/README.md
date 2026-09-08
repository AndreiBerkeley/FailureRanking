# pools-1 — the master partition of HoVer tasks

Three pools. Every later study draws its tasks from inside the pool made for
its purpose, uses as many or as few as it needs, and never crosses pools.

| pool | tasks | kept from existing splits | newly drawn |
|---|---:|---:|---:|
| `taxonomy` | 600 | 550 | 50 |
| `judging` | 500 | 50 | 450 |
| `generalization` | 4,984 | 500 | 4,484 |

**How it was built.** Tasks already captured keep their roles: the optimizer's 550 tasks (`gepa-1`) are in `taxonomy`, the 50 `eval-1` sample tasks in `judging`, the 500 `eval-1` domain tasks in `generalization`; the 350 never-run spare tasks of the old split-3 and the 4,634 never-drawn claims filled the rest. Newly
drawn tasks come from a seeded draw (seed 2026) stratified by label (1 = supported, 0 = not supported), so
each pool's fill has the same mix as the reservoir it came from.

| pool | 0 | 1 |
|---|---|---|
| taxonomy | 277 | 323 |
| judging | 230 | 270 |
| generalization | 2,306 | 2,678 |

**Rules.** Pool sizes are ceilings, not prescriptions. Tasks the optimizer saw
are only ever in `taxonomy`; `judging` and `generalization` contain none.
`generalization` is only ever a target: nothing about it may be used to build
an instrument or a formula. The older splits `gepa-1` and `eval-1` remain as
the record of what was run; `pools-1` contains them.
