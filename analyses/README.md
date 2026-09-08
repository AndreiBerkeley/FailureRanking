# analyses — the proof behind each checkpoint

Every checkpoint in [`roadmap/checkpoints/checkpoints.md`](../roadmap/checkpoints/checkpoints.md)
needs its own evidence, produced from the data in [`data/`](../data/INDEX.md).
This is where that evidence is made and kept.

## Layout

```
analyses/
  checkpoint-1/
    <experiment-id>/
      README.md         question, reasoning, what was done, result, what it does and does not settle
      provenance.json   which captures, splits, sets and instruments it read, by id and hash
      scripts/          the code that produced results/, runnable from the repo root
      results/          outputs only: tables, figures, JSON
  checkpoint-2/
  ...
```

## Rules

- An experiment reads `data/` by id and never copies it. Its provenance names
  every capture, split and set it used.
- `results/` holds outputs only. Anything an experiment derives that another
  experiment might reuse is promoted to `data/` as a new artifact with its
  own provenance, not left in `results/`.
- An experiment directory is created when work starts. It is entered in
  [`roadmap/checkpoints/methodology.md`](../roadmap/checkpoints/methodology.md)
  only once it is finished and its result is stable; that entry points here
  under "where the evidence lives".
- Experiment ids are short and dated, e.g. `2026-09-profile-stability`. They
  are never reused.

## Status

| checkpoint | experiments | finished |
|---|---:|---:|
| 1 | 1 | 0 |
