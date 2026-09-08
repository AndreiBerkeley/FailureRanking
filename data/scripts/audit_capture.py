#!/usr/bin/env python3
"""Re-check a capture from the data/ tree alone: python3 data/scripts/audit_capture.py <benchmark> <capture>"""
from __future__ import annotations
import gzip, hashlib, json, sys
from collections import Counter
from pathlib import Path
DATA = Path(__file__).resolve().parents[1]
PATTERNS = ("gold", "supporting", "required_titles", "outcome", "score"); EXACT = {"label"}
def scan(o, p=""):
    h = []
    if isinstance(o, dict):
        for k, v in o.items():
            kl = str(k).lower()
            if kl in EXACT or any(x in kl for x in PATTERNS): h.append(f"{p}/{k}")
            h += scan(v, f"{p}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): h += scan(v, f"{p}[{i}]")
    return h
def main(b, cap):
    B = DATA / b; d = B / "traces" / cap; m = json.load(open(d / "manifest.json"))
    split = json.load(open(B / "splits" / m["split"] / "split.json")); allowed = set()
    for p in m["portions"]: allowed |= set(split["portions"][p])
    cset = json.load(open(B / "candidates" / "sets" / f"{m['candidate_set']}.json")); cands = set(cset["candidate_ids"])
    idx = {r["trace_id"]: r for line in open(d / "index.jsonl") for r in [json.loads(line)]}
    problems, seen, keys, gold = [], set(), set(), 0
    for cid, meta in m["bodies"].items():
        f = d / meta["file"]
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != meta["sha256"]: problems.append(f"{meta['file']}: hash differs")
        n = 0
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n"); x = json.loads(line); n += 1; t = x["trace_id"]; r = idx.get(t)
                if r is None: problems.append(f"{t}: no index row"); continue
                if hashlib.sha256(line.encode()).hexdigest() != r["body_sha256"]: problems.append(f"{t}: body hash differs")
                if x["candidate_id"] != cid or x["candidate_id"] not in cands: problems.append(f"{t}: candidate wrong")
                if x["task_id"] not in allowed: problems.append(f"{t}: task outside portions")
                k = (x["candidate_id"], x["task_id"], x["repeat"])
                if k in keys: problems.append(f"{t}: duplicate key")
                keys.add(k); seen.add(t)
                if scan(x): gold += 1
        if n != meta["rows"]: problems.append(f"{meta['file']}: {n} rows vs {meta['rows']}")
    if set(idx) - seen: problems.append(f"{len(set(idx)-seen)} index rows without body")
    if len(seen) != m["present_traces"]: problems.append("present_traces differs")
    if gold: problems.append(f"{gold} bodies carry gold-bearing keys")
    print(f"{b} {cap}: {len(seen)} traces, {len({k[0] for k in keys})} candidates, {len({k[1] for k in keys})} tasks, repeats {sorted({k[2] for k in keys})}")
    if problems: print("FAILED"); [print("  -", p) for p in problems[:15]]; return 1
    print("OK: index↔bodies, hashes, counts, set/split membership, no gold keys"); return 0
if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
