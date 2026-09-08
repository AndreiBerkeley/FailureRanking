# tasks — the SWE-bench Verified task registry

One row per instance. Gold-bearing.

| field | meaning |
|---|---|
| `task_id` | the `instance_id`: repository and pull request number |
| `inputs.repo`, `inputs.base_commit` | the repository and the commit the issue was filed against |
| `inputs.problem_statement`, `inputs.hints_text` | the issue text and any discussion hints |
| `inputs.version`, `inputs.environment_setup_commit`, `inputs.created_at` | environment details |
| `gold.patch` | the reference fix |
| `gold.test_patch` | the tests added with the fix |
| `gold.FAIL_TO_PASS`, `gold.PASS_TO_PASS` | the tests a correct patch must make pass, and must keep passing |
| `gold.eval_script` | the harness's evaluation script for the instance |
| `meta.difficulty` | the annotators' time-to-fix band |
| `meta.image`, `meta.eval_type`, `meta.log_parser` | harness details |

500 instances across 12 repositories; Django accounts for 231 and SymPy for 75.
Difficulty: 194 under 15 minutes, 261 between 15 minutes and an hour, 42
between one and four hours, 3 over four hours.

Read from the local Hugging Face cache of `SWE-bench/SWE-bench_Verified`
(test split) by `../scripts/materialize_tasks.py`; the cache copy used and
the arrow file's hash are in `provenance.json`.
