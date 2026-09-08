# candidates — the HoVer candidate registry

One row per candidate in `registry.jsonl`. A candidate is a set of four
instruction texts for the four components of the HoVer multi-hop program.

| field | meaning |
|---|---|
| `candidate_id` | `cnd-` plus the first 12 hex of the sha256 of the components (sorted-key JSON); the identity every other file uses |
| `alias` | the human name it had in the source pool (`cand-004`) |
| `components` | the four instruction texts, keyed by component name |
| `accepted` | whether the optimizer accepted it onto its frontier |
| `val_score` | the optimizer's validation score on `splits/gepa-1` |
| `origin` | which optimizer run and iteration proposed it, and its parents |

`sets/` holds named lists of ids. The `models-1` set (rows `model-00` to `model-09`) varies the solver model and holds the instructions fixed at cand-019's; for those rows `candidate_id` and `component_sha256` hash `{components, solver_model}` together, `instructions_sha256` is the hash of the text alone, and `solver_model` names the model. `runs/` holds the optimizer run that produced
the candidates, one directory per run.
