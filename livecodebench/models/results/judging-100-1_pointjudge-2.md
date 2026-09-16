livecodebench  run=runs/new_pipeline/lcb-models/pointjudge-2  taxonomy=data/livecodebench/taxonomies/tax-2/taxonomy.json  judged tasks=100  (data/livecodebench/splits/judging-100-1/split.json)  gen tasks=755

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| 1 gold | +0.886 | yes |
| 2 amplitude | +0.829 | no |
| 3 incidence | +0.889 | yes |
| 4 breadth | +0.391 | no |
| 5 worst mode | +0.647 | yes |
| 6 combinations | +0.722 | no |
| 7 patterns | +0.576 | no |
| 8 step-amp | +0.829 | no |
| 9 recovery | +0.778 | no |
| 10 containment | +0.829 | no |

low-support code/candidate cells in method 9 (app_m < 5): 41
