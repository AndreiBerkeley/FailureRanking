# data — benchmarks and everything collected from them

One directory per benchmark. Inside each, four kinds of directory that are
never mixed: registries (what exists: `tasks/`, `candidates/`, `program/`),
definitions (how things were chosen: `splits/`, `candidates/sets/`), captures
(what was run: `traces/`, `outcomes/`), and instrument outputs (what was read
from the traces: `taxonomies/`, `mappings/`). Every directory carries a
`README.md` and a `provenance.json`. Artifacts are append-only: a new capture,
split, taxonomy or mapping gets a new id beside the old one.

Gold lives in `tasks/` and `outcomes/` and nowhere else. `traces/` and
`mappings/` carry none and are audited for it.

| benchmark | tasks | candidates | splits | captures | taxonomies | mappings |
|---|---:|---:|---|---|---|---|
| [hover](hover/README.md) | 6,084 | 40 (set pool-3 = 12) | gepa-1, eval-1, pools-1 | cap-1 (6,600), cap-2 (600), cap-3 (6,000), cap-4 (600), cap-5 (5,400) | tax-7, tax-18, tax-10 (re-levelled) | map-1 to map-5 |
| [ifbench](ifbench/README.md) | 13,103 | 12 | gepa-1, eval-1, pools-1 | cap-1 (6,000, 5 repeats), cap-2 (300 induction), cap-3 (4,800, judging), cap-4 (3,600, taxonomy; 1 blocked task), cap-5 (4,800, generalization; 1 blocked task) | tax-1 (13), tax-2 (13, amended) | map-1 (600) |
| [hotpotqa](hotpotqa/README.md) | 750 | 12 | gepa-1, eval-1, pools-1 | cap-1 (6,000, 5 repeats), cap-2 (2,400 domain), cap-3 (300 induction), cap-4 (4,800, generalization), cap-5 (600, judging), cap-6 (2,400, taxonomy) | tax-1 (7), tax-2 (7, amended) | map-1 (600) |
| [swebench](swebench/README.md) | 500 | none yet | none yet | none yet | none yet | none yet |

Each of the three complete benchmarks has a master partition `pools-1` with
three pools, taxonomy / judging / generalization, that contains the older
`gepa-1` and `eval-1` splits; every study draws from inside one pool. The
generalization pool is only ever the target. IFBench's domain has scores but no traces yet.
SWE-bench has tasks only; its split will follow a different design. The
earlier pipeline's taxonomies and mappings for ifbench and hotpotqa were not
carried over; they remain in `benchmarks/<benchmark>/` as the archive.

The instruments are described in [`../pipeline/README.md`](../pipeline/README.md).
Analyses that consume this data live in [`../analyses/`](../analyses/README.md).
Shared scripts are in [`scripts/`](scripts/README.md); each benchmark's
`scripts/` holds what rebuilds that benchmark.
