# swebench

SWE-bench Verified: 500 real GitHub issues from 12 Python repositories, each
with the repository state the issue was filed against. A run is given the
issue text and the repository and must produce a code patch. Gold is a set of
tests: the patch passes if the tests that failed before the fix now pass
(`FAIL_TO_PASS`) and the tests that passed before still pass (`PASS_TO_PASS`),
run inside the instance's own environment. The 500 were screened by human
annotators from the 2,294-instance SWE-bench test set for solvability and
clear specification; each carries an annotated difficulty band.

## Status

Tasks only. No program, candidates, splits, traces, taxonomies or mappings yet.
The split will follow a different design from the other benchmarks and is not
defined here.

```
tasks/      registry with gold                         500 tasks
scripts/    materialize_tasks.py: rebuilds tasks/ from the local dataset cache
```

## Identities

| thing | id |
|---|---|
| task | the SWE-bench `instance_id`, e.g. `django__django-11099` |

## What exists beyond the 500

The full SWE-bench release is in the same local cache: 2,294 test instances,
225 dev, 19,008 train. The test set is the pool the 500 were drawn from and is
available if a larger pool is wanted, at the cost of the human screening.

## Rules

- `tasks/` is gold-bearing: the gold patch, the test patch, the test lists and
  the evaluation script all live there and nowhere else.
- Running a task requires the instance's container image (`meta.image`) and the
  evaluation harness; neither is stored here.
