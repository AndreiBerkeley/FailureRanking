# tasks — the IFBench task registry

One row per task. Gold-bearing: this is the only place gold lives.

| field | meaning |
|---|---|
| `task_id` | `ifbench:<key>:<hash>`, the id the artifact's runner assigned; recomputed from the source record and verified |
| `inputs` | what the program is given |
| `gold` | `gold.instruction_id_list` and `gold.kwargs`: the constraints the official checker verifies |
| `source` | where the record comes from |
| `splits` | which split portions the task belongs to, as `split/portion` |

13,103 tasks. The registry holds every task any split or capture
references and grows as they are added; a row never changes once written, only
its `splits` list can gain entries.

| split / portion | tasks |
|---|---:|
| `eval-1/domain` | 194 |
| `eval-1/sample` | 100 |
| `gepa-1/train` | 100 |
| `gepa-1/validation` | 100 |
| `pools-1/generalization` | 12,303 |
| `pools-1/judging` | 500 |
| `pools-1/taxonomy` | 300 |
