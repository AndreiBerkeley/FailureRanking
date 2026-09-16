# code — the instruments, as run

Snapshots of the code that produced everything on this branch, copied from the working
repository without modification. Paths inside the scripts refer to that repository's layout
(`data/<benchmark>/…`, `runs/new_pipeline/…`), not to this branch's; the mapping between
the two is in `build_model_ranking_branch.py`, which assembled this tree.

| path | what it is |
|---|---|
| `new_pipeline/generation/` | taxonomy generation stages 1–6 and the gap-test proposal step |
| `new_pipeline/refine.py`, `gate.py`, `run.py` | refinement round, interannotation gate, the driver |
| `new_pipeline/judge/` | the panel + open-reader judge (hover GEPA_candidates mappings) |
| `new_pipeline/pointjudge/` | the two-reader + decider failure-point judge (models-1 mappings) |
| `GENERATION_v2.md`, `GENERATION_v3.md` | the prompt documents; every LLM prompt is a fenced block read from these at import |
| `pointjudge_design.md` | the judge's design note: the failure-point unit, the passes, the decider |
| `livecodebench_scripts/` | `capture.py` (capture + score), `export_pool.py`, `lcb.py`, the split builders, `build_tax2.py`, `assign_uncovered.py` |
| `hover_scripts/` | the models-1 capture, the hover scorer, `append_sp15.py`, the set-b draw |
| `BASELINES.md`, `methods_scripts/run_baselines.py` | the eleven parameter-free methods and the script that computes every results table |

Model calls go through OpenRouter (`OPENROUTER_API_KEY`) or Gemini direct (`GEMINI_API_KEY`);
no key is stored anywhere on this branch. Python 3.12+; the livecodebench scorer needs the
upstream LiveCodeBench runner in a venv with numpy (see `livecodebench/README.md`).
