# map-5 — `tax-10` applied to the judged sample of the judging pool

The measurement judge read 600 traces of `cap-2` (12 candidates × 50 tasks, repeat 0;
tasks named in `splits/eval-1`) holding `tax-10`: 2 readers, a code counted when at least
2 agreed, plus the open reader (gemini-3.1-pro-preview) that holds no taxonomy and whose problems are mapped
afterwards. 600 judged, 0 failed. Made 2026-09-08.

| file | what it is |
|---|---|
| `mapping.jsonl` | one row per trace: ids, status, the codes that fired with their counts, which readers supplied each |
| `judge_records/<candidate>.jsonl.gz` | the full judge record per trace: panel votes, open-reader problems and their mapping |
| `manifest.json` | settings, counts, per-code firing, audits, record hashes |

Traces firing each code:

| code | traces |
|---|---:|
| `RL_04` | 245 |
| `RL_08` | 219 |
| `RL_10` | 194 |
| `RL_01` | 183 |
| `RL_09` | 182 |
| `RL_02` | 156 |
| `RL_05` | 142 |
| `RL_07` | 88 |
| `RL_06` | 86 |
| `RL_03` | 76 |

Never fired: none.
