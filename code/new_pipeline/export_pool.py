#!/usr/bin/env python3
"""Write a benchmark's pool of judge-view traces from data/<benchmark> captures.

    python -m new_pipeline.export_pool --benchmark hover --portion taxonomy --out <dir>

Selects every trace of every capture whose task is in the named pools-1
portion, writes each as <trace_id>.json in the message form the generator and
judge read, and an outcomes sidecar used ONLY to stratify the corpus split.
Refuses to write a trace that still carries an outcome-bearing key.
"""
from __future__ import annotations
import argparse, gzip, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from new_pipeline import goldfree  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True); ap.add_argument("--portion", required=True)
    ap.add_argument("--split", default="pools-1"); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--captures", default=None, help="comma-separated capture ids; default all")
    ap.add_argument("--repeats", default=None, help="comma-separated repeat numbers to keep (default all); e.g. 0 for one run per candidate and task")
    a = ap.parse_args(); keep_reps = {int(x) for x in a.repeats.split(",")} if a.repeats else None
    D = REPO / "data" / a.benchmark; tasks = set(json.loads((D / "splits" / a.split / "split.json").read_text())["portions"][a.portion])
    caps = a.captures.split(",") if a.captures else sorted(p.name for p in (D / "traces").glob("cap-*"))
    a.out.mkdir(parents=True, exist_ok=True); scores, cands, written, skipped, offending, failed, dup, seen, synth = {}, {}, 0, 0, 0, 0, 0, {}, 0
    # Some captures hold stage records but no judge view (ifbench cap-1). The view is a
    # deterministic rendering of the stages, so it is built here with the same converter
    # the runner used for the later captures, from the candidate's own instructions.
    components = {json.loads(l)["candidate_id"]: json.loads(l)["components"] for l in open(D / "candidates" / "registry.jsonl")} if (D / "candidates" / "registry.jsonl").exists() else {}
    build_messages = None
    def synth_view(b):
        nonlocal build_messages
        if build_messages is None:
            sys.path.insert(0, str(REPO / "legacy" / "trials" / "2026-08-25-gepa-cross-benchmark-candidates"))
            from convert_traces_for_adamast import build_messages as _bm; build_messages = _bm
        return {"messages": build_messages(a.benchmark, {"trace": b["stages"], "prediction": b.get("prediction") or {}}, components.get(b["candidate_id"], {}))}
    for cap in caps:
        man = json.loads((D / "traces" / cap / "manifest.json").read_text())
        for cid in man["candidate_ids"]: cands.setdefault(cid, len(cands))
        for l in open(D / "outcomes" / f"{cap}.jsonl"):
            r = json.loads(l); scores[r["trace_id"]] = r["score"]
        for cid, meta in man["bodies"].items():
            with gzip.open(D / "traces" / cap / meta["file"], "rt", encoding="utf-8") as fh:
                for line in fh:
                    b = json.loads(line)
                    if b["task_id"] not in tasks: continue
                    if keep_reps is not None and int(b.get("repeat", 0)) not in keep_reps: continue
                    if b.get("status") == "capture_failed": failed += 1; continue   # the provider returned nothing: no trace to read
                    if b["trace_id"] in seen:   # ifbench/hotpotqa ids are sha(bench|candidate|task|repeat): a task re-run in a later capture repeats the id
                        dup += 1; continue      # first capture in sorted order wins; the manifest records how many were skipped
                    seen[b["trace_id"]] = cap
                    jv = b.get("judge_view")
                    if (not jv or not jv.get("messages")) and b.get("stages") and a.benchmark in ("ifbench", "hotpotqa"):
                        jv = synth_view(b); synth += 1
                    if not jv or not jv.get("messages"): skipped += 1; continue
                    rec = {"trace_id": b["trace_id"], "messages": jv["messages"],
                           "metadata": {"task_source_id": b["task_id"], "task_id": b["task_id"], "candidate_index": cands[cid], "candidate_id": cid,
                                        "benchmark": a.benchmark, "capture": cap, "repeat": b["repeat"], "split": f"{a.split}/{a.portion}"}}
                    if goldfree.offending_keys(rec): offending += 1; continue
                    (a.out / f"{b['trace_id']}.json").write_text(json.dumps(rec, ensure_ascii=False)); written += 1
    if offending: raise SystemExit(f"{offending} traces carried an outcome-bearing key and were not written")
    (a.out / "outcomes.json").write_text(json.dumps({"scores": {t: s for t, s in scores.items() if (a.out / f"{t}.json").exists()}, "note": "stratification only; never rendered into a prompt"}))
    (a.out / "pool_manifest.json").write_text(json.dumps({"benchmark": a.benchmark, "split": a.split, "portion": a.portion, "captures": caps, "tasks_in_portion": len(tasks),
                                                          "traces_written": written, "traces_without_judge_view": skipped, "traces_capture_failed": failed, "traces_duplicate_id_skipped": dup, "repeats_kept": sorted(keep_reps) if keep_reps else "all", "judge_views_synthesised_from_stages": synth, "candidate_index": cands}, indent=1))
    print(f"{a.benchmark} {a.split}/{a.portion}: {written} traces written to {a.out} from {caps}; {skipped} skipped (no judge view); {failed} capture failures left out; {dup} duplicate trace ids skipped; {synth} judge views built from stage records")


if __name__ == "__main__":
    main()
