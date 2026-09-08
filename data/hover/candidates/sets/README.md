# sets — named lists of candidate ids

A set is a list of ids pointing into `../registry.jsonl`, with the rule that
chose them. It never copies a candidate.

| set | size | rule |
|---|---:|---|
| `pool-2` | 40 | every candidate the optimizer run proposed: 20 accepted, 20 rejected drawn uniformly |
| `pool-3` | 12 | 8 accepted at even intervals over validation score, 4 rejected at even intervals; spans the full score range |
