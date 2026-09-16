hover-pool3  run=data/hover/mappings/map-6  taxonomy=data/hover/taxonomies/tax-10/taxonomy.json  judged tasks=50  gen tasks=500

| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |
|---|---:|---:|---:|---|
| 1 gold | +1.000 | +0.367 | +0.367 | no |
| 2 amplitude | +0.017 | -0.077 | +0.367 | no |
| 3 incidence | -0.347 | -0.283 | +0.367 | no |
| 4 breadth | -0.800 | -0.636 | +0.367 | no |
| 5 worst mode | +0.000 | +0.048 | +0.367 | no |
| 6 combinations | +0.233 | +0.000 | +0.367 | no |
| 7 patterns | -0.018 | -0.322 | +0.367 | no |
| 9 recovery | +0.633 | +0.121 | +0.367 | no |

low-support code/candidate cells in method 9 (app_m < 5): 15
methods 8 and 10 need per-step firings; this judge records code counts per trace only
