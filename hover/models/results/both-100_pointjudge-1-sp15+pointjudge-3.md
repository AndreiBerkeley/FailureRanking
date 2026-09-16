hover  run=runs/new_pipeline/hover-models/pointjudge-1-sp15 + runs/new_pipeline/hover-models/pointjudge-3  taxonomy=data/hover/taxonomies/tax-15/taxonomy.json  judged tasks=100  gen tasks=500

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| 1 gold | +0.529 | yes |
| 2 amplitude | +0.056 | no |
| 3 incidence | +0.200 | no |
| 4 breadth | -0.097 | no |
| 5 worst mode | +0.314 | no |
| 6 combinations | +0.111 | no |
| 7 patterns | -0.188 | no |
| 8 step-amp | +0.111 | no |
| 9 recovery | +0.333 | no |
| 10 containment | +0.167 | no |

low-support code/candidate cells in method 9 (app_m < 5): 19
