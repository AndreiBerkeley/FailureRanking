"""Assemble the curated tree of the `model_ranking` branch from this working repo.

    python3 data/scripts/build_model_ranking_branch.py <worktree-root> [--only section,section] [--swe-traces]

Sections: livecodebench, livecodebench-recovery, hover, hover-models-recovery, terminalbench, swebench,
tau2bench, bfcl, code, code-redo (all, in that order, when --only is not given). SWE-bench's trajectories
carry no licence, so its judge-set traces are written only with --swe-traces; otherwise its source keys are.

The branch is an orphan: a reader sees only what the model-ranking study needs, laid out
per benchmark. This script copies DATA and CODE only; every README.md / methodology.md on
the branch is written by hand in the worktree and is never touched here. Re-running the
script refreshes the data directories it owns (they are removed and rebuilt) and skips
any source that does not exist yet, printing what it skipped.

Layout produced (see the branch README for the reader's view):

    livecodebench/program, livecodebench/tasks
    livecodebench/models/{candidates,splits,taxonomies,traces,taxonomy_generation,judge_traces/{judging-50-1,judging-150}}
    hover/program, hover/tasks
    hover/GEPA_candidates/{candidates,taxonomy,taxonomy_generation,splits,outcomes,judge_traces/{sample-50,judging-50}}
    hover/models/{candidates,taxonomies,splits,outcomes,taxonomy_generation,judge_traces/{judged-50-a,judged-50-b}}
    code/

Trace files are one JSON per trace in the judge's shape ({trace_id, messages, metadata})
with the gold kept in a separate outcomes file beside them, never inside a trace.
"""
import glob, gzip, json, re, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
args = [x for x in sys.argv[1:]]
ONLY = None
if "--only" in args:
    i = args.index("--only"); ONLY = set(args[i + 1].split(",")); del args[i:i + 2]
SWE_TRACES = "--swe-traces" in args          # SWE-bench's trajectories carry no licence: off unless asked
args = [x for x in args if x != "--swe-traces"]
if not args:
    sys.exit(__doc__)
OUT = Path(args[0]).resolve()
skipped = []
WRITTEN = []          # every destination a section wrote; the redaction pass reads these

# Third-party secrets that appear in public source data (an agent printing its environment, a tutorial key)
# are never republished: every written text file is scanned and each match replaced by [REDACTED:<kind>].
SECRET = re.compile(r"(?P<anthropic>sk-ant-[A-Za-z0-9_-]{20,})|(?P<openai>sk-proj-[A-Za-z0-9_-]{20,})|"
                    r"(?P<openrouter>sk-or-v1-[0-9a-f]{20,})|(?P<generic_sk>sk-[A-Za-z0-9]{32,})|"
                    r"(?P<google>AIza[0-9A-Za-z_-]{35})|(?P<github>ghp_[A-Za-z0-9]{36})|"
                    r"(?P<slack>xox[baprs]-[A-Za-z0-9-]{10,})|(?P<aws>AKIA[0-9A-Z]{16})|(?P<huggingface>hf_[A-Za-z0-9]{30,})")
TEXT = (".json", ".jsonl", ".md", ".txt", ".log", ".py")


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
    WRITTEN.append(dst)
    print(f"  {dst.relative_to(OUT)}  <- {src.relative_to(REPO)}")


def copy_file(src, dst):
    src, dst = REPO / src, OUT / dst
    if not src.exists():
        skipped.append(str(src)); return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    WRITTEN.append(dst)


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
    WRITTEN.append(dst)
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
    WRITTEN.append(dst)
    print(f"  {dst.relative_to(OUT)}  <- data/hover/traces/{cap}  ({n} traces)")


def split_tasks(path, key="judged"):
    return set(json.loads((REPO / path).read_text())["portions"][key])


def section_livecodebench():
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


