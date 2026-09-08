# runs — the instrument runs that produced the taxonomies

| run | what it did | produced |
|---|---|---|
| `taxgen-1` | generation: six model calls over cap-1 traces with outcomes stripped, from domain analysis to rule validation; every stage's prompt and raw response is kept | `../tax-7` |
| `taxgen-2` | gap test: from a pool of 5400 cap-1 traces on tasks the generator had not read, observed a fixed sample of 300 without the taxonomy in view, then asked which observations `tax-7` could express; the records it produced are what the split step was verified on | records for `taxgen-3` |
| `taxgen-3` | granularity: proposed splits of `tax-7` codes that carry several mechanisms and accepted only those whose parts occur independently in the records | `../tax-18` |

Each directory is a verbatim copy of the run as it was left, except that
`taxgen-2`'s copy of its input traces is replaced by the list of their ids
(`fresh_corpus_trace_ids.json`); the traces themselves are in `../../traces/cap-1`.
Source locations: `runs/taxgen-v4/hover`, `hover-gaps`, `hover-granularity`.
