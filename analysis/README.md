# analysis — traces worth reading

Three folders, one per (benchmark, candidate set). Each holds 20–30 traces chosen because the
judge's reading of them says something about why the trace methods rank the candidates well
(livecodebench) or not at all (hover): points on passing runs, failing runs with no point,
codes that fire on winners and losers alike, firings that later steps carried or did not.

| folder | benchmark · candidates | judge | what to look for |
|---|---|---|---|
| `livecodebench_model/` | livecodebench · 9 models | pointjudge-2, tax-2 | the pass/fail asymmetry that makes amplitude work, and its edges |
| `model_hover/` | hover · 9 models | pointjudge-1-sp15 + pointjudge-3, tax-15 | form codes on passing runs; retrieval misses with nothing to quote |
| `gepa-candidates_hover/` | hover · 12 instruction sets | map-5 + map-6, tax-10 | near-universal firing; the one clean candidate ranking backwards |

Each folder: `README.md` (categories, one row per case with the observation), `cases.json`
(the same, machine-readable), `traces/<trace_id>.json` (the trace as the judge saw it),
`judge/<trace_id>.json` (the judge's record for it — points with step, evidence and codes, or
the panel's votes by turn and the open reader's problems). Selection is deterministic and is
reproduced by `code/select_analysis_cases.py`; it reads gold only to choose cases, which is the
point of the folder.
