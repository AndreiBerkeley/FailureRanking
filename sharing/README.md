# sharing — taxonomies, formulas and results in one place

Four experiments, two benchmarks with two candidate types on HoVer, plus Terminal-Bench. A
candidate is either a GEPA-optimised prompt set (same model, different prompts) or a model
(same prompts, different model). In every experiment a judge reads each candidate's traces on
a small judged task set and records failure points under a taxonomy; a recovery reader then
says which points the program recovered from; formulas turn the points into a score; the
score's ranking is checked against pass rates on a disjoint, larger generalization set.

## The four setups

| experiment | candidates | judged tasks | recovery | gen tasks | taxonomy | judge | recovery reader |
|---|---|---:|---|---:|---|---|---|
| GEPA · HoVer | 12 prompt sets | 50 | on all 50 | 500 | `GEPA_Candidates_HoVer_taxonomy.json` — 15 codes, SP_14 and SP_15 hand-authored | readers gpt-5.6-luna ×2, decider gpt-5.6-sol | claude-sonnet-5 |
| Models · HoVer | 9 models | 100 (two disjoint sets of 50, a and b) | on set b only | 500 | `Models_HoVer_taxonomy.json` — 15 codes, SP_15 hand-authored | readers gemini-3.6-flash ×2, decider claude-sonnet-5 | claude-sonnet-5, before the success rule was added to its prompt |
| Models · LiveCodeBench | 9 models | 150 | none | 755 | `Models_LiveCodeBench_taxonomy.json` — 10 codes | readers gemini-3.6-flash ×2, decider claude-sonnet-5 | — |
| Models · Terminal-Bench 2.0 | 7 models (Terminus 2 agent, leaderboard trajectories) | 20, 19 usable | on all | 69 | `Models_TerminalBench_taxonomy.json` — 10 codes | readers gpt-5.6-luna ×2, decider gpt-5.6-sol | claude-sonnet-5 |

Judge and recovery on GEPA·HoVer and Terminal-Bench had the program's *success rule* in view
(how the output is scored); the Models·HoVer and LiveCodeBench passes predate it. On
Terminal-Bench one task (`vulnerable-secret`) is dropped for every candidate because two
candidates' traces were refused by the judge's provider. The generalization sets are single
runs per task (repeat 0), never read by any model.

## Files

| file | what |
|---|---|
| `*_taxonomy.json` | the taxonomy each judge read: codes with definition, when to use / not, consequence, at most 3 evidence quotes; hand-authored codes flagged |
| `*_recovery.md` | what the recovery reader did with the judge's points: verdict counts, per candidate, per failure mode, points per trace before and after |
| `formulas.md` | the formulas (gold, the nine baselines, the three recovery-dependent ones), the two inputs (all points / unrecovered only), and the measure (tau-b with ties dropped, resolved pairs, top-1, top-3) |
| `results.md` | per experiment with recovery: Table 1 on every point, Table 2 on unrecovered points plus the recovery-dependent formulas; each formula in both conventions for points no code fit |
| `compared_scoring.md` | does the score read as a solve rate: 1 − unrecovered incidence and 1 − profile risk per candidate beside the tasks actually solved (judged and generalization), and the average absolute distance, with gold-judged vs gold-gen as the reference |
| `results_ablation.md` | how the numbers move with the tasks: judged-side sweep (k = 10…150, 10 draws), generalization-side resampling (m = 100, 300, full), disjoint judged sets — GEPA·HoVer, Models·HoVer, LiveCodeBench |
| `scripts/` | the generators: `trim_taxonomy.py`, `recovery_report.py`, `results_tables.py`, `compared_scoring.py`, `sampling_tables.py`; every table above is their output over the recorded runs, no model call |

Read `formulas.md` first, then `results.md`; `results_ablation.md` says how much to trust a
given number; the recovery reports say what the unrecovered input actually contains.
