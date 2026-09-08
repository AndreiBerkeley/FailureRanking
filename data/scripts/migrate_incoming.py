#!/usr/bin/env python3
"""Turn a finished pools-1 capture run in data/<benchmark>/traces/_incoming/ into
a numbered capture with outcomes, manifest, provenance and README.

    python3 data/scripts/migrate_incoming.py --benchmark hover    --portion judging  --capture cap-5
    python3 data/scripts/migrate_incoming.py --benchmark ifbench  --portion taxonomy --capture cap-3

HoVer runs (capture_pool.py output) go through hoverlib.migrate_capture; the
gepa-artifact runs (capture_artifact_pool.py shards, schema 2) are converted
here. Every check the other migrations make is made: completeness against the
fills list, candidate identity by hash, no gold in bodies, scores equal the
recorded ones. Refuses to overwrite an existing capture; on any failure the
partially written capture directory is removed.
"""
from __future__ import annotations
import argparse, datetime, gzip, hashlib, json, shutil, sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "data" / "hover" / "scripts"))
TODAY = datetime.date.today().isoformat()
SCRIPT = "data/scripts/migrate_incoming.py"
GOLD_KEY_PATTERNS = ("gold", "supporting", "required_titles", "outcome", "score"); GOLD_KEY_EXACT = {"label"}

