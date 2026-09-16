hover-pool3  run=data/hover/mappings/map-5 + data/hover/mappings/map-6  taxonomy=data/hover/taxonomies/tax-10/taxonomy.json  judged tasks=100  gen tasks=500

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| 1 gold | +1.000 | +0.742 | +0.742 | no |
| 2 amplitude | +0.032 | -0.091 | +0.742 | no |
| 3 incidence | -0.148 | -0.345 | +0.742 | no |
| 4 breadth | -0.818 | -0.636 | +0.742 | no |
| 5 worst mode | +0.000 | -0.188 | +0.742 | no |
| 6 combinations | +0.226 | +0.091 | +0.742 | no |
| 7 patterns | -0.300 | -0.250 | +0.742 | no |
| 9 recovery | +0.419 | +0.273 | +0.742 | no |

low-support code/candidate cells in method 9 (app_m < 5): 5
methods 8 and 10 need per-step firings; this judge records code counts per trace only
