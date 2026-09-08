# new_taxonomies — the current failure-mode taxonomy of each benchmark

One directory per benchmark: `taxonomy.json` (the codes with definitions, use / do-not-use
boundaries, columns and ids), the artifact's own `README.md` (code table and, for amended
versions, every amendment with its before, after and reason) and its `provenance.json`. They are
copies of the artifacts in `data/<benchmark>/taxonomies/`, where the ids and hashes are authoritative.

| benchmark | artifact | codes | general | domain | how it was made |
|---|---|---:|---:|---:|---|
| [`hover`](hover/README.md) | `tax-10` | 10 | 4 | 6 | tax-18 re-levelled by hand on 2026-09-07: 10 of its 18 codes could only fire where a candidate's own instructions defined the artifact breached, so every code now names a mechanism any candidate could exhibit, with the specifics moved into per-code evidence |
| [`ifbench`](ifbench/README.md) | `tax-2` | 13 | 6 | 7 | tax-1 (new_pipeline: generation, one refinement round, gate, gap test, splits) with 11 hand amendments to 4 codes' wording after review of map-1 |
| [`hotpotqa`](hotpotqa/README.md) | `tax-2` | 7 | 3 | 4 | tax-1 (new_pipeline, same steps) with 6 hand amendments to 3 codes' wording after review of map-1 |

The amendments change wording only: the code sets, ids and columns are those of the generated
versions (`ifbench/tax-1`, `hotpotqa/tax-1`); HoVer's also changes the code set, from 18 to 10.
The most consequential wording change, on
every benchmark, states that the `[[ ## field ## ]]` markers and the `reasoning` field are the
execution harness's own output format and never a failure; the judge and the generator now say
the same in their trace-layout notes.

A code names a failure mechanism observable in a trace, in one of two columns: `general`,
the mistake is at the edges of an agent's execution, in taking its input in or forming its
output; `domain`, it is in the work between. No code names an agent, an outcome or a remedy;
those are recorded per occurrence. The framework and the prompts are in `GENERATION_v2.md`;
the generator, refinement round and gate are `new_pipeline/`.
