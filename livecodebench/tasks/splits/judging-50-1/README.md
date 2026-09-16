# judging-50-1 — the 50 judged tasks of the judging pool

50 tasks drawn from `pools-1/judging` (150), seeded within difficulty, before any candidate
ran on that pool. Easy is under-weighted because the taxonomy pool showed 39 of 50 easy
tasks solved by all nine candidates (no ranking information); medium and hard discriminate.

| difficulty | platform | release | prompt variant |
|---|---|---|---|
| {'easy': 16, 'hard': 17, 'medium': 17} | {'atcoder': 28, 'leetcode': 22} | {'v1': 22, 'v2': 5, 'v3': 5, 'v4': 5, 'v5': 7, 'v6': 6} | {'starter_code': 22, 'stdin': 28} |

Use: `capture.py capture --split judging-50-1 --portion judging ...`. The other 100 judging-pool
tasks stay unused; nothing crosses into taxonomy or generalization.

Built by `scripts/build_judging_subset.py`; the same seed reproduces it exactly.
