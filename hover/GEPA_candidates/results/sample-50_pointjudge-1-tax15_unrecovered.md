hover-pool3  run=runs/new_pipeline/hover/pointjudge-1-tax15-unrecovered  taxonomy=data/hover/taxonomies/tax-15-pool3/taxonomy.json  judged tasks=50  gen tasks=500

| method | tau vs gold-gen | top-1 | tau vs gold-50 | top-1 (gold-50) |
|---|---:|---|---:|---|
| 1 gold | +0.785 | no | +1.000 | yes |
| 2 amplitude | +0.143 | no | +0.258 | yes |
| 3 incidence | +0.828 | yes | +0.860 | no |
| 4 breadth | +0.000 | no | -0.094 | no |
| 5 worst mode | -0.129 | no | -0.290 | no |
| 6 combinations | -0.169 | no | +0.062 | yes |
| 7 patterns | +0.344 | no | +0.367 | yes |
| 8 step-amp | +0.188 | no | +0.238 | yes |
| 9 recovery | +0.200 | no | +0.281 | yes |
| 10 containment | +0.354 | no | +0.406 | yes |
| 13 last-turn incidence | +0.833 | no | +0.966 | yes |

low-support code/candidate cells in method 9 (app_m < 5): 82
steps for methods 8 and 10: panel votes_by_turn and open-reader agents, from judge_records
