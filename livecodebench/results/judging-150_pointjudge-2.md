livecodebench  run=runs/new_pipeline/lcb-models/pointjudge-2  taxonomy=data/livecodebench/taxonomies/tax-2/taxonomy.json  judged tasks=150  gen tasks=755

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| 1 gold | +0.941 | yes |
| 2 amplitude | +0.889 | no |
| 3 incidence | +0.889 | yes |
| 4 breadth | +0.565 | yes |
| 5 worst mode | +0.611 | no |
| 6 combinations | +0.771 | no |
| 7 patterns | +0.706 | no |
| 8 step-amp | +0.889 | no |
| 9 recovery | +0.833 | no |
| 10 containment | +0.889 | no |

low-support code/candidate cells in method 9 (app_m < 5): 33
