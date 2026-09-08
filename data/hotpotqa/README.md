# hotpotqa

HotpotQA, from the pinned gepa-artifact (commit `cbefbc1a…`). Program:
HotpotQA multi-hop program (4 modules + retrieval). Gold: HotpotQA official exact match on the answer field, 1.0 or 0.0.

## Identities

| thing | id | where defined |
|---|---|---|
| task | `hotpotqa:<key>:<hash>`, the artifact runner's id | `tasks/tasks.jsonl` |
| candidate | `cnd-` + first 12 hex of sha256 of its components | `candidates/registry.jsonl` |
| trace | (candidate, task, repeat); `trace_id` = first 24 hex of sha256 of `hotpotqa|<index>|<task>|<repeat>`, the source's own recipe | `traces/<capture>/index.jsonl` |
| capture | `cap-N` | `traces/cap-N/manifest.json` |
| split | `gepa-1`, `eval-1`, `pools-1` | `splits/<id>/split.json` |

## Layout

```
tasks/            registry, gold-bearing                       750 tasks
program/          the program every candidate runs (with structure.json)
candidates/       registry of 12; sets/pool-1; runs/gepa-1 (the optimizer run)
splits/gepa-1/    train 100 + validation 100                       what the optimizer saw
splits/eval-1/    sample 100 + domain 200                       the artifact's test set
splits/pools-1/   taxonomy 200 + judging 150 + generalization 400   the master partition; contains the two above
traces/cap-1/     pool-1 × sample × 5 repeats                      6,000 traces with stage records
traces/cap-2/     pool-1 × domain × 1                              2,400 traces, judge view only
outcomes/         recorded gold scores per capture
traces/cap-3/     induction corpus on gepa-1 train                  300 traces, judge view only
traces/cap-4/     pool-1 × pools-1 generalization fill × 1        4,800 traces, stage records + judge view
traces/cap-5/     pool-1 × pools-1 judging fill × 1                 600 traces, stage records + judge view
traces/cap-6/     pool-1 × pools-1 taxonomy fill × 1              2,400 traces, stage records + judge view
```

`taxonomies/tax-1/` (7 codes) was generated on 2026-09-07 by `new_pipeline` from the pools-1 taxonomy pool; its run record is in `taxonomies/runs/new_pipeline-run-1/`. `mappings/map-1/` applies it to the judged sample (`splits/judging-sample-1`): 12 candidates × 50 tasks × repeat 0 = 600 traces, two readers plus the open reader.

## What is here and what is not

Migrated on 2026-09-06 from `benchmarks/hotpotqa` and the trial directory
`legacy/trials/2026-08-25-gepa-cross-benchmark-candidates`, all left untouched.
Domain traces exist only in judge-view form; the runner did not keep stage records for them.
Not carried over: the earlier pipeline's taxonomy (`benchmarks/hotpotqa/taxonomies/tax-1`)
and its judge mapping (`benchmarks/hotpotqa/mappings/mapping-1`). They were made
with a different instrument, stay where they are as the archive, and are not
evidence for anything built here.

## Rules

- `traces/` and `mappings/` never contain gold; each capture and mapping is
  scanned for gold-bearing keys and the result recorded in its manifest.
- The tasks in `splits/gepa-1` were seen by the optimizer. `eval-1` `domain`
  is only ever the target.
- Nothing is edited in place. A changed split, set, capture, taxonomy or
  mapping is a new id.

## Verification

```
python3 data/scripts/audit_capture.py hotpotqa cap-1
```
