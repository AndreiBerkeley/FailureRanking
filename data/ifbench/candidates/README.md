# candidates — the IFBench candidate registry

One row per candidate in `registry.jsonl`. A candidate is the instruction text
for each module of the program.

| field | meaning |
|---|---|
| `candidate_id` | `cnd-` plus the first 12 hex of the sha256 of the components (sorted-key JSON) |
| `alias` | `cand-00` to `cand-11`; the artifact's own index. Reports of the earlier trial numbered them 1 to 12 |
| `components` | the instruction texts, keyed by module |
| `val_score` | the optimizer's validation aggregate on `splits/gepa-1` |
| `optimizer_best` | the candidate the optimizer judged best |
| `seed_program` | true for `cand-00`, the unmodified program |

The optimizer stopped when 12 candidates had been tracked; which were accepted
onto its frontier and which rejected was not harvested for this pool, unlike
HoVer's. `runs/gepa-1/` holds the run that produced them.
