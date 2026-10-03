# tax-1 — 10 failure modes for the terminalbench program

Generated on 2026-09-18 by `new_pipeline` from the taxonomy pool `runs/new_pipeline/terminalbench/pool_taxonomy_frontier7`: 4 general
and 6 domain codes. The draft came from stages 1–6 of `GENERATION_v3.md` on
64 traces over 16 tasks; one refinement round
rewrote it against the judge's reading of 64 traces on 16 other tasks;
the interannotation gate measured draft and result on 60 traces of 15 further tasks
with four readers and the open reader; the gap test read 20 fresh traces. No outcome
was in view at any stage; outcomes were used only to compose the corpora.

Refinement verdicts: {"keep": 1, "edit": 4, "retire": 1}. Granularity: {"examined": 5, "left_alone": {}}.
Gap test: 45 findings, verdicts {"covered": 42, "stretch": 3}, fitness {"median": 90, "min": 40, "max": 95, "below_good": 3, "below_loose": 3}.

Under `GENERATION_v3.md`: codes the blind reader corroborated under 0.30 at the final gate are retired (R1_006); gap-test findings no code fits well become proposals and survivors are admitted (this run: {"proposed": 1, "surviving_stage6": 1, "too_few": 0}). No hand codes.

| gate | codes | pooled kappa | coverage | traces judged | result |
|---|---:|---:|---:|---:|---|
| baseline | 6 | 0.682 | 0.945 | 55 | fail |
| round_1 | 6 | 0.634 | 0.897 | 60 | fail |

The full run record, with every prompt, raw model output, judge record and gate file, is in
`../runs/new_pipeline-pools1-v3-1/`. Ids are the `SP_` namespace assigned when the granularity splits were applied,
with the refinement round's `R1_` ids and the draft's ids recorded in `taxonomy.json` provenance.

| id | column | name | definition |
|---|---|---|---|
| `SP_01` | general | output_placed_in_reasoning_block | The agent emits its structured response or command payload inside the internal reasoning block instead of providing it in the designated output turn or payload field. |
| `SP_02` | general | missing_required_schema_field | The agent outputs structured JSON in the correct output location, but omits mandatory schema fields required by the harness protocol (such as 'keystrokes' or 'plan'). |
| `SP_03` | general | malformed_output_syntax_or_formatting | The agent generates output that violates JSON syntax rules or field-level string formatting constraints, such as unescaped line breaks, corrupted JSON structures, or missing required trailing newlines in command strings. |
| `SP_04` | general | invalid_command_formatting_or_syntax | The agent constructs shell commands or inline script arguments with malformed syntax, incorrect escape sequences, invalid regex patterns, or unescaped shell expansion characters, causing immediate shell parse or executio |
| `SP_05` | domain | incorrect_api_parameter_or_interface_usage | The agent invokes a library function, CLI tool, or package API using invalid, unsupported, deprecated, or version-mismatched argument names, positional parameters, or configuration structures. |
| `SP_06` | domain | flawed_numerical_and_mathematical_algorithms | The agent implements mathematical derivations, numerical solvers, or array algorithms that violate mathematical principles, numerical stability requirements, or algorithmic invariants. |
| `SP_07` | domain | incorrect_domain_rules_and_constraints | The agent fails to enforce domain-specific constraints, boundary conditions, or factual logic rules required by the problem domain. |
| `SP_08` | domain | framework_and_compiler_execution_logic_errors | The agent uses constructs or operations that violate execution environment requirements, such as breaking framework gradient tracking or creating inconsistent types across branches for JIT compilers. |
| `SP_09` | domain | incorrect_environment_or_process_state_inference | The agent draws invalid conclusions about process execution states, terminal interactive prompts, system hardware architectures, path resolutions, file contents, or data values visible in the execution trace. |
| `SP_10` | domain | missing_required_header_or_import_declaration | Source code is written or modified using functions, types, or symbols without including or importing the required header files or module declarations. |
