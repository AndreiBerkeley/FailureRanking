"""Assemble the curated tree of the `model_ranking` branch from this working repo.

    python3 data/scripts/build_model_ranking_branch.py <worktree-root>

The branch is an orphan: a reader sees only what the model-ranking study needs, laid out
per benchmark. This script copies DATA and CODE only; every README.md / methodology.md on
the branch is written by hand in the worktree and is never touched here. Re-running the
script refreshes the data directories it owns (they are removed and rebuilt) and skips
any source that does not exist yet, printing what it skipped.

Layout produced (see the branch README for the reader's view):

    livecodebench/program, livecodebench/tasks
    livecodebench/models/{candidates,splits,taxonomies,traces,taxonomy_generation,judge_traces/{judging-50-1,judging-150}}
    hover/program, hover/tasks
    hover/GEPA_candidates/{candidates,taxonomy,splits,outcomes,judge_traces/{sample-50,judging-50}}
    hover/models/{candidates,taxonomies,splits,outcomes,taxonomy_generation,judge_traces/{judged-50-a,judged-50-b}}
    code/

Trace files are one JSON per trace in the judge's shape ({trace_id, messages, metadata})
with the gold kept in a separate outcomes file beside them, never inside a trace.
"""
import glob, gzip, json, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if len(sys.argv) < 2:
    sys.exit(__doc__)
OUT = Path(sys.argv[1]).resolve()
skipped = []


def fresh(dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)


