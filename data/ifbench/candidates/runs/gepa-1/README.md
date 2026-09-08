# gepa-1 — the optimizer run that produced the candidates

GEPA 0.1.4 on split `gepa-1`, task model `gemini/gemini-3.1-flash-lite`, reflection model
`gemini/gemini-3.6-flash`, Pareto selection, merge disabled, stopped when 12
tracked candidates were recorded. Run 2026-08-25 as
`legacy/trials/2026-08-25-gepa-cross-benchmark-candidates/runs/ifbench_g31lite_g36_seed0_representative_v3`;
copied here on 2026-09-06.

| file | what it is |
|---|---|
| `gepa_result.json` | the optimizer's result object: candidates, validation aggregates, best index |
| `run_config.json`, `split_manifest.json` | settings and the split it saw |
| `usage.json`, `usage_launches/`, `launcher.log` | cost, call counts, log |
| `gepa_run.tar.gz` | the optimizer's working directory, archived whole |

An earlier run of the same launcher (`ifbench_g31lite_g36_seed0_v1`) is invalid and
was stopped: it drew the first 100 records of an ordered pool. It is not copied.
