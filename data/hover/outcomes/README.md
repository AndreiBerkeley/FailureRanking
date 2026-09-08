# outcomes — gold scores per trace

One file per capture, one row per trace: `candidate_id`, `task_id`, `repeat`,
`trace_id`, `score`. Derived by a scorer that reads the task registry's gold and
the trace's prediction; nothing here is copied from the source tree, and the
re-derived scores were checked equal to the recorded ones for every trace. Each
file has a `<capture>.provenance.json` beside it.

Gold-bearing by construction. Any scoring path that claims to be free of gold
must not read this directory.

| capture | records | scorer |
|---|---:|---|
| `cap-1` | 6600 | HoVer retrieval metric: 1 iff all three gold titles retrieved |
| `cap-2` | 600 | HoVer retrieval metric: 1 iff all three gold titles retrieved |
| `cap-3` | 6000 | HoVer retrieval metric: 1 iff all three gold titles retrieved |
| `cap-4` | 600 | HoVer retrieval metric: 1 iff all three gold titles retrieved |
| `cap-5` | 5400 | HoVer retrieval metric: 1 iff all three gold titles retrieved |
