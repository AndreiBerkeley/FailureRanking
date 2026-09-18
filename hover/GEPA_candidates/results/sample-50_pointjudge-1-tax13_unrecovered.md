hover-pool3  run=runs/new_pipeline/hover/pointjudge-1-unrecovered  taxonomy=data/hover/taxonomies/tax-13/taxonomy.json  judged tasks=50  gen tasks=500

| method | tau vs gold-gen | top-1 | tau vs gold-50 | top-1 (gold-50) |
|---|---:|---|---:|---|
| 1 gold | +0.785 | no | +1.000 | yes |
| 2 amplitude | +0.387 | no | +0.311 | no |
| 3 incidence | +0.738 | yes | +0.600 | no |
| 4 breadth | -0.040 | no | -0.160 | no |
| 5 worst mode | -0.129 | no | -0.290 | no |
| 6 combinations | +0.169 | no | +0.188 | no |
| 7 patterns | +0.377 | no | +0.400 | no |
| 8 step-amp | +0.258 | no | +0.311 | no |
| 9 recovery | +0.460 | no | +0.387 | no |
| 10 containment | +0.569 | no | +0.562 | no |
| 13 last-turn incidence | +0.833 | no | +0.864 | yes |

low-support code/candidate cells in method 9 (app_m < 5): 74
steps for methods 8 and 10: panel votes_by_turn and open-reader agents, from judge_records
