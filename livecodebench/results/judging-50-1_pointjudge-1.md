livecodebench  run=runs/new_pipeline/lcb-models/pointjudge-1  taxonomy=data/livecodebench/taxonomies/tax-1/taxonomy.json  judged tasks=50  gen tasks=755

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| 1 gold | +1.000 | +0.765 | +0.765 | yes |
| 2 amplitude | +0.879 | +0.657 | +0.765 | no |
| 3 incidence | +0.812 | +0.588 | +0.765 | no |
| 4 breadth | +0.852 | +0.857 | +0.765 | yes |
| 5 worst mode | +0.630 | +0.379 | +0.765 | no |
| 6 combinations | +0.867 | +0.867 | +0.765 | no |
| 7 patterns | +0.556 | +0.786 | +0.765 | yes |
| 8 step-amp | +0.879 | +0.657 | +0.765 | no |
| 9 recovery | +0.765 | +0.667 | +0.765 | no |
| 10 containment | +0.879 | +0.657 | +0.765 | no |

low-support code/candidate cells in method 9 (app_m < 5): 37
