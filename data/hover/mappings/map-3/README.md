# map-3 — `tax-18` read over `cap-2` (sample portion)

**Complete: every trace of `cap-2` judged.**

The judge held `tax-18` and read each trace of `cap-2` turn by turn, recording
which codes occurred and how many times. Two readers holding the taxonomy voted
(a code fires when both report it); one reader holding no vocabulary listed
problems, which were then mapped onto the taxonomy. A trace's codes are the
union of the two.

| | |
|---|---|
| panel | 2 readers, `openrouter/google/gemini-3.6-flash`, threshold 2 |
| open reader | `openrouter/google/gemini-3.1-pro-preview` |
| route | openrouter |
| thinking | HIGH; traces per call 5; traces never truncated |
| attempted / judged / failed | 600 / 600 / 0 |
| problems the open reader found that mapped to no code | 37 |

| file | what it is |
|---|---|
| `mapping.jsonl` | one row per attempted trace: ids, status, the codes that fired and how often, which branch reported each |
| `judge_records/<candidate_id>.jsonl.gz` | the full judge output per trace: each reader's answer per turn, the open reader's problems and their mapping |
| `manifest.json` | settings, counts, coverage, per-code firing counts, audit results |

Traces firing each code, most to least: `SP_02` 424, `SP_01` 182, `SP_07` 173, `SP_06` 150, `SP_17` 136, `SP_03` 107, `SP_15` 78, `SP_09` 68, `SP_05` 53, `SP_18` 48, `SP_10` 44, `SP_08` 27, `SP_16` 27, `SP_14` 23, `SP_13` 21, `SP_11` 20, `SP_12` 20, `SP_04` 14.

No gold reaches the judge and none appears here; the judge's own check that
nothing had to be stripped is recorded for every trace. Source:
`results/hover/judge-tax18-judging`.
