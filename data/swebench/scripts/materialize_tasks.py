#!/usr/bin/env python3
"""Write data/swebench/tasks/tasks.jsonl from the SWE-bench Verified test split
already present in the local Hugging Face cache. No network. Needs pyarrow, so
run it with an interpreter that has it, e.g.
    /Users/andreicojocaru/Desktop/GEPA_Experiments/.venv/bin/python data/swebench/scripts/materialize_tasks.py
The newest cached copy is used and its identity (dataset hash directory, arrow
file sha256) is recorded in provenance.json.
"""
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path
import pyarrow as pa, pyarrow.ipc as ipc

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "data" / "swebench" / "tasks"
CACHE = Path.home() / ".cache" / "huggingface" / "datasets" / "SWE-bench___swe-bench_verified" / "default" / "0.0.0"
TODAY = "2026-09-06"
GOLD = ("patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS", "eval_script")
INPUT = ("repo", "base_commit", "problem_statement", "hints_text", "version", "environment_setup_commit", "created_at")
META = ("difficulty", "eval_type", "image", "log_parser")

def read_arrow(p: Path):
    with pa.memory_map(str(p), "r") as src:
        try: return ipc.open_stream(src).read_all()
        except pa.ArrowInvalid: return ipc.open_file(src).read_all()

def main():
    dirs = sorted([d for d in CACHE.iterdir() if (d / "swe-bench_verified-test.arrow").exists()], key=lambda d: d.stat().st_mtime)
    src_dir = dirs[-1]; arrow = src_dir / "swe-bench_verified-test.arrow"
    tbl = read_arrow(arrow); rows = tbl.to_pylist()
    assert len(rows) == 500, len(rows)
    def js(v):
        if isinstance(v, str) and v[:1] in "[{":
            try: return json.loads(v)
            except Exception: return v
        return v
    out = []
    for r in rows:
        out.append({"task_id": r["instance_id"], "benchmark": "swebench",
                    "inputs": {k: r.get(k) for k in INPUT if k in r},
                    "gold": {k: js(r.get(k)) for k in GOLD if k in r},
                    "meta": {k: r.get(k) for k in META if k in r},
                    "source": {"dataset": "SWE-bench/SWE-bench_Verified", "split": "test", "cache_hash_dir": src_dir.name}})
    out.sort(key=lambda x: x["task_id"])
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "tasks.jsonl", "w") as f:
        for x in out: f.write(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n")
    repos = {}
    for x in out: repos[x["inputs"]["repo"]] = repos.get(x["inputs"]["repo"], 0) + 1
    diff = {}
    for x in out: d = x["meta"].get("difficulty"); diff[d] = diff.get(d, 0) + 1
    prov = {"id": "tasks", "kind": "task registry", "benchmark": "swebench", "created": TODAY,
            "derives_from": [str(arrow)], "produced_by": {"script": "data/swebench/scripts/materialize_tasks.py", "interpreter": sys.executable,
                                                          "command": f"{sys.executable} data/swebench/scripts/materialize_tasks.py"},
            "source": {"dataset": "SWE-bench/SWE-bench_Verified (Hugging Face)", "split": "test", "cache_hash_dir": src_dir.name,
                       "arrow_sha256": hashlib.sha256(arrow.read_bytes()).hexdigest(), "columns": tbl.column_names,
                       "other_cached_copies": [d.name for d in dirs if d != src_dir]},
            "counts": {"tasks": len(out), "repos": repos, "difficulty": diff},
            "checks": {"row_count_500": True, "instance_ids_unique": len({x["task_id"] for x in out}) == 500}}
    json.dump(prov, open(OUT / "provenance.json", "w"), indent=2, sort_keys=True); print(json.dumps(prov["counts"], indent=1)); print("columns:", tbl.column_names)
if __name__ == "__main__": main()
