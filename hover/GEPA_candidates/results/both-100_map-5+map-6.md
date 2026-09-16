hover-pool3  run=data/hover/mappings/map-5 + data/hover/mappings/map-6  taxonomy=data/hover/taxonomies/tax-10/taxonomy.json  judged tasks=100  gen tasks=500

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| 1 gold | +0.742 | no |
| 2 amplitude | -0.091 | no |
| 3 incidence | -0.345 | no |
| 4 breadth | -0.636 | no |
| 5 worst mode | -0.188 | no |
| 6 combinations | +0.091 | no |
| 7 patterns | -0.250 | no |
| 9 recovery | +0.273 | no |

low-support code/candidate cells in method 9 (app_m < 5): 5
methods 8 and 10 need per-step firings; this judge records code counts per trace only
