# Rank agreement between the pools of `pools-1`

Do the three pools of the master split rank the 12 candidates the same way,
by gold score alone? Computed 2026-09-07 from `data/<benchmark>/outcomes/cap-*.jsonl`,
repeat 0 only, provider-blocked traces excluded. Gold is used here for
validation only; no trace content is read.

| file | what it is |
|---|---|
| `scripts/rank_agreement.py` | Kendall tau-b with permutation p, Spearman rho, top-1 match, top-3 overlap, per pair of pools |
| `scripts/rank_detail.py` | resolvability of each pool (spread of means vs standard error), bootstrap CI of tau, taxonomy pool split into optimizer-seen and never-seen tasks |
| `results.json` | the numbers from `rank_agreement.py`, with per-pool candidate means |

Headline: HoVer's three pools agree (tau 0.76 to 0.93, same top candidate on
all three). HotpotQA's agree moderately (0.34 to 0.51), driven by its two weak
candidates. IFBench's do not agree at all, because its candidates cannot be
told apart by gold at these pool sizes: on the 500-task judging pool 0 of 66
candidate pairs are separated by more than twice their combined standard error.
