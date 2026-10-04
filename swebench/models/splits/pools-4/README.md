# pools-4 — RedoAdamast's generation and test draw (swebench)

| portion | tasks | traces | role |
|---|---:|---:|---|
| taxonomy | 30 (initial 20, seg1 5, final 5) | 90 | generated `taxonomies/tax-1` |
| judged | 50 | 600 (all 12 candidates, one run each) | judged by `mappings/map-1` |
| eval | 405 | 4,860 outcomes | generalization target |

Drawn by RedoAdamast (`select_tasks.py`, `export_test.py`, seed 0; snapshot in `data/redo_adamast/code-1`), not
by our `make_split.py`: not stratified, and unrelated to `pools-1`..`pools-3`. **eval** = every task all
12 candidates ran that is in neither portion.
The 15 cap-1 tasks some candidate did not run are in no portion; see
`outcomes/cap-1-complete.provenance.json`.
