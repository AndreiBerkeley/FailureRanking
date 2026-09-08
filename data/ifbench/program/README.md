# program — the IFBench program every candidate runs

All 12 candidates are the same program with different instructions:
IFBenchCoT2StageProgram (2 modules), from the pinned gepa-artifact.

| module | what it does |
|---|---|
| `generate_response_module` | reads the prompt, writes a response |
| `ensure_correct_response_module` | reads the prompt and that response, checks it against the constraints, writes the final response |

A candidate is the instruction text for each module (see `../candidates/`). A
trace of one run records each module's inputs and outputs in order.

`structure.json` (added 2026-09-07) gives the two agents, their roles (responder, checker) and the handoffs between them, in the same form as HotpotQA's; the generator and judge read their agent list from it. Module names were checked against the traces in `cap-4`.

Gold: IFBench official per-instruction average: the fraction of the task's instructions the final response satisfies, 1.0 when all do.
