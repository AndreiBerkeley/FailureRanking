# hover

Three-hop claim verification over Wikipedia abstracts. Source: the
`hover-nlp/hover` train split, filtered to claims with exactly three distinct
supporting titles. A run must retrieve all three; the gold score is 1 if it does
and 0 otherwise.

## Identities

| thing | id | where defined |
|---|---|---|
| task | the dataset's uid, e.g. `001f342b-…` | `tasks/tasks.jsonl` |
| candidate | `cnd-` + first 12 hex of sha256 of its components | `candidates/registry.jsonl` |
| trace | (candidate, task, repeat); carries a 24-hex `trace_id` | `traces/<capture>/index.jsonl` |
| capture | `cap-N` | `traces/cap-N/manifest.json` |
| split | `gepa-1`, `eval-1`, `pools-1` | `splits/<id>/split.json` |
| taxonomy | `tax-7`, `tax-18` | `taxonomies/<id>/taxonomy.json` |
| mapping | `map-N` | `mappings/map-N/manifest.json` |

## Layout

```
tasks/            registry, gold-bearing                       6,084 tasks
program/          the four-module program every candidate runs; structure.json
candidates/       registry of 40; sets/pool-2, pool-3; runs/gepa-1 (the optimizer run)
splits/gepa-1/    train 400 + validation 150                   what the optimizer saw
splits/eval-1/    sample 50 + domain 500                       never seen by the optimizer
splits/pools-1/   taxonomy 600 + judging 500 + generalization 4,984   the master partition; contains the two above
traces/cap-1/     pool-3 × gepa-1 × 1                          6,600 traces
traces/cap-2/     pool-3 × eval-1 sample × 1                     600 traces
traces/cap-3/     pool-3 × eval-1 domain × 1                   6,000 traces
outcomes/         cap-1, cap-2, cap-3 gold scores               re-derived and verified
taxonomies/       tax-7 and tax-18, with the three runs that made them
mappings/         map-1..4: the judge's reading of cap-2 and cap-3 under each taxonomy
instruments.json  fingerprints of the two instruments in force when the above were made
scripts/          migration and audit scripts
```

## How the pieces relate

The optimizer ran on `gepa-1` and proposed the 40 candidates. Twelve of them
(`pool-3`) were run on all three splits, giving the three captures. The
taxonomy generator read a 300-trace sample of `cap-1` and produced `tax-7`;
a gap test and a granularity step on further `cap-1` traces produced `tax-18`.
The judge then read `cap-2` (the sample) in full and about a third of `cap-3`
(the domain) under each taxonomy, giving the four mappings. Checkpoint 1's
first experiment compares each sample mapping with its domain mapping.

## What is here and what is not

Migrated on 2026-09-06 from `benchmarks/hover` (the v3 capture),
`runs/taxgen-v4` and `results/hover/judge-*`, all left untouched. Not migrated:
the other 28 candidates' traces (never captured), the earlier taxonomies and
judge runs of the v1 and v2 experiments, and the gold-only studies in
`results/hover/split-4-gold-scores` and `split-5-gold-scores`.

## Rules

- `traces/` and `mappings/` never contain gold. Every capture and mapping is
  scanned for gold-bearing keys before it is accepted; the result is in its
  manifest.
- A scoring path that claims to be free of gold reads `traces/` and
  `mappings/` only.
- The tasks in `splits/gepa-1` were seen by the optimizer. Scoring on them
  cannot claim to be free of optimizer influence. The taxonomies were induced
  there on purpose.
- Nothing about `splits/eval-1` `domain` may be used to build an instrument or
  a formula; it is only ever the target.
- Nothing is edited in place. A changed split, set, capture, taxonomy or
  mapping is a new id.

## Verification

```
python3 data/hover/scripts/audit_capture.py cap-1     # also cap-2, cap-3
python3 data/hover/scripts/audit_mapping.py map-1     # also map-2, map-3, map-4
```

Each re-checks an artifact from this tree alone: index against bodies, counts
against the manifest, membership in the split and candidate set, codes within
the taxonomy, and the no-gold scan.
