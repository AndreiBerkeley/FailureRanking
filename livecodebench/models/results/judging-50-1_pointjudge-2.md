livecodebench  run=runs/new_pipeline/lcb-models/pointjudge-2  taxonomy=data/livecodebench/taxonomies/tax-2/taxonomy.json  judged tasks=50  (data/livecodebench/splits/judging-50-1/split.json)  gen tasks=755

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| 1 gold | +0.765 | yes |
| 2 amplitude | +0.882 | no |
| 3 incidence | +0.771 | no |
| 4 breadth | +1.000 | yes |
| 5 worst mode | +0.576 | no |
| 6 combinations | +0.833 | no |
| 7 patterns | +0.793 | yes |
| 8 step-amp | +0.882 | no |
| 9 recovery | +0.778 | no |
| 10 containment | +0.882 | no |

low-support code/candidate cells in method 9 (app_m < 5): 50
