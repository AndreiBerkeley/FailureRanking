# map-1 — `tax-7` read over `cap-2` (sample portion)

**Complete: every trace of `cap-2` judged.**

The judge held `tax-7` and read each trace of `cap-2` turn by turn, recording
which codes occurred and how many times. Two readers holding the taxonomy voted
(a code fires when both report it); one reader holding no vocabulary listed
problems, which were then mapped onto the taxonomy. A trace's codes are the
union of the two.

| | |
|---|---|
| panel | 2 readers, `gemini-3.6-flash`, threshold 2 |
| open reader | `gemini-3.1-pro-preview` |
| route | gemini-direct |
| thinking | HIGH; traces per call 5; traces never truncated |
| attempted / judged / failed | 600 / 600 / 0 |
| problems the open reader found that mapped to no code | 32 |

| file | what it is |
|---|---|
| `mapping.jsonl` | one row per attempted trace: ids, status, the codes that fired and how often, which branch reported each |
| `judge_records/<candidate_id>.jsonl.gz` | the full judge output per trace: each reader's answer per turn, the open reader's problems and their mapping |
| `manifest.json` | settings, counts, coverage, per-code firing counts, audit results |

Traces firing each code, most to least: `FM_001` 487, `FM_003` 257, `FM_006` 129, `FM_002` 107, `FM_004` 81, `FM_005` 51, `FM_007` 38.

No gold reaches the judge and none appears here; the judge's own check that
nothing had to be stripped is recorded for every trace. Source:
`results/hover/judge-tax2-judging`.
