# outcomes — gold scores per run

One file per capture, one row per trace: `candidate_id`, `task_id`, `repeat`,
`trace_id`, `score`. Scores are the runner's recorded values of the official metric (IFBench official per-instruction average). Each file has a `.provenance.json` beside it.

Gold-bearing by construction. A scoring path that claims to be free of gold must
not read this directory.

| file | records |
|---|---:|
| `cap-1` | 6000 |
| `cap-2` | 300 |
| `cap-3` | 4800 |
| `cap-4` | 3600 |
| `cap-5` | 4800 |
| `eval-1-domain-uncaptured` | 2328 |
