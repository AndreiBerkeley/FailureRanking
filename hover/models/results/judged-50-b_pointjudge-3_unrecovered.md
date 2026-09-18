hover  run=runs/new_pipeline/hover-models/pointjudge-3-unrecovered  taxonomy=data/hover/taxonomies/tax-15/taxonomy.json  judged tasks=50  (data/hover/splits/models-1-judged-50-b/split.json)  gen tasks=500

| method | tau vs gold-gen | top-1 | tau vs gold-50 | top-1 (gold-50) |
|---|---:|---|---:|---|
| 1 gold | +0.444 | yes | +1.000 | yes |
| 2 amplitude | +0.722 | no | +0.389 | no |
| 3 incidence | +0.750 | no | +0.312 | no |
| 4 breadth | +0.355 | no | -0.097 | no |
| 5 worst mode | +0.829 | no | +0.257 | no |
| 6 combinations | +0.611 | yes | +0.278 | yes |
| 7 patterns | +0.515 | no | +0.212 | no |
| 8 step-amp | +0.714 | no | +0.257 | no |
| 9 recovery | +0.829 | yes | +0.429 | yes |
| 10 containment | +0.771 | no | +0.200 | no |
| 13 last-turn incidence | +0.758 | no | +0.333 | no |

low-support code/candidate cells in method 9 (app_m < 5): 45
