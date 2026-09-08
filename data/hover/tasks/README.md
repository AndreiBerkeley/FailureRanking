# tasks — the HoVer task registry

One row per task. Gold-bearing: this is the only place gold lives.

| field | meaning |
|---|---|
| `task_id` | the source dataset's uid; the identity every other file uses |
| `claim` | the claim to verify |
| `label` | the dataset's supported / not-supported label (1 / 0) |
| `gold.supporting_titles` | the three distinct Wikipedia titles a run must retrieve to score 1 (the source gold files repeated a title when two supporting sentences came from it; deduplicated here on 2026-09-06) |
| `source` | dataset, split, row index, and the claim's sha256 |
| `splits` | which split portions the task belongs to, as `split/portion` |

Currently 6084 tasks. The registry holds every task any stored capture
references; it grows as captures are added and never shrinks. A task's row
never changes once written; only its `splits` list can gain entries.

| split / portion | tasks |
|---|---:|
| `eval-1/domain` | 500 |
| `eval-1/sample` | 50 |
| `gepa-1/train` | 400 |
| `gepa-1/validation` | 150 |
| `pools-1/generalization` | 4984 |
| `pools-1/judging` | 500 |
| `pools-1/taxonomy` | 600 |
