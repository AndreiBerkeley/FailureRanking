hover-pool3  run=data/hover/mappings/map-5  taxonomy=data/hover/taxonomies/tax-10/taxonomy.json  judged tasks=50  gen tasks=500

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| 1 gold | +1.000 | +0.785 | +0.785 | no |
| 2 amplitude | +0.046 | +0.061 | +0.785 | no |
| 3 incidence | -0.184 | -0.320 | +0.785 | no |
| 4 breadth | -0.548 | -0.375 | +0.785 | no |
| 5 worst mode | -0.082 | -0.194 | +0.785 | no |
| 6 combinations | +0.231 | +0.242 | +0.785 | no |
| 7 patterns | -0.267 | -0.115 | +0.785 | no |
| 9 recovery | +0.446 | +0.394 | +0.785 | no |

low-support code/candidate cells in method 9 (app_m < 5): 18
methods 8 and 10 need per-step firings; this judge records code counts per trace only
