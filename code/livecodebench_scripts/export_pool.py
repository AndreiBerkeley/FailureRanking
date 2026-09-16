"""Export a scored capture as a judge-view pool for new_pipeline.

    export_pool.py --capture <scored capture> [<scored capture> ...] --out <pool dir>

Writes one <trace_id>.json per ok trace in the shape the pipeline reads
(trace_id, messages, metadata with task_source_id / candidate_index), plus
outcomes.json -- the gold sidecar, used only to compose failure-bearing corpora and
never rendered into a prompt -- and pool_manifest.json. Traces carry no score.
"""
import argparse, json, shutil
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--capture", type=Path, required=True, nargs="+", help="one or more scored captures, same candidate set")
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()

mans = [json.load(open(c / "manifest.json")) for c in a.capture]
man = mans[0]
for m in mans[1:]:
    assert m["candidate_index"] == man["candidate_index"] and m["candidate_set"] == man["candidate_set"], "captures disagree on candidates"
scores = {}
for c in a.capture:
    for line in open(c / "outcomes.jsonl"):
        o = json.loads(line); scores[o["trace_id"]] = o["score"]
a.out.mkdir(parents=True, exist_ok=True)
n = skipped = unscored = 0
for c, m in zip(a.capture, mans):
    for p in sorted((c / "traces").glob("*/*.json")):
        r = json.loads(p.read_text())
        if r.get("status") != "ok": skipped += 1; continue
        if r["trace_id"] not in scores: unscored += 1; continue
        rec = {"trace_id": r["trace_id"], "messages": r["messages"],
               "metadata": {"task_source_id": r["task_id"], "task_id": r["task_id"],
                            "candidate_index": r["candidate_index"], "candidate_id": r["candidate_id"],
                            "benchmark": "livecodebench", "capture": c.name, "repeat": r.get("repeat", 0),
                            "split": f"{m['split']}/{m['portion']}", "solver_model": r["solver_model"],
                            "reasoning": r.get("reasoning"), "difficulty": r["metadata"].get("difficulty"),
                            "platform": r["metadata"].get("platform"), "prompt_variant": r["metadata"].get("prompt_variant")}}
        (a.out / f"{r['trace_id']}.json").write_text(json.dumps(rec, indent=1)); n += 1
(a.out / "outcomes.json").write_text(json.dumps({"scores": scores, "note": "stratification only; never rendered into a prompt"}, indent=1))
(a.out / "pool_manifest.json").write_text(json.dumps({
    "benchmark": "livecodebench", "split": " + ".join(f"{m['split']}/{m['portion']}" for m in mans), "portion": man["portion"], "captures": [c.name for c in a.capture],
    "candidate_set": man["candidate_set"], "candidate_index": man["candidate_index"], "tasks_in_portion": sum(m["tasks"] for m in mans),
    "traces_written": n, "traces_capture_failed": skipped, "traces_unscored": unscored,
    "prompt": man.get("prompt"), "prompt_sha256": man.get("prompt_sha256"), "settings": man.get("settings")}, indent=2))
print(f"wrote {n} traces (+outcomes.json, pool_manifest.json) -> {a.out}; skipped {skipped} failed, {unscored} unscored")
