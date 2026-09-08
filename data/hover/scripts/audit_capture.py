#!/usr/bin/env python3
"""Re-check a capture in data/hover from the new tree alone.

    python3 data/hover/scripts/audit_capture.py cap-1

Checks: every index row has a body line with the recorded sha256 and vice
versa; counts match the manifest; every trace's task is in the manifest's
split portions and its candidate in the manifest's set; no gold-bearing key
appears anywhere in a body. Exit status is non-zero on any failure.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HOVER = Path(__file__).resolve().parents[1]
GOLD_KEY_PATTERNS = ("gold", "supporting", "required_titles")
GOLD_KEY_EXACT = {"label"}


def scan_gold_keys(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in GOLD_KEY_EXACT or any(p in kl for p in GOLD_KEY_PATTERNS):
                hits.append(f"{path}/{k}")
            hits.extend(scan_gold_keys(v, f"{path}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(scan_gold_keys(v, f"{path}[{i}]"))
    return hits


def main(capture: str) -> int:
    cap = HOVER / "traces" / capture
    manifest = json.load(open(cap / "manifest.json"))
    split = json.load(open(HOVER / "splits" / manifest["split"] / "split.json"))
    allowed_tasks = set()
    for p in manifest["portions"]:
        allowed_tasks |= set(split["portions"][p])
    allowed_cands = set(manifest["candidate_ids"])
    cset = json.load(open(HOVER / "candidates" / "sets" / f"{manifest['candidate_set']}.json"))
    problems = []
    if set(cset["candidate_ids"]) != allowed_cands:
        problems.append("manifest candidate_ids != candidate set file")

    index = {}
    for line in open(cap / "index.jsonl"):
        r = json.loads(line)
        index[r["trace_id"]] = r
    seen = set()
    keys = set()
    gold_hits = 0
    per_cand = Counter()
    for cid, meta in manifest["bodies"].items():
        f = cap / meta["file"]
        h = hashlib.sha256(open(f, "rb").read()).hexdigest()
        if h != meta["sha256"]:
            problems.append(f"{meta['file']}: file sha256 differs from manifest")
        n = 0
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                b = json.loads(line)
                n += 1
                tid = b["trace_id"]
                r = index.get(tid)
                if r is None:
                    problems.append(f"{tid}: body without index row"); continue
                if hashlib.sha256(line.encode("utf-8")).hexdigest() != r["body_sha256"]:
                    problems.append(f"{tid}: body sha256 differs from index")
                if (b["candidate_id"], b["task_id"], b["repeat"]) != (r["candidate_id"], r["task_id"], r["repeat"]):
                    problems.append(f"{tid}: identity differs between body and index")
                if b["candidate_id"] != cid:
                    problems.append(f"{tid}: filed under the wrong candidate")
                if b["candidate_id"] not in allowed_cands:
                    problems.append(f"{tid}: candidate not in set")
                if b["task_id"] not in allowed_tasks:
                    problems.append(f"{tid}: task not in split portions")
                k = (b["candidate_id"], b["task_id"], b["repeat"])
                if k in keys:
                    problems.append(f"{tid}: duplicate (candidate, task, repeat)")
                keys.add(k)
                if scan_gold_keys(b):
                    gold_hits += 1
                seen.add(tid)
                per_cand[cid] += 1
        if n != meta["rows"]:
            problems.append(f"{meta['file']}: {n} rows, manifest says {meta['rows']}")
    missing = set(index) - seen
    if missing:
        problems.append(f"{len(missing)} index rows without a body")
    if len(seen) != manifest["present_traces"]:
        problems.append(f"{len(seen)} bodies, manifest says {manifest['present_traces']}")
    if gold_hits:
        problems.append(f"{gold_hits} bodies contain gold-bearing keys")

    print(f"{capture}: {len(seen)} traces, {len(per_cand)} candidates, {len({k[1] for k in keys})} tasks, "
          f"repeats {sorted({k[2] for k in keys})}")
    if problems:
        print("FAILED"); [print("  -", p) for p in problems[:20]]
        return 1
    print("OK: index↔bodies, hashes, counts, set/split membership, no gold keys")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "cap-1"))
