hover-pool3  runs=runs/new_pipeline/hover/recovery-2-tax15  judged tasks=50  units=41  gen tasks=500

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| gold | +0.785 | no |
| recovery-weighted, per-candidate, γ=1 | +0.182 | no |
| recovery-weighted, per-candidate, γ=2 | -0.030 | no |
| recovery-weighted, per-candidate, γ=3 | -0.212 | no |
| recovery-weighted, pooled, γ=1 | -0.515 | no |
| recovery-weighted, pooled, γ=2 | -0.515 | no |
| recovery-weighted, pooled, γ=3 | -0.515 | no |

units with pooled appearances >= 10: 33 of 41; per-candidate cells under support 3: 85
