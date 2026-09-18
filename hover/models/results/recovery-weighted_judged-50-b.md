hover  runs=runs/new_pipeline/hover-models/recovery-1  judged tasks=50  units=59  gen tasks=500

| method | tau vs gold-gen | top-1 |
|---|---:|---|
| gold | +0.444 | yes |
| recovery-weighted, per-candidate, γ=1 | +0.778 | no |
| recovery-weighted, per-candidate, γ=2 | +0.833 | no |
| recovery-weighted, per-candidate, γ=3 | +0.889 | no |
| recovery-weighted, pooled, γ=1 | +0.778 | no |
| recovery-weighted, pooled, γ=2 | +0.722 | no |
| recovery-weighted, pooled, γ=3 | +0.722 | no |

units with pooled appearances >= 10: 35 of 59; per-candidate cells under support 3: 110
