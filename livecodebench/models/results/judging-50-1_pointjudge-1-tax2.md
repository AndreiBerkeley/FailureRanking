livecodebench  run=runs/new_pipeline/lcb-models/pointjudge-1-tax2  taxonomy=data/livecodebench/taxonomies/tax-2/taxonomy.json  judged tasks=50  gen tasks=755

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| 1 gold | +0.765 | yes |
| 2 amplitude | +0.941 | yes |
| 3 incidence | +0.824 | yes |
| 4 breadth | +0.812 | yes |
| 5 worst mode | +0.379 | no |
| 6 combinations | +1.000 | yes |
| 7 patterns | +0.829 | yes |
| 8 step-amp | +0.941 | yes |
| 9 recovery | +0.829 | yes |
| 10 containment | +0.941 | yes |

low-support code/candidate cells in method 9 (app_m < 5): 49
