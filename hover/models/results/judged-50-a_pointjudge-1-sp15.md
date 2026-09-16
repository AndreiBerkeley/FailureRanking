hover  run=runs/new_pipeline/hover-models/pointjudge-1-sp15  taxonomy=data/hover/taxonomies/tax-15/taxonomy.json  judged tasks=50  gen tasks=500

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| 1 gold | +1.000 | +0.867 | +0.867 | yes |
| 2 amplitude | +0.067 | +0.000 | +0.867 | no |
| 3 incidence | +0.750 | +0.750 | +0.867 | no |
| 4 breadth | -0.391 | -0.310 | +0.867 | no |
| 5 worst mode | +0.310 | +0.314 | +0.867 | no |
| 6 combinations | -0.067 | +0.000 | +0.867 | no |
| 7 patterns | -0.200 | -0.222 | +0.867 | no |
| 8 step-amp | +0.133 | +0.111 | +0.867 | no |
| 9 recovery | +0.467 | +0.278 | +0.867 | no |
| 10 containment | +0.133 | +0.111 | +0.867 | no |

low-support code/candidate cells in method 9 (app_m < 5): 28
