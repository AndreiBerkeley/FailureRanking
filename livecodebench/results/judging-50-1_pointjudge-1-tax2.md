livecodebench  run=runs/new_pipeline/lcb-models/pointjudge-1-tax2  taxonomy=data/livecodebench/taxonomies/tax-2/taxonomy.json  judged tasks=50  gen tasks=755

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| 1 gold | +1.000 | +0.765 | +0.765 | yes |
| 2 amplitude | +0.818 | +0.941 | +0.765 | yes |
| 3 incidence | +0.939 | +0.824 | +0.765 | yes |
| 4 breadth | +0.667 | +0.812 | +0.765 | yes |
| 5 worst mode | +0.630 | +0.379 | +0.765 | no |
| 6 combinations | +0.758 | +1.000 | +0.765 | yes |
| 7 patterns | +0.576 | +0.829 | +0.765 | yes |
| 8 step-amp | +0.818 | +0.941 | +0.765 | yes |
| 9 recovery | +0.758 | +0.829 | +0.765 | yes |
| 10 containment | +0.818 | +0.941 | +0.765 | yes |

low-support code/candidate cells in method 9 (app_m < 5): 49
