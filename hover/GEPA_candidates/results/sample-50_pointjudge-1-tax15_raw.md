hover-pool3  run=runs/new_pipeline/hover/pointjudge-1-tax15  taxonomy=data/hover/taxonomies/tax-15-pool3/taxonomy.json  judged tasks=50  gen tasks=500

| method | tau vs gold-gen | top-1 | tau vs gold-50 | top-1 (gold-50) |
|---|---:|---|---:|---|
| 1 gold | +0.785 | no | +1.000 | yes |
| 2 amplitude | -0.424 | no | -0.415 | no |
| 3 incidence | -0.409 | no | -0.636 | no |
| 4 breadth | -0.519 | no | -0.509 | no |
| 5 worst mode | -0.587 | no | -0.683 | no |
| 6 combinations | -0.242 | no | -0.169 | no |
| 7 patterns | -0.206 | no | -0.226 | no |
| 8 step-amp | -0.364 | no | -0.354 | no |
| 9 recovery | +0.415 | no | +0.594 | yes |
| 10 containment | -0.333 | no | -0.262 | no |
| 13 last-turn incidence | +0.365 | no | +0.484 | no |

low-support code/candidate cells in method 9 (app_m < 5): 34
steps for methods 8 and 10: panel votes_by_turn and open-reader agents, from judge_records
