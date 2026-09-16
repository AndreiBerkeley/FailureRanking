# tax-1 — first livecodebench taxonomy (7 codes, GENERATION_v3)

The final taxonomy of `runs/new_pipeline/lcb-models/run-1`, copied byte-identical from
`taxonomy_final.json`. Induced by `new_pipeline` under `GENERATION_v3.md` from 160 traces
(40 tasks × the 9 `models-1` candidates) of the taxonomy pool; nothing hand-authored.

| id | column | name | definition |
|---|---|---|---|
| `SP_01` | general | `incomplete_or_malformed_output_generation` | The agent produces output that is incomplete, truncated, replaced with trivial dummy values, or contains non-code syntax errors, failing to output a fully functional execution unit. |
| `SP_02` | domain | `complexity_bound_exceeded` | The agent designs an algorithm whose asymptotic time or space complexity exceeds the input constraints of the task. |
| `SP_03` | domain | `invalid_dynamic_programming_state_or_transition` | The agent formulates a dynamic programming state space or recurrence transition that fails to cover all valid state combinations, skips required intermediate states, or permits invalid state pairings. |
| `SP_04` | domain | `flawed_mathematical_or_combinatorial_derivation` | The agent applies an incorrect explicit algebraic formula, invalid combinatorial counting property, or flawed mathematical simplification during problem solving. |
| `SP_05` | domain | `simulation_mechanics_and_traversal_state_tracking_defect` | The agent mismodels physical or grid simulation rules, queue/visited state updates during graph or spatial traversal, or tracking structures representing step-by-step movement. |
| `SP_06` | domain | `off_by_one_and_boundary_shift_error` | The agent introduces single-unit calculation offsets, off-by-one loop range bounds, bit mask size mismatches, or incorrect boundary comparison thresholds. |
| `SP_07` | domain | `incomplete_or_overly_restrictive_logic_condition` | The agent uses faulty predicate logic, omits necessary validation checks, or applies overly restrictive filtering conditions that misclassify valid states. |

## How it was reached

| step | result |
|---|---|
| draft (stage 1–6) | 6 codes; baseline gate kappa 0.875, coverage 0.784 — PASS (60 traces) |
| refinement round 1 | 4 keep + 2 edit; gate kappa 0.764, coverage 0.605 — FAIL (coverage floor 0.70) |
| gap test | 50 fresh traces, 29 findings: 22 covered, 7 loose, **0 uncovered**; 0 proposals |
| granularity | 3 codes examined; `off_by_one_or_boundary_condition_error` split into `SP_06` + `SP_07` ("every pair of parts occurs apart"); `flawed_mathematical_or_combinatorial_derivation` kept as one mechanism |

The 6-code draft passed its gate and the refined version did not; the refined-and-split
version was chosen anyway (2026-09-11) to see how it judges, on the reasoning that the gap
test found nothing uncovered and that the coverage drop was measured on 60 traces. The
draft stays at `runs/new_pipeline/lcb-models/run-1/generation/taxonomy_v2.json` if a
comparison is wanted.

## What it does not carry

Only one general code (`SP_01`). Input-parsing / input-format defects are absent because
the observer reported none in its 94 findings: on the full 1,350-trace taxonomy pool, only
6 traces (0.4%) raise inside their input-reading code on the first test, five of them because
the program consumes stdin twice (a duplicated body or a second reading loop), and none of
the six were in the 160-trace generation corpus. Wrong-answer failures caused by silently
misread input were not separately measured.

Rates under this taxonomy are valid only from a judge pass run with it in view; the
generation-corpus findings are grounding, not occurrences.
