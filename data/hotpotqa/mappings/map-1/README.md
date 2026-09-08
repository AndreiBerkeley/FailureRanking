# map-1 — `tax-1` applied to the judged sample of the judging pool

The measurement judge read 600 traces of `cap-1` (12 candidates × 50 tasks, repeat 0;
tasks named in `splits/judging-sample-1`) holding `tax-1`: 2 readers, a code counted when at least
2 agreed, plus the open reader (openrouter/google/gemini-3.1-pro-preview) that holds no taxonomy and whose problems are mapped
afterwards. 600 judged, 0 failed. Made 2026-09-07.

| file | what it is |
|---|---|
| `mapping.jsonl` | one row per trace: ids, status, the codes that fired with their counts, which readers supplied each |
| `judge_records/<candidate>.jsonl.gz` | the full judge record per trace: panel votes, open-reader problems and their mapping |
| `manifest.json` | settings, counts, per-code firing, audits, record hashes |

Traces firing each code:

| code | traces |
|---|---:|
| `SP_01` | 395 |
| `SP_07` | 306 |
| `SP_04` | 121 |
| `SP_02` | 63 |
| `SP_06` | 31 |
| `SP_03` | 2 |
| `SP_05` | 2 |

Never fired: none.
