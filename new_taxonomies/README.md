# new_taxonomies — the current failure-mode taxonomy of each benchmark

One directory per benchmark: `taxonomy.json` (the codes with definitions, use / do-not-use
boundaries, columns and ids), the artifact's own `README.md` (code table and how it was made)
and its `provenance.json`. They are copies of the artifacts in `data/<benchmark>/taxonomies/`,
where the ids and hashes are authoritative.

| benchmark | artifact | codes | general | domain | how it was made |
|---|---|---:|---:|---:|---|
| [`hover`](hover/README.md) | `tax-18` | 18 | 7 | 11 | v2 generation on cap-1 traces, then granularity splits of tax-7 (2026-09-06); no refinement round or gate yet |
| [`ifbench`](ifbench/README.md) | `tax-1` | 13 | 6 | 7 | new_pipeline on the pools-1 taxonomy pool: v2 generation, one refinement round, interannotation gate, gap test, granularity splits (2026-09-07) |
| [`hotpotqa`](hotpotqa/README.md) | `tax-1` | 7 | 3 | 4 | new_pipeline on the pools-1 taxonomy pool: same steps (2026-09-07) |

A code names a failure mechanism observable in a trace, in one of two columns: `general`,
the mistake is at the edges of an agent's execution, in taking its input in or forming its
output; `domain`, it is in the work between. No code names an agent, an outcome or a remedy;
those are recorded per occurrence. The framework and the prompts are in `GENERATION_v2.md`;
the generator, refinement round and gate are `new_pipeline/`.
