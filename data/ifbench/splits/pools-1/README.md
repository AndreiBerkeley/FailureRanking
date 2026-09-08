# pools-1 — the master partition of IFBench tasks

Three pools. Every later study draws its tasks from inside the pool made for
its purpose, uses as many or as few as it needs, and never crosses pools.

| pool | tasks | kept from existing splits | newly drawn |
|---|---:|---:|---:|
| `taxonomy` | 300 | 200 | 100 |
| `judging` | 500 | 100 | 400 |
| `generalization` | 12,303 | 194 | 12,109 |

**How it was built.** Tasks already captured keep their roles: the optimizer's 200 tasks (`gepa-1`) are in `taxonomy`, the 100 `eval-1` sample tasks in `judging`, the 194 `eval-1` domain tasks in `generalization`; the rest was filled from the train file. Newly
drawn tasks come from a seeded draw (seed 2026) stratified by number of constraints in the prompt, so
each pool's fill has the same mix as the reservoir it came from.

Fills were drawn only from tasks with one or two constraints, the range the test set covers; the train file's three-to-five-constraint prompts are left out so the pools stay comparable to the tasks the candidates were tuned on.

| pool | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| taxonomy | 193 | 86 | 18 | 3 |
| judging | 358 | 142 | 0 | 0 |
| generalization | 8,395 | 3,908 | 0 | 0 |

**Rules.** Pool sizes are ceilings, not prescriptions. Tasks the optimizer saw
are only ever in `taxonomy`; `judging` and `generalization` contain none.
`generalization` is only ever a target: nothing about it may be used to build
an instrument or a formula. The older splits `gepa-1` and `eval-1` remain as
the record of what was run; `pools-1` contains them.
