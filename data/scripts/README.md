# scripts — shared across benchmarks

| script | what it does |
|---|---|
| `migrate_gepa_artifact_benchmark.py --benchmark <ifbench\|hotpotqa>` | rebuilds `data/<benchmark>` from `benchmarks/` and the trial directory; read-only on its sources; aborts on any failed check |
| `audit_capture.py <benchmark> <capture>` | re-checks a capture from the data tree alone: index against bodies, hashes, counts, split and set membership, no gold keys |
| `audit_mapping.py <benchmark> <mapping>` | re-checks a mapping: rows against records, hashes, capture membership, codes within the taxonomy, no gold keys |

HoVer has its own migration scripts under `data/hover/scripts/`, because its
sources have a different shape; the audits here work on it too.

## Capturing the pools-1 fills

| script | what it does |
|---|---|
| `collect_judging_gemini.sh` | command 1 of 2: runs the judging-pool fills of all three benchmarks over the direct Gemini route (`GEMINI_API_KEY`) |
| `collect_taxonomy_openrouter.sh` | command 2 of 2: runs the taxonomy-pool fills of all three benchmarks over OpenRouter, same model (`OPENROUTER_API_KEY`); checks the model slug first |
| `capture_artifact_pool.py --benchmark <ifbench\|hotpotqa> --portion <p>` | the runner behind both for the gepa-artifact benchmarks; `--dry-run` loads everything without a model call |
| `../hover/scripts/capture_pool.py --split <p>` | the HoVer runner; `--dry-run` likewise |

Fills are the task ids in `data/<benchmark>/splits/pools-1/fills.json`: pool
tasks that still lack a full-record trace for every candidate. Raw output lands
in `data/<benchmark>/traces/_incoming/pools-1-<portion>/`, resumable, and is
turned into a capture (`cap-N`) by a migration step afterwards.