def jload(p): return json.load(open(p))
def jdump(o, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f: json.dump(o, f, indent=2, sort_keys=True, ensure_ascii=False); f.write("\n")
def jsonl(p): return [json.loads(l) for l in open(p) if l.strip()]
def jsonl_write(rows, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for r in rows: f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
def sha_b(b): return hashlib.sha256(b).hexdigest()
def sha_f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()
def scan(o, path=""):
    hits = []
    if isinstance(o, dict):
        for k, v in o.items():
            kl = str(k).lower()
            if kl in GOLD_KEY_EXACT or any(p in kl for p in GOLD_KEY_PATTERNS): hits.append(f"{path}/{k}")
            hits += scan(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): hits += scan(v, f"{path}[{i}]")
    return hits
def prov(pid, kind, b, derives, counts, checks, extra=None):
    d = {"id": pid, "kind": kind, "benchmark": b, "created": TODAY, "derives_from": derives,
         "produced_by": {"script": SCRIPT, "command": f"python3 {SCRIPT} --benchmark {b}"}, "counts": counts, "checks": checks}
    if extra: d.update(extra)
    return d

def outcomes_readme(b, metric):
    D = REPO / "data" / b
    rows = "\n".join(f"| `{p.stem}` | {sum(1 for _ in open(p))} |" for p in sorted((D / "outcomes").glob("*.jsonl")))
    (D / "outcomes" / "README.md").write_text(f"""# outcomes — gold scores per run

One file per capture, one row per trace: `candidate_id`, `task_id`, `repeat`,
`trace_id`, `score`. {metric} Each file has a `.provenance.json` beside it.

Gold-bearing by construction. A scoring path that claims to be free of gold must
not read this directory.

| file | records |
|---|---:|
{rows}
""")

def hover(portion, cap):
    import hoverlib as H
    D = REPO / "data" / "hover"; src = D / "traces" / "_incoming" / f"pools-1-{portion}"
    fills = jload(D / "splits" / "pools-1" / "fills.json"); ids = set(fills["portions"][portion])
    reg = {r["task_id"]: r for r in jsonl(D / "tasks" / "tasks.jsonl")}
    rec = {t: {"label": r["label"], "source_index": r["source"]["source_index"], "claim_sha256": r["source"]["claim_sha256"]} for t, r in reg.items()}
    _, by_alias = H.load_registry()
    old = jload(src / "outcomes.json"); model = old.get("task_model", "gemini/gemini-3.1-flash-lite")
    captured_on = datetime.date.fromtimestamp((src / "outcomes.json").stat().st_mtime).isoformat()
    runner_prov = {"runner": "data/hover/scripts/capture_pool.py", "command": f"capture_pool.py --split {portion} --repeats 1 --emit-corpus --task-model {model}",
                   "task_model": model, "route": "openrouter" if model.startswith("openrouter/") else "gemini-direct", "repeats": 1, "captured_on": captured_on}
    r = H.migrate_capture(src=src, capture_id=cap, split_id="pools-1", portions=[portion], allowed_tasks=ids, rec=rec, by_alias=by_alias,
                          expected_tasks=len(ids), captured_on=captured_on, derives_from=[f"data/hover/traces/_incoming/pools-1-{portion}", "data/hover/splits/pools-1/fills.json"],
                          script=SCRIPT, description=f"pool-3 on the pools-1 {portion} fill, one run each", runner_prov=runner_prov, solver_model=model)
    # every gold title in the registry must match what the runner recorded (dedup)
    for t, titles in r["gold_by_task"].items(): assert sorted(set(titles)) == reg[t]["gold"]["supporting_titles"], t
    n = len(r["index_rows"])
    H.write_capture_readme(cap, f"pool-3 on the pools-1 {portion} fill, one run each", f"""12 candidates (set `pool-3`) × {len(ids)} tasks (split `pools-1`, portion `{portion}`, the
tasks that still lacked traces) × 1 repeat = {n:,} traces. Solver `{model}`
({runner_prov['route']} route). Captured {captured_on} by `data/hover/scripts/capture_pool.py`;
turned into this capture on {TODAY}, re-keyed to the registries and verified by hash.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what was expected, what is present, audit results |
| `index.jsonl` | one row per trace: ids, status, call count, cost, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces, one candidate per file, one trace per line |
| `program_states/<candidate_id>.json` | the DSPy program state that ran |

Bodies hold the full run record and the outcome-blind `judge_view`. No gold is
here; scores are in `../../outcomes/{cap}.jsonl`. Together with the earlier
captures this completes the `{portion}` pool of `pools-1`.
""")
    H.write_outcomes(cap, r["outcome_rows"], [f"data/hover/traces/{cap}", "data/hover/tasks/tasks.jsonl"], SCRIPT)
    H.write_outcomes_readme()
    return n, dict(r["status_counter"])

def artifact(b, portion, cap):
    D = REPO / "data" / b; src = D / "traces" / "_incoming" / f"pools-1-{portion}"
    fills = jload(D / "splits" / "pools-1" / "fills.json"); ids = set(fills["portions"][portion])
    reg = {r["candidate_id"]: r for r in jsonl(D / "candidates" / "registry.jsonl")}
    cfg = jload(src / "run_config.json"); model = cfg["task_model"]
    shards = sorted((src / "records").glob("cand*_repeat*.json")); assert len(shards) == 12 * cfg["repeats"], f"{len(shards)} shards"
    d = D / "traces" / cap; (d / "bodies").mkdir(parents=True)
    index_rows, outs, meta, statuses, seen = [], [], {}, Counter(), set()
    for sh in shards:
        s = jload(sh); cid = s["candidate_id"]; assert cid in reg and cid == "cnd-" + sha_b(json.dumps(reg[cid]["components"], sort_keys=True).encode())[:12]
        assert s["task_count"] == len(s["records"]) == len(ids), f"{sh.name}: {len(s['records'])} records"
        rows = []
        for r in s["records"]:
            tid = r["task_id"]; assert tid in ids, f"{tid} outside the fill"
            key = (cid, tid, s["repeat"]); assert key not in seen; seen.add(key)
            body = {"trace_id": r["trace_id"], "benchmark": b, "capture": cap, "candidate_id": cid, "task_id": tid, "repeat": s["repeat"],
                    "status": "capture_failed" if r.get("capture_failed") else "parse_failed" if r.get("parse_failed") else "ok",
                    "capture_failed": r.get("capture_failed"), "solver": {"models": [model], "n_stages": len(r["trace"])},
                    "input": {("prompt" if b == "ifbench" else "question"): (r["trace"][0]["inputs"].get("query" if b == "ifbench" else "question") if r["trace"] else None)},
                    "prediction": r["prediction"], "stages": r["trace"], "judge_view": {"messages": r["judge_view"]["messages"], "metadata": {"candidate_id": cid, "task_id": tid, "repeat": s["repeat"]}},
                    "legacy": {"candidate_index": s["candidate_idx"], "shard": str(sh.relative_to(REPO))}}
            assert not scan(body), f"gold key in {r['trace_id']}"
            statuses[body["status"]] += 1; rows.append(body)
            outs.append({"candidate_id": cid, "task_id": tid, "repeat": s["repeat"], "trace_id": r["trace_id"], "score": float(r["score"]), "capture": cap,
                         **({"capture_failed": True} if r.get("capture_failed") else {})})
        rows.sort(key=lambda x: (x["task_id"], x["repeat"])); out = d / "bodies" / f"{cid}.jsonl.gz"
        with gzip.open(out, "wt", compresslevel=6, encoding="utf-8") as f:
            for x in rows:
                line = json.dumps(x, sort_keys=True, ensure_ascii=False); f.write(line + "\n")
                index_rows.append({"trace_id": x["trace_id"], "candidate_id": cid, "task_id": x["task_id"], "repeat": x["repeat"], "status": x["status"], "body_sha256": sha_b(line.encode())})
        meta[cid] = {"file": f"bodies/{cid}.jsonl.gz", "rows": len(rows), "sha256": sha_f(out)}
    assert len(index_rows) == 12 * len(ids) * cfg["repeats"]
    index_rows.sort(key=lambda r: (r["candidate_id"], r["task_id"], r["repeat"])); jsonl_write(index_rows, d / "index.jsonl")
    usage = jload(src / "usage.json") if (src / "usage.json").exists() else None
    captured_on = datetime.date.fromtimestamp(shards[-1].stat().st_mtime).isoformat()
    route = "openrouter" if model.startswith("openrouter/") else "gemini-direct"
    audits = {"candidate_task_repeat_unique": True, "no_gold_keys_in_bodies": True, "tasks_within_fill": True, "candidate_hashes_match_registry": True, "complete_against_fill": True}
    man = {"capture_id": cap, "benchmark": b, "description": f"pool-1 on the pools-1 {portion} fill, one run each", "candidate_set": "pool-1", "candidate_ids": sorted(meta),
           "split": "pools-1", "portions": [portion], "task_count": len(ids), "repeats": list(range(cfg["repeats"])), "solver": {"model": model, "route": route, "max_tokens": 4096},
           "program": cfg.get("candidates_from"), "runner": {"script": "data/scripts/capture_artifact_pool.py", "config": cfg}, "captured_on": captured_on,
           "expected_traces": 12 * len(ids) * cfg["repeats"], "present_traces": len(index_rows), "status_counts": dict(statuses), "bodies": meta,
           "usage": usage.get("task") if usage else None, "judge_view": "outcome-blind message list built by the runner from the stage records", "audits": audits,
           "derives_from": [str(src.relative_to(REPO)), f"data/{b}/splits/pools-1/fills.json"]}
    jdump(man, d / "manifest.json"); jdump(prov(cap, "trace capture", b, man["derives_from"], {"traces": len(index_rows), "candidates": 12, "tasks": len(ids)}, audits), d / "provenance.json")
    (d / "README.md").write_text(f"""# {cap} — pool-1 on the pools-1 {portion} fill, one run each

12 candidates × {len(ids)} tasks (split `pools-1`, portion `{portion}`, the tasks that
still lacked traces) × 1 repeat = {len(index_rows):,} traces. Solver `{model}` ({route}
route). Captured {captured_on} by `data/scripts/capture_artifact_pool.py`; turned into this
capture on {TODAY}.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what is present, audit results, provider usage |
| `index.jsonl` | one row per trace: ids, status, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces: each module's inputs and outputs in order, the prediction, and the outcome-blind `judge_view` |

The runner's per-trace score is not in the body; it is in `../../outcomes/{cap}.jsonl`.
Together with the earlier captures this completes the `{portion}` pool of `pools-1`.

Statuses: {dict(statuses)}. `ok` is a complete run; `parse_failed` is a run whose
output dspy could not parse (the candidate's failure, scored 0 by the metric);
`capture_failed` is a task for which the provider returned no completion at all,
almost always a content block on the prompt itself. Such a trace is empty, carries
the provider's reason, is scored 0.0 like a parse failure, and is flagged
`capture_failed` in the outcomes file so an analysis can leave it out. The pool
export never includes it.
""")
    outs.sort(key=lambda r: (r["candidate_id"], r["task_id"], r["repeat"])); jsonl_write(outs, D / "outcomes" / f"{cap}.jsonl")
    per = {}
    for r in outs: per.setdefault(r["candidate_id"], []).append(r["score"])
    metric = "IFBench official per-instruction average" if b == "ifbench" else "HotpotQA official exact match on the answer"
    jdump(prov(f"outcomes/{cap}", "gold outcomes", b, [f"data/{b}/traces/{cap}"], {"records": len(outs), "mean_score_by_candidate": {c: round(sum(v)/len(v), 4) for c, v in sorted(per.items())}},
               {"copied_from_runner_scores": True}, {"scorer": metric}), D / "outcomes" / f"{cap}.provenance.json")
    outcomes_readme(b, f"Scores are the runner's recorded values of the official metric ({metric}).")
    return len(index_rows), dict(statuses)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--benchmark", required=True, choices=("hover", "ifbench", "hotpotqa"))
    ap.add_argument("--portion", required=True); ap.add_argument("--capture", required=True); a = ap.parse_args()
    D = REPO / "data" / a.benchmark; capdir = D / "traces" / a.capture
    if capdir.exists(): sys.exit(f"{capdir} exists; captures are append-only")
    try:
        n, st = hover(a.portion, a.capture) if a.benchmark == "hover" else artifact(a.benchmark, a.portion, a.capture)
    except Exception:
        shutil.rmtree(capdir, ignore_errors=True); (D / "outcomes" / f"{a.capture}.jsonl").unlink(missing_ok=True); (D / "outcomes" / f"{a.capture}.provenance.json").unlink(missing_ok=True)
        raise
    print(f"{a.benchmark} {a.capture}: {n} traces, statuses {st}")

if __name__ == "__main__": main()