def section_hover():
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
    for t in ("tax-10", "tax-13", "tax-15-pool3"):
        copy_tree(f"data/hover/taxonomies/{t}", f"{G}/taxonomy/{t}")
    copy_tree("data/hover/taxonomies/runs/new_pipeline-pool3-v3-1", f"{G}/taxonomy_generation/run-v3-1",
              exclude=("corpus_*", "fresh_corpus"))
    for s in ("eval-1", "judging-sample-2"):
        copy_tree(f"data/hover/splits/{s}", f"{G}/splits/{s}")
    for c in ("cap-2", "cap-3", "cap-5"):
        copy_file(f"data/hover/outcomes/{c}.jsonl", f"{G}/outcomes/{c}.jsonl")
        copy_file(f"data/hover/outcomes/{c}.provenance.json", f"{G}/outcomes/{c}.provenance.json")
    export_hover_capture("cap-2", f"{G}/judge_traces/sample-50/traces")
    copy_tree("data/hover/mappings/map-5", f"{G}/judge_traces/sample-50/judge")
    # the 2026-09-18 pointjudge (tax-13, Luna readers / Sol decider, success rule in view) with the
    # tax-15-pool3 assignments applied, its recovery pass, and the unrecovered-only derivation
    for j in ("pointjudge-1-tax15", "recovery-2-tax15", "pointjudge-1-tax15-unrecovered"):
        copy_tree(f"runs/new_pipeline/hover/{j}", f"{G}/judge_traces/sample-50/{j}")
    copy_file("runs/new_pipeline/hover/pointjudge-1.log", f"{G}/judge_traces/sample-50/pointjudge-1-tax15/pointjudge-1.log")
    copy_file("runs/new_pipeline/hover/recovery-2.log", f"{G}/judge_traces/sample-50/recovery-2-tax15/recovery-2.log")
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
    for j in ("recovery-1", "pointjudge-3-unrecovered"):        # the recovery pass on set b (2026-09-16) and its unrecovered-only mapping
        copy_tree(f"runs/new_pipeline/hover-models/{j}", f"{M}/judge_traces/judged-50-b/judge/{j}")
    copy_file("runs/new_pipeline/hover-models/recovery-1.log", f"{M}/judge_traces/judged-50-b/judge/recovery-1.log")


def section_code():
    print("code")
    copy_tree("new_pipeline", "code/new_pipeline", exclude=("outcome",))   # new_pipeline/outcome is not part of any result here
    copy_file("GENERATION_v2.md", "code/GENERATION_v2.md")
    copy_file("GENERATION_v3.md", "code/GENERATION_v3.md")
    copy_file("methods/BASELINES.md", "code/BASELINES.md")
    copy_tree("methods/scripts", "code/methods_scripts")
    copy_tree("data/livecodebench/scripts", "code/livecodebench_scripts")
    for f in ("capture_models.py", "hoverlib.py", "append_sp15.py", "draw_judged_50_b.py", "build_tax15_pool3.py", "assign_uncoded_pool3.py"):
        copy_file(f"data/hover/scripts/{f}", f"code/hover_scripts/{f}")
    copy_file("judges/proposed/two-reader-decider.md", "code/pointjudge_design.md")
    copy_file("data/scripts/build_model_ranking_branch.py", "code/build_model_ranking_branch.py")
    copy_file("data/scripts/archive_new_pipeline_run.py", "code/archive_new_pipeline_run.py")


def copy_pool_outcomes(src, dst):
    """A pool's gold sidecar and manifest only, without the trace bodies."""
    src, dst = REPO / src, OUT / dst
    if not src.exists():
        skipped.append(str(src)); return
    fresh(dst); dst.mkdir()
    for f in ("outcomes.json", "pool_manifest.json"):
        shutil.copy2(src / f, dst / f)
    WRITTEN.append(dst)
    print(f"  {dst.relative_to(OUT)}  <- {src.relative_to(REPO)}  (outcomes only)")


def export_view_traces(bench, dst, portion="test"):
    """data/<bench>/traces/view-1 (RedoAdamast's judge views of cap-1) -> one JSON per trace in the branch's
    shape {trace_id, messages, metadata}. The judge saw only the messages; the metadata (candidate, task,
    repeat, cap-1 trace id) is added from the view index for the reader. No gold."""
    src, dst = REPO / f"data/{bench}/traces/view-1", OUT / dst
    if not src.exists():
        skipped.append(str(src)); return
    fresh(dst); dst.mkdir(); n = 0
    for line in open(src / "index.jsonl"):
        r = json.loads(line)
        if r["portion"] != portion:
            continue
        v = json.loads((src / r["file"]).read_text())
        rec = {"trace_id": v["trace_id"], "messages": v["messages"],
               "metadata": {"task_id": r["task_id"], "candidate_id": r["candidate_id"], "repeat": r["repeat"],
                            "benchmark": bench, "capture": "cap-1", "cap1_trace_id": r["cap1_trace_id"]}}
        (dst / f"{v['trace_id']}.json").write_text(json.dumps(rec, indent=1)); n += 1
    WRITTEN.append(dst)
    print(f"  {dst.relative_to(OUT)}  <- data/{bench}/traces/view-1 ({portion}, {n} traces)")


