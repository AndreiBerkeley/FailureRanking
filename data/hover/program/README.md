# program — the HoVer program every candidate runs

All 40 candidates are the same program with different instructions. The
program is a four-module pipeline: it summarises the passages retrieved for the
claim, writes a query for the second hop, summarises again, and writes a query
for the third hop. Three retrievals happen between the modules and are performed
by the harness, not by the model. The final output is the set of everything
retrieved.

| module | what it does |
|---|---|
| `summarize1` | reads the claim and the first-hop passages, writes a summary |
| `create_query_hop2` | reads the claim and that summary, writes the second-hop search query |
| `summarize2` | reads the claim, the earlier context and the second-hop passages, writes a summary |
| `create_query_hop3` | reads everything so far, writes the third-hop search query |

A candidate is the four instruction texts for these modules (see
`../candidates/`). A trace of one run shows each module as a turn: the
instructions it had, what it received, and what it produced.

`structure.json` is the machine-readable description of this: the trace
format, the markers that separate turns, and the modules and their roles. Both
instruments read it, the taxonomy generator to know which agent each failure
belongs to and the judge to render a trace as turns. Copied verbatim from
`runs/taxgen-v2/structures/hover.json`.
