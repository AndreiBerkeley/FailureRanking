# pools-1 — the master split for livecodebench

Three task-disjoint pools over all 1,055 release_v6 problems. Every later study draws
from inside one pool; nothing crosses pools.

| pool | size | easy / medium / hard | starter-code / stdin |
|---|---:|---|---|
| taxonomy | 150 | 50 / 50 / 50 | 57 / 93 |
| judging | 150 | 50 / 50 / 50 | 64 / 86 |
| generalization | 755 | 222 / 283 / 250 | 323 / 432 |

Taxonomy and judging were drawn by seed 2026 within each difficulty tier; generalization
is everything left. Platform and release were not stratified — their per-pool counts are
recorded in `split.json` under `stratum_counts` and land close to the corpus proportions
by the draw alone.

Gold (the test cases) is not in this directory; it stays in `tasks/raw/`.

Built by `scripts/build_split.py`; regenerating with the same seed reproduces it exactly.
