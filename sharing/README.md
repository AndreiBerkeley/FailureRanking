# sharing: taxonomies, formulas and results in one place

Four experiments: HoVer with two candidate types, LiveCodeBench, and Terminal-Bench. A candidate is either a
GEPA-optimised prompt set (same model, different prompts) or a model (same program, different model). In every
experiment a judge reads each candidate's traces on a small judged task set and records failure instances
under a taxonomy; a recovery reader then says which instances the program recovered from; formulas turn the
instances into a score; the score's ranking is checked against pass rates on a disjoint, larger
generalization set.

## The four setups

| experiment | candidates | judged tasks | recovery | gen tasks | taxonomy | judge | recovery reader |
|---|---|---:|---|---:|---|---|---|
| GEPA · HoVer | 12 prompt sets | 50 | on all 50 | 500 | `GEPA_Candidates_HoVer_taxonomy.json`: 15 codes, SP_14 and SP_15 hand-authored | readers gpt-5.6-luna ×2, decider gpt-5.6-sol | claude-sonnet-5 |
| Models · HoVer | 9 models | 50 (set b; set a has no recovery pass) | on all 50 | 500 | `Models_HoVer_taxonomy.json`: 15 codes, SP_15 hand-authored | readers gemini-3.6-flash ×2, decider claude-sonnet-5 | claude-sonnet-5 (`recovery-2`) |
| Models · LiveCodeBench | 9 models | 50 (the judged split `judging-50-1`) | on all 150 judged | 755 | `Models_LiveCodeBench_taxonomy.json`: 10 codes | readers gemini-3.6-flash ×2, decider claude-sonnet-5 | claude-sonnet-5 |
| Models · Terminal-Bench 2.0 | 7 models (Terminus 2 agent, leaderboard trajectories) | 20, 19 usable | on all | 69 | `Models_TerminalBench_taxonomy.json`: 10 codes | readers gpt-5.6-luna ×2, decider gpt-5.6-sol | claude-sonnet-5 |

The recovery reader had the program's *success rule* (how the output is scored) in view in all four. The
judges of GEPA·HoVer and Terminal-Bench had it too; the Models·HoVer and LiveCodeBench judges predate it. On
Terminal-Bench one task (`vulnerable-secret`) is dropped for every candidate because two candidates' traces
were refused by the judge's provider. LiveCodeBench was judged on 150 tasks; its main results read the 50-task
split, and every results file adds the full 150 as a supplementary section that enters no mean and no choice of
a best method. The generalization sets are single runs per task (repeat 0), never read by any model.

The traces, judge records and recovery records behind every table are in the benchmark directories at the top
of the branch: `hover/GEPA_candidates/judge_traces/sample-50`, `hover/models/judge_traces/judged-50-b`,
`livecodebench/models/judge_traces/judging-150` (with the 50-task split in `judging-50-1`), and
`terminalbench/models/judge_traces/judged-20`.

## Files

| file | what |
|---|---|
| `best_methods.md` | the best formula without recovery and with it (highest mean tau over the four experiments), every formula's tau beside it, and how far each solve-rate-scaled score is from the actual solve rate |
| `formulas.md` | every formula as numbered steps from the judge's records to the score; the measure (tau-b with ties dropped, resolved pairs, top-1, top-3); the solve-rate distance; how the best method is chosen |
| `results.md` | per experiment: Table 1 on every instance, Table 2 on unrecovered instances plus the recovery-dependent formulas; each formula in both conventions for instances no code fit |
| `compared_scoring.md` | per candidate: 1 − incidence, 1 − unrecovered incidence and 1 − profile risk beside the tasks actually solved (judged and generalization), and the mean absolute distance, with gold-judged vs gold-gen as the reference |
| `first_last_study.md` | the study of scores that read only each trace's first and last failure instance: mode filters pooled across candidates or per candidate, a 75-cell grid of data-estimated weights, a leave-one-experiment-out check, and an entropy-weighted setup |
| `results_ablation.md` | how the numbers move with the tasks: judged-side sweep (k = 10…150, 10 draws), generalization-side resampling (m = 100, 300, full), disjoint judged sets; GEPA·HoVer, Models·HoVer, LiveCodeBench |
| `*_taxonomy.json` | the taxonomy each judge read: codes with definition, when to use / not, consequence, at most 3 evidence quotes; hand-authored codes flagged |
| `*_recovery.md` | what the recovery reader did with the judge's failure instances: verdict counts (unrecovered / corrected / contained), per candidate, per failure mode, instances per trace before and after |
| `pipeline.md` | how a taxonomy is generated; the split rule (floors for judging (20) and generation (15), sizes from N = min(dataset, 1000), when the two share tasks) with the four experiments measured against it; how the recovery pass works |
| `scripts/` | the generators: `trim_taxonomy.py`, `recovery_report.py`, `results_tables.py`, `compared_scoring.py`, `best_methods.py`, `first_last_study.py`, `sampling_tables.py`; every table above is their output over the recorded runs, no model call |

Read `best_methods.md` for the answer and `formulas.md` for what each number means, then `results.md` for the
per-experiment detail. `results_ablation.md` says how much to trust a given number; the recovery reports say
what the unrecovered input contains.
