# tasks — the livecodebench task registry

One row per problem, metadata only. **The gold — public and hidden test cases — is not
here**; it lives in `raw/` (gitignored, 4.2 GB) and is decoded at scoring time by
`scripts/lcb.py`.

| field | meaning |
|---|---|
| `task_id` | LiveCodeBench `question_id`; the identity every other file uses |
| `title`, `platform`, `contest_id`, `contest_date` | from the source |
| `difficulty` | easy / medium / hard, as labelled by LiveCodeBench |
| `release` | which release file the problem first appeared in (v1 … v6) |
| `prompt_variant` | `starter_code` (LeetCode: complete the given class) or `stdin` (AtCoder, Codeforces) — selects which prompt variant the model receives |
| `raw_file` | where its full record and tests are |
