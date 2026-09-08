# tasks — the HotpotQA task registry

One row per task. Gold-bearing: this is the only place gold lives.

| field | meaning |
|---|---|
| `task_id` | `hotpotqa:<key>:<hash>`, the id the artifact's runner assigned; recomputed from the source record and verified |
| `inputs` | what the program is given |
| `gold` | `gold.answer` and `gold.supporting_facts`: the official answer and the sentences that support it |
| `source` | where the record comes from |
| `splits` | which split portions the task belongs to, as `split/portion` |

750 tasks. The registry holds every task any split or capture
references and grows as they are added; a row never changes once written, only
its `splits` list can gain entries.

| split / portion | tasks |
|---|---:|
| `eval-1/domain` | 200 |
| `eval-1/sample` | 100 |
| `gepa-1/train` | 100 |
| `gepa-1/validation` | 100 |
| `pools-1/generalization` | 400 |
| `pools-1/judging` | 150 |
| `pools-1/taxonomy` | 200 |
