# map-6 — `tax-10` applied to the judged sample of the judging pool

The measurement judge read 600 traces of `cap-5` (12 candidates × 50 tasks, repeat 0;
tasks named in `splits/judging-sample-2`) holding `tax-10`: 2 readers, a code counted when at least
2 agreed, plus the open reader (gemini-3.1-pro-preview) that holds no taxonomy and whose problems are mapped
afterwards. 600 judged, 0 failed. Made 2026-09-09.

| file | what it is |
|---|---|
| `mapping.jsonl` | one row per trace: ids, status, the codes that fired with their counts, which readers supplied each |
| `judge_records/<candidate>.jsonl.gz` | the full judge record per trace: panel votes, open-reader problems and their mapping |
| `manifest.json` | settings, counts, per-code firing, audits, record hashes |

Traces firing each code:

| code | traces |
|---|---:|
| `RL_04` | 250 |
| `RL_08` | 214 |
| `RL_09` | 187 |
| `RL_01` | 184 |
| `RL_10` | 182 |
| `RL_02` | 169 |
| `RL_05` | 127 |
| `RL_06` | 99 |
| `RL_03` | 95 |
| `RL_07` | 84 |

Never fired: none.
