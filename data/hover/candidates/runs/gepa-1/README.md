# gepa-1 — the optimizer run that produced the candidates

GEPA, seed 0, on split `gepa-1`, task model `gemini/gemini-3.1-flash-lite`,
reflection model `gemini/gemini-3.1-pro-preview`. Run 2026-08-29 as
`benchmarks/hover/pools/pool-2/runs/seed0`; copied whole here on 2026-09-06.

| file | what it is |
|---|---|
| `run_config.json` | every setting the run was launched with |
| `result.json` | the optimizer's own result object: frontier, parents, per-instance bests |
| `usage.json`, `usage_launches/` | cost and call counts |
| `candidates.json`, `gepa_state.json`, `gepa_state.bin` | the optimizer's candidate list and resumable state |
| `pareto/`, `generated_best_outputs_valset/`, `candidate_tree.html` | its frontier, best outputs, and lineage view |
| `logs/` | stdout, stderr, structured log |
| `iterations.tar.gz` | the full per-iteration tree, archived whole |

The candidates harvested from this run are the registry in `../../registry.jsonl`.
