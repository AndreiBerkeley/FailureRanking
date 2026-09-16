hover-pool3  run=data/hover/mappings/map-5  taxonomy=data/hover/taxonomies/tax-10/taxonomy.json  judged tasks=50  gen tasks=500

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| 1 gold | +0.785 | no |
| 2 amplitude | +0.061 | no |
| 3 incidence | -0.320 | no |
| 4 breadth | -0.375 | no |
| 5 worst mode | -0.194 | no |
| 6 combinations | +0.242 | no |
| 7 patterns | -0.115 | no |
| 9 recovery | +0.394 | no |

low-support code/candidate cells in method 9 (app_m < 5): 18
methods 8 and 10 need per-step firings; this judge records code counts per trace only