def section_livecodebench_recovery():
    print("livecodebench / models: recovery")
    LM = "livecodebench/models"
    copy_file("data/livecodebench/program/structure.json", "livecodebench/program/structure.json")   # carries the success rule the reader saw
    copy_tree("runs/new_pipeline/lcb-models/recovery-1", f"{LM}/judge_traces/judging-150/judge/recovery-1")


def section_hover_models_recovery():
    print("hover / models: recovery with the success rule in view (set b)")
    copy_tree("runs/new_pipeline/hover-models/recovery-2", "hover/models/judge_traces/judged-50-b/judge/recovery-2")


def section_terminalbench():
    print("terminalbench (shared)")
    copy_file("data/terminalbench/README.md", "terminalbench/README.source.md")
    copy_file("data/terminalbench/program/structure.json", "terminalbench/program/structure.json")
    copy_file("data/terminalbench/program/README.md", "terminalbench/program/README.source.md")
    copy_file("data/terminalbench/tasks/tasks.jsonl", "terminalbench/tasks/tasks.jsonl")
    copy_file("data/terminalbench/tasks/provenance.json", "terminalbench/tasks/provenance.json")
    copy_tree("data/terminalbench/splits/pools-1", "terminalbench/tasks/splits/pools-1")
    print("terminalbench / models")
    T = "terminalbench/models"
    copy_file("data/terminalbench/candidates/sets/terminus2-1.json", f"{T}/candidates/terminus2-1.json")
    copy_file("data/terminalbench/candidates/registry.jsonl", f"{T}/candidates/registry.jsonl")
    copy_tree("data/terminalbench/taxonomies/tax-1", f"{T}/taxonomies/tax-1")
    copy_tree("runs/new_pipeline/terminalbench/run-1", f"{T}/taxonomy_generation/run-1",
              exclude=("corpus_*", "fresh_corpus"))
    copy_pool("runs/new_pipeline/terminalbench/pool_judged20_frontier7", f"{T}/judge_traces/judged-20/traces")
    for j in ("pointjudge-1", "recovery-1", "pointjudge-1-unrecovered"):
        copy_tree(f"runs/new_pipeline/terminalbench/{j}", f"{T}/judge_traces/judged-20/judge/{j}")
    for f in ("pointjudge-1.log", "recovery-1.log"):
        copy_file(f"runs/new_pipeline/terminalbench/{f}", f"{T}/judge_traces/judged-20/judge/{f}")
    copy_pool_outcomes("runs/new_pipeline/terminalbench/pool_eval69_frontier7", f"{T}/outcomes/eval69")


