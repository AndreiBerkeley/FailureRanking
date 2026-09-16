hover  run=runs/new_pipeline/hover-models/pointjudge-3  taxonomy=data/hover/taxonomies/tax-15/taxonomy.json  judged tasks=50  gen tasks=500

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| 1 gold | +0.444 | yes |
| 2 amplitude | -0.056 | no |
| 3 incidence | +0.200 | no |
| 4 breadth | -0.059 | no |
| 5 worst mode | +0.257 | no |
| 6 combinations | +0.056 | no |
| 7 patterns | -0.167 | no |
| 8 step-amp | +0.000 | no |
| 9 recovery | +0.333 | no |
| 10 containment | +0.000 | no |

low-support code/candidate cells in method 9 (app_m < 5): 32
