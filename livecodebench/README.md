# livecodebench

Competitive programming: one model call writes a Python program for a problem, and the
program is run against the problem's hidden tests. Release_v6, 1,055 problems (AtCoder 602,
LeetCode 444, Codeforces 9; easy/medium/hard 322/383/350). Gold = every test passed.

```
program/        prompt.md (the exact prompt, both variants), structure.json (one agent, single step)
tasks/          tasks.jsonl (registry: id, title, platform, difficulty, contest date, prompt variant — no tests),
                splits/pools-1 (the master split), code_generation_lite.py (loader for the raw release)
models/         the 9-model candidate set — the only candidate set on this benchmark
```

**The program** is one turn: system prompt "You are an expert Python programmer…", user
prompt = problem statement + the official format block (starter-code variant for LeetCode
problems, stdin variant for the rest), verbatim in `program/prompt.md`. The first
```` ```python ```` fence of the reply is executed; nothing else in the reply matters to the
harness. A trace is therefore the problem, the reply, and nothing between — no tools, no
feedback, no second turn.

**Master split `pools-1`** (seed 2026, task-disjoint): taxonomy 150 (50/50/50 by
difficulty), judging 150 (50/50/50), generalization 755 (222/283/250).

**Tests are not here.** The hidden tests (4.2 GB) are LiveCodeBench's own: download
release_v6 from the `livecodebench/code_generation_lite` dataset on Hugging Face into
`tasks/raw/`, clone the upstream `LiveCodeBench` repository for its runner, and
`code/livecodebench_scripts/capture.py score` reproduces every outcome file on this branch.
