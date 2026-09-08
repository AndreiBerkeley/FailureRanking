# program — the HotpotQA program every candidate runs

All 12 candidates are the same program with different instructions:
HotpotQA multi-hop program (4 modules + retrieval), from the pinned gepa-artifact.

| module | what it does |
|---|---|
| `summarize1` | reads the question and the first-hop passages, writes a summary |
| `create_query_hop2` | reads the question and that summary, writes the second-hop search query |
| `summarize2` | reads the question, the earlier context and the second-hop passages, writes a summary |
| `final_answer` | reads the question and both summaries, writes the answer |

A candidate is the instruction text for each module (see `../candidates/`). A
trace of one run records each module's inputs and outputs in order.

`structure.json` is the machine-readable description both instruments read: trace format, turn markers, modules and roles. Copied verbatim from `runs/taxgen-v2/structures/hotpotqa.json`.

Gold: HotpotQA official exact match on the answer field, 1.0 or 0.0.