def copy_tree(src, dst, exclude=()):
    src, dst = REPO / src, OUT / dst
    if not src.exists():
        skipped.append(str(src)); return
    fresh(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store", *exclude))
    print(f"  {dst.relative_to(OUT)}  <- {src.relative_to(REPO)}")


def copy_file(src, dst):
    src, dst = REPO / src, OUT / dst
    if not src.exists():
        skipped.append(str(src)); return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_pool(src, dst, task_ids=None):
    """A judge pool (one JSON per trace + outcomes.json + pool_manifest.json), optionally
    restricted to the traces of the named tasks; the outcomes sidecar is restricted too."""
    src, dst = REPO / src, OUT / dst
    if not src.exists():
        skipped.append(str(src)); return
    fresh(dst); dst.mkdir()
    kept = set(); n = 0
    for p in sorted(src.glob("*.json")):
        if p.name in ("outcomes.json", "pool_manifest.json"):
            continue
        if task_ids is not None:
            tid = json.loads(p.read_text())["metadata"]["task_source_id"]
            if tid not in task_ids:
                continue
        shutil.copy2(p, dst / p.name); kept.add(p.stem); n += 1
    out = json.loads((src / "outcomes.json").read_text())
    out["scores"] = {k: v for k, v in out["scores"].items() if k in kept}
    (dst / "outcomes.json").write_text(json.dumps(out, indent=1))
    man = json.loads((src / "pool_manifest.json").read_text())
    if task_ids is not None:
        man["restricted_to_tasks"] = sorted(task_ids); man["traces_written"] = n
    (dst / "pool_manifest.json").write_text(json.dumps(man, indent=2))
    print(f"  {dst.relative_to(OUT)}  <- {src.relative_to(REPO)}  ({n} traces)")


def export_hover_capture(cap, dst, trace_ids=None):
    """cap-N bodies (gzipped jsonl per candidate, judge_view inside) -> one JSON per trace
    in the pool shape. Only the outcome-blind judge_view is exported; the run record with
    the prediction stays in the main repo."""
    src, dst = REPO / "data/hover/traces" / cap, OUT / dst
    if not src.exists():
        skipped.append(str(src)); return
    fresh(dst); dst.mkdir()
    n = 0
    for b in sorted((src / "bodies").glob("*.jsonl.gz")):
        with gzip.open(b, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                if trace_ids is not None and r["trace_id"] not in trace_ids:
                    continue
                jv = r["judge_view"]
                rec = {"trace_id": r["trace_id"], "messages": jv["messages"],
                       "metadata": {**jv["metadata"], "task_id": r["task_id"], "candidate_id": r["candidate_id"],
                                    "benchmark": "hover", "capture": cap, "repeat": r["repeat"], "status": r["status"]}}
                rec["metadata"].pop("origin", None)
                (dst / f"{r['trace_id']}.json").write_text(json.dumps(rec, indent=1)); n += 1
    shutil.copy2(src / "manifest.json", dst / "capture_manifest.json")
    print(f"  {dst.relative_to(OUT)}  <- data/hover/traces/{cap}  ({n} traces)")


def split_tasks(path, key="judged"):
    return set(json.loads((REPO / path).read_text())["portions"][key])


print("livecodebench (shared)")
copy_file("data/livecodebench/tasks/tasks.jsonl", "livecodebench/tasks/tasks.jsonl")
copy_file("data/livecodebench/tasks/README.md", "livecodebench/tasks/README.source.md")
copy_tree("data/livecodebench/splits/pools-1", "livecodebench/tasks/splits/pools-1")
copy_file("data/livecodebench/evaluator/code_generation_lite.py", "livecodebench/tasks/code_generation_lite.py")
copy_file("data/livecodebench/program/prompt.md", "livecodebench/program/prompt.md")
copy_file("data/livecodebench/program/structure.json", "livecodebench/program/structure.json")

print("livecodebench / models")
LM = "livecodebench/models"
copy_file("data/livecodebench/candidates/sets/models-1.json", f"{LM}/candidates/models-1.json")
for s_ in ("judging-50-1", "judging-100-1"):
    copy_tree(f"data/livecodebench/splits/{s_}", f"{LM}/splits/{s_}")
for t in ("tax-1", "tax-2"):
    copy_tree(f"data/livecodebench/taxonomies/{t}", f"{LM}/taxonomies/{t}")
copy_pool("runs/new_pipeline/lcb-models/pool_taxonomy", f"{LM}/traces/taxonomy_pool")
copy_pool("runs/new_pipeline/lcb-models/pool_generalization", f"{LM}/traces/generalization_pool")
copy_tree("runs/new_pipeline/lcb-models/run-1", f"{LM}/taxonomy_generation/run-1",
          exclude=("corpus_*", "fresh_corpus"))
j50 = split_tasks("data/livecodebench/splits/judging-50-1/split.json", key="judging")
copy_pool("runs/new_pipeline/lcb-models/pool_judging150", f"{LM}/judge_traces/judging-150/traces")
copy_pool("runs/new_pipeline/lcb-models/pool_judging150", f"{LM}/judge_traces/judging-50-1/traces", task_ids=j50)
for j in ("pointjudge-1", "pointjudge-1-tax2"):
    copy_tree(f"runs/new_pipeline/lcb-models/{j}", f"{LM}/judge_traces/judging-50-1/judge/{j}")
copy_file("runs/new_pipeline/lcb-models/pointjudge-1.log", f"{LM}/judge_traces/judging-50-1/judge/pointjudge-1.log")
copy_tree("runs/new_pipeline/lcb-models/pointjudge-2", f"{LM}/judge_traces/judging-150/judge/pointjudge-2")
copy_file("runs/new_pipeline/lcb-models/pointjudge-2.log", f"{LM}/judge_traces/judging-150/judge/pointjudge-2.log")

print("hover (shared)")
copy_file("data/hover/program/structure.json", "hover/program/structure.json")
copy_file("data/hover/program/README.md", "hover/program/README.source.md")
copy_file("data/hover/tasks/tasks.jsonl", "hover/tasks/tasks.jsonl")
copy_file("data/hover/tasks/README.md", "hover/tasks/README.source.md")
copy_tree("data/hover/splits/pools-1", "hover/tasks/splits/pools-1")

print("hover / GEPA_candidates")
G = "hover/GEPA_candidates"
copy_file("data/hover/candidates/sets/pool-3.json", f"{G}/candidates/pool-3.json")
ids = set(json.loads((REPO / "data/hover/candidates/sets/pool-3.json").read_text())["candidate_ids"])
rows = [l for l in open(REPO / "data/hover/candidates/registry.jsonl") if json.loads(l)["candidate_id"] in ids]
(OUT / G / "candidates").mkdir(parents=True, exist_ok=True)
(OUT / G / "candidates/registry.jsonl").write_text("".join(rows))
copy_tree("data/hover/taxonomies/tax-10", f"{G}/taxonomy/tax-10")
for s in ("eval-1", "judging-sample-2"):
    copy_tree(f"data/hover/splits/{s}", f"{G}/splits/{s}")
for c in ("cap-2", "cap-3", "cap-5"):
    copy_file(f"data/hover/outcomes/{c}.jsonl", f"{G}/outcomes/{c}.jsonl")
    copy_file(f"data/hover/outcomes/{c}.provenance.json", f"{G}/outcomes/{c}.provenance.json")
export_hover_capture("cap-2", f"{G}/judge_traces/sample-50/traces")
copy_tree("data/hover/mappings/map-5", f"{G}/judge_traces/sample-50/judge")
map6_ids = {json.loads(l)["trace_id"] for l in open(REPO / "data/hover/mappings/map-6/mapping.jsonl")}
export_hover_capture("cap-5", f"{G}/judge_traces/judging-50/traces", trace_ids=map6_ids)
copy_tree("data/hover/mappings/map-6", f"{G}/judge_traces/judging-50/judge")

print("hover / models")
M = "hover/models"
copy_file("data/hover/candidates/sets/models-1.json", f"{M}/candidates/models-1.json")
for t in ("tax-14", "tax-15"):
    copy_tree(f"data/hover/taxonomies/{t}", f"{M}/taxonomies/{t}")
for s in ("models-1", "models-1-judged-50", "models-1-judged-50-b"):
    copy_tree(f"data/hover/splits/{s}", f"{M}/splits/{s}")
for c in ("cap-7", "cap-8"):
    copy_file(f"data/hover/outcomes/{c}.jsonl", f"{M}/outcomes/{c}.jsonl")
    copy_file(f"data/hover/outcomes/{c}.provenance.json", f"{M}/outcomes/{c}.provenance.json")
copy_tree("data/hover/taxonomies/runs/new_pipeline-models-1", f"{M}/taxonomy_generation/run-1",
          exclude=("corpus_*", "fresh_corpus"))
a, b = split_tasks("data/hover/splits/models-1-judged-50/split.json"), split_tasks("data/hover/splits/models-1-judged-50-b/split.json")
copy_pool("runs/new_pipeline/hover-models/pool_judging", f"{M}/judge_traces/judged-50-a/traces", task_ids=a)
copy_pool("runs/new_pipeline/hover-models/pool_judging", f"{M}/judge_traces/judged-50-b/traces", task_ids=b)
for j in ("pointjudge-1", "pointjudge-1-sp15"):
    copy_tree(f"runs/new_pipeline/hover-models/{j}", f"{M}/judge_traces/judged-50-a/judge/{j}")
copy_file("runs/new_pipeline/hover-models/pointjudge-1.log", f"{M}/judge_traces/judged-50-a/judge/pointjudge-1.log")
copy_tree("runs/new_pipeline/hover-models/pointjudge-3", f"{M}/judge_traces/judged-50-b/judge/pointjudge-3")
copy_file("runs/new_pipeline/hover-models/pointjudge-3.log", f"{M}/judge_traces/judged-50-b/judge/pointjudge-3.log")

print("code")
copy_tree("new_pipeline", "code/new_pipeline")
copy_file("GENERATION_v2.md", "code/GENERATION_v2.md")
copy_file("GENERATION_v3.md", "code/GENERATION_v3.md")
copy_file("methods/BASELINES.md", "code/BASELINES.md")
copy_tree("methods/scripts", "code/methods_scripts")
copy_tree("data/livecodebench/scripts", "code/livecodebench_scripts")
for f in ("capture_models.py", "hoverlib.py", "append_sp15.py", "draw_judged_50_b.py"):
    copy_file(f"data/hover/scripts/{f}", f"code/hover_scripts/{f}")
copy_file("judges/proposed/two-reader-decider.md", "code/pointjudge_design.md")
copy_file("data/scripts/build_model_ranking_branch.py", "code/build_model_ranking_branch.py")

if skipped:
    print("\nskipped (source not present yet):")
    for s in skipped:
        print("  ", Path(s).relative_to(REPO))
