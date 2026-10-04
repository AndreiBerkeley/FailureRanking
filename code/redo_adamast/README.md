# redo_adamast — code snapshots of Andrei's RedoAdamast workspace

`~/Desktop/RedoAdamast` is not a git repository, so the code that produced the runs copied into
`data/<swebench|tau2bench|bfcl>/` (`taxonomies/tax-1`, `mappings/map-1`, `splits/pools-4`, `traces/view-1`)
is kept here as it stood when they were copied.

- `code-1/` — `RedoAdamast/generation/` on 2026-09-29, minus `__pycache__`. `run.py` generates a taxonomy,
  `judge.py` judges traces against it, `select_tasks.py` / `prepare_data.py` / `export_test.py` draw and export
  the traces, `llm.py` is the transport. `code-1.provenance.json` has the sha256 of every file.

A later snapshot is `code-2`, next to this one.
