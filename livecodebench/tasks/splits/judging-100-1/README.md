# judging-100-1 — the rest of the judging pool

The 100 `pools-1/judging` tasks not in `judging-50-1`; together the two are the whole
150-task judging pool. Set difference, no draw, built before any candidate ran on them.

| difficulty | platform | release | prompt variant |
|---|---|---|---|
| {'easy': 34, 'hard': 33, 'medium': 33} | {'atcoder': 58, 'leetcode': 42} | {'v1': 40, 'v2': 13, 'v3': 8, 'v4': 12, 'v5': 12, 'v6': 15} | {'starter_code': 42, 'stdin': 58} |

Use: `capture.py capture --split judging-100-1 --portion judging ...`; export together with
`models-1-judging50` into one 150-task pool.

Built by `scripts/build_judging_rest.py`.
