livecodebench  run=runs/new_pipeline/lcb-models/pointjudge-1  taxonomy=data/livecodebench/taxonomies/tax-1/taxonomy.json  judged tasks=50  gen tasks=755

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| 1 gold | +0.765 | yes |
| 2 amplitude | +0.657 | no |
| 3 incidence | +0.588 | no |
| 4 breadth | +0.857 | yes |
| 5 worst mode | +0.379 | no |
| 6 combinations | +0.867 | no |
| 7 patterns | +0.786 | yes |
| 8 step-amp | +0.657 | no |
| 9 recovery | +0.667 | no |
| 10 containment | +0.657 | no |

low-support code/candidate cells in method 9 (app_m < 5): 37
