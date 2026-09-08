# core/ — the segmented scoring framework

The reviewed implementation of the pipeline specified in
[docs/SEGMENTS.md](../docs/SEGMENTS.md). Built 2026-08-17 with the
registries deliberately EMPTY: each method is registered later, one at a
time, after review against its axis contract.

## Modules

- `segments.py` — the five variable axes, their contracts, the option
  `Registry` (requires/provides capability tags), and the fixed ranking
  convention (higher is better, average-rank ties).
- `evidence.py` — the static segment-1 loader over the frozen adapter-15
  artifact, plus gold loading and `build_dataset` (attaching training
  gold is what enables scenario-1 configurations).
- `grid.py` — `Configuration`, `Dataset`, the compatibility mask, the
  pipeline composer (task burden -> task quality -> mean quality), full
  cross-product enumeration with optional-axis skips, and the
  (configuration, dataset)-keyed cache.
- `bench.py` — the frozen test bench: targets (cross-seed repeats 1-4,
  disjoint 250) and metrics (Kendall tau-b, Spearman rho, rank MAE,
  tie-aware top-1). Both scores and targets are higher-is-better; no
  direction flips anywhere.
- `test_core.py` — framework tests using an isolated registry with dummy
  options; the shipped `DEFAULT` registry must remain empty until methods
  are reviewed in.

Run tests from the repository root:

```bash
~/.local/share/uv/tools/adamast/bin/python -m core.test_core
```

## Acceptance test (pending)

When the historical options are registered, the acceptance criterion is
exact reproduction of the seven reference methods' scores and rankings
(the five 2026-08-12 formulas and combination-influence v1/v2) through
the grid, under the higher-is-better convention (their orderings, top-1
picks, and bench metrics must match the recorded trial results).

## Rules inherited from CLAUDE.md

Scores are computed independently per candidate; ranking happens only
after all scores exist. More evidence must affect uncertainty and
coverage, not mechanically reward or penalize a candidate. Gold enters
only through segment-4 options that declare the training-gold
requirement, which marks the configuration scenario-1; the disjoint-250
gold is reserved for the bench.