def section_redo(b, cset, traces=True):
    """SWE-bench / tau2-bench / BFCL: RedoAdamast's taxonomy and judge run on our cap-1 (data/<b>/taxonomies/tax-1,
    mappings/map-1) and the recovery pass over them (runs/new_pipeline/<b>/recovery-2)."""
    print(f"{b} (shared)")
    copy_file(f"data/{b}/README.md", f"{b}/README.source.md")
    copy_file(f"data/{b}/program/structure.json", f"{b}/program/structure.json")
    print(f"{b} / models")
    R = f"{b}/models"
    copy_file(f"data/{b}/candidates/sets/{cset}.json", f"{R}/candidates/{cset}.json")
    copy_file(f"data/{b}/candidates/registry.jsonl", f"{R}/candidates/registry.jsonl")
    copy_tree(f"data/{b}/splits/pools-4", f"{R}/splits/pools-4")
    for f in ("cap-1-complete.jsonl", "cap-1-complete.provenance.json"):
        copy_file(f"data/{b}/outcomes/{f}", f"{R}/outcomes/{f}")
    copy_tree(f"data/{b}/taxonomies/tax-1", f"{R}/taxonomies/tax-1", exclude=("calls",))
    J = f"{R}/judge_traces/judged-50"
    if traces:
        export_view_traces(b, f"{J}/traces")
    else:                                 # the trajectories are not republished; the keys rebuild them from the public bucket
        keys = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:data/{b}/traces/cap-1/source_keys.txt"],
                              capture_output=True, text=True, check=True).stdout
        (OUT / J).mkdir(parents=True, exist_ok=True)
        (OUT / J / "source_keys.txt").write_text(keys); WRITTEN.append(OUT / J / "source_keys.txt")
        print(f"  {J}/source_keys.txt  <- git HEAD data/{b}/traces/cap-1/source_keys.txt (traces not republished)")
    copy_file(f"data/{b}/traces/view-1/index.jsonl", f"{J}/view_index.jsonl")
    copy_tree(f"data/{b}/mappings/map-1", f"{J}/judge/map-1", exclude=("calls",))
    recs = ["recovery-2"] + (["recovery-2-patch"] if b == "swebench" else [])
    for r in recs:
        copy_tree(f"runs/new_pipeline/{b}/{r}", f"{J}/judge/{r}")
    copy_file(f"runs/new_pipeline/{b}/recovery-2.log", f"{J}/judge/recovery-2.log")


def section_code_redo():
    print("code: RedoAdamast snapshot, imports and converters")
    copy_tree("data/redo_adamast/code-1", "code/redo_adamast/code-1", exclude=("v3_reference", "INITIAL_GENERATION_PROMPTS.md"))
    copy_file("data/redo_adamast/code-1.provenance.json", "code/redo_adamast/code-1.provenance.json")
    copy_file("data/redo_adamast/README.md", "code/redo_adamast/README.md")
    for f in ("import_redo_adamast.py", "recheck_recovery_output.py"):
        copy_file(f"data/scripts/{f}", f"code/{f}")
    for b in ("terminalbench", "swebench", "tau2bench", "bfcl"):
        copy_tree(f"data/{b}/scripts", f"code/{b}_scripts")


SECTIONS = {
    "livecodebench": section_livecodebench,
    "livecodebench-recovery": section_livecodebench_recovery,
    "hover": section_hover,
    "hover-models-recovery": section_hover_models_recovery,
    "terminalbench": section_terminalbench,
    "swebench": lambda: section_redo("swebench", "mini-v2-1", traces=SWE_TRACES),
    "tau2bench": lambda: section_redo("tau2bench", "banking-aug-1"),
    "bfcl": lambda: section_redo("bfcl", "fc-1"),
    "code": section_code,
    "code-redo": section_code_redo,
}
unknown = (ONLY or set()) - set(SECTIONS)
if unknown:
    sys.exit(f"unknown section(s): {sorted(unknown)}; known: {list(SECTIONS)}")
for name, fn in SECTIONS.items():
    if ONLY is None or name in ONLY:
        fn()


def redact_written():
    hits, files, unreadable = {}, 0, []
    for root in WRITTEN:
        for f in ([root] if root.is_file() else sorted(root.rglob("*"))):
            if not f.is_file() or f.suffix not in TEXT:
                continue
            files += 1
            try:
                t = f.read_text()
            except UnicodeDecodeError:
                unreadable.append(f); continue
            kinds = []
            def sub(m):
                kinds.append(m.lastgroup); return f"[REDACTED:{m.lastgroup}]"
            new = SECRET.sub(sub, t)
            if kinds:
                f.write_text(new); hits[str(f.relative_to(OUT))] = kinds
    print(f"\nredaction: {files} text files scanned, {sum(map(len, hits.values()))} secret-looking strings replaced in {len(hits)} files")
    for k, v in hits.items():
        print(f"  {k}: {', '.join(sorted(set(v)))} ×{len(v)}")
    if unreadable:
        print("  not UTF-8, not scanned:", *[str(u.relative_to(OUT)) for u in unreadable])


redact_written()

if skipped:
    print("\nskipped (source not present yet):")
    for s in skipped:
        print("  ", Path(s).relative_to(REPO))
