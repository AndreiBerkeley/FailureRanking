# map-4 — `tax-18` read over `cap-3` (domain portion)

**Partial: 2,187 of 6,000 traces of `cap-3` judged (36%).** The judge run stopped there; the judged traces are spread evenly over the 12 candidates (172 to 193 each). A later run that completes the capture becomes a new mapping beside this one.

The judge held `tax-18` and read each trace of `cap-3` turn by turn, recording
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
| attempted / judged / failed | 2,187 / 2,187 / 0 |
| problems the open reader found that mapped to no code | 122 |

| file | what it is |
|---|---|
| `mapping.jsonl` | one row per attempted trace: ids, status, the codes that fired and how often, which branch reported each |
| `judge_records/<candidate_id>.jsonl.gz` | the full judge output per trace: each reader's answer per turn, the open reader's problems and their mapping |
| `manifest.json` | settings, counts, coverage, per-code firing counts, audit results |

Traces firing each code, most to least: `SP_02` 1625, `SP_01` 664, `SP_07` 585, `SP_17` 523, `SP_06` 495, `SP_03` 412, `SP_15` 296, `SP_09` 250, `SP_18` 179, `SP_10` 157, `SP_14` 125, `SP_05` 111, `SP_13` 106, `SP_11` 98, `SP_12` 74, `SP_16` 70, `SP_08` 64, `SP_04` 54.

No gold reaches the judge and none appears here; the judge's own check that
nothing had to be stripped is recorded for every trace. Source:
`results/hover/judge-tax18-generalization`.
