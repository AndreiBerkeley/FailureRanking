# new_pipeline — the v2 taxonomy pipeline with refinement and certification

One pool of traces in, one certified taxonomy out. Generation is the v2
generator exactly as it produced the current HoVer taxonomies; what is new is
that its draft is then refined against a judge's reading of a second corpus,
certified by an interannotation gate on a third, and only then put through the
v2 follow-up checks. Codes carry a column, `general` or `domain`. There are no
A, B, C categories anywhere in this package.

## The steps

```
pool of judge-view traces
  └─ 0  split by task into generation (N) / refinement (~N/2) / gate (60 over ≥30 tasks) + fresh remainder
  └─ 1  generation, stages 1–6                       generation/run.py      -> draft
  └─ 2  baseline gate on the draft (diagnostic)      gate.py
  └─ 3  round k (default one round):
          judge the refinement corpus                judge/run.py
          refine: checklist panel, consolidation,
                  operations (stage 7)               refine.py             -> R{k}_… ids
          gate on the gate corpus (stage 8)          gate.py               pass: κ ≥ 0.75, coverage ≥ 0.70
  └─ 4  follow-ups on fresh traces: gap test, granularity split, apply     -> taxonomy_final.json
```

Nothing in the gate corpus reaches the refiner. No outcome reaches any model:
traces are stripped at every boundary and a run refuses to start otherwise.

## Run it

```
python3 -m new_pipeline.export_pool --benchmark hover --portion taxonomy --out runs/new_pipeline/hover/pool_taxonomy
python3 -m new_pipeline.run --benchmark hover --pool runs/new_pipeline/hover/pool_taxonomy \
    --structure data/hover/program/structure.json --out runs/new_pipeline/hover/run-1 --n-generation 100
```

`--model` names the model for the generator, the refiner and the judge's panel;
an `openrouter/<vendor>/<model>` id routes through OpenRouter. `--open-model`
sets the judge's open reader. `--rounds`, `--refine-panel`, `--gate-readers`,
`--kappa-target`, `--coverage-floor`, `--no-baseline-gate`, `--skip-followups`
do what they say. `--dry-run` splits the corpora, dry-runs generation, and
prints every later command without a model call. Every step is resumable: a
finished artifact is not redone, so an interrupted run continues from the same
command.

## What to read first, in order

1. This file.
2. `../GENERATION_v2.md`: the design and the prompts themselves. Stages 1–6 are
   generation, stage 7 the refinement round, stage 8 the gate. `generation/prompts.py`
   parses that document at import, so the document is the prompt source.
3. `run.py`: the orchestration above, with the state file it keeps.
4. `corpora.py`: the task-disjoint split and why it is by task.
5. `generation/run.py`, `generation/contracts.py`, `generation/render.py`: stages 1–6.
6. `refine.py`: the evidence it gathers from the judge's records, the three calls,
   the derived verdicts, and how operations are applied and ids reissued.
7. `gate.py`: Fleiss' kappa over (trace, code) subjects and coverage from the
   open reader; `--measure-only` recomputes them from any finished judge run.
8. `judge/run.py`, `judge/judge.py`: the judge, panel plus open reader.
9. `generation/gaps.py`, `generation/granularity.py`, `generation/apply_splits.py`: the follow-ups.
10. `goldfree.py`, `llm.py`, `export_pool.py`: outcome stripping, the model
    transports, and how a pool is exported from `data/`.

## Provenance and status

`generation/`, `judge/`, `goldfree.py` and `corpora.py` are copies of
`pipeline/taxonomy2`, `pipeline/measure`, `pipeline/goldfree.py` and
`pipeline/taxonomy/corpora.py` as of 2026-09-06, with package-relative imports
and no absolute paths; `llm.py` is the model-transport section of
`pipeline/taxonomy/stages.py`. `refine.py`, `gate.py`, `run.py` and
`export_pool.py` are new. The refinement round and the gate have been exercised
offline only: the gate's agreement measure on the existing two-reader HoVer
mappings, the refiner's evidence and prompts on the same records, and the
operation logic on synthetic input. An end-to-end run with model calls is the
remaining test.
