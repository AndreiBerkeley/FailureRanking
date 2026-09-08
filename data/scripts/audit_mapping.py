#!/usr/bin/env python3
"""Re-check a mapping from the data/ tree alone: python3 data/scripts/audit_mapping.py <benchmark> <mapping>"""
from __future__ import annotations
import gzip, hashlib, json, sys
from collections import Counter
from pathlib import Path
DATA = Path(__file__).resolve().parents[1]
PATTERNS = ("gold", "supporting", "required_titles", "outcome"); EXACT = {"label"}
def scan(o, p=""):
    h = []
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("gold_stripped", "judge_metadata"): continue
            kl = str(k).lower()
            if kl in EXACT or any(x in kl for x in PATTERNS): h.append(f"{p}/{k}")
            h += scan(v, f"{p}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): h += scan(v, f"{p}[{i}]")
    return h
def main(b, mid):
    B = DATA / b; d = B / "mappings" / mid; m = json.load(open(d / "manifest.json"))
    tf = B / "taxonomies" / m["taxonomy"] / "taxonomy.json"; codes = {c["id"] for c in json.load(open(tf))["codes"]}
    if hashlib.sha256(open(tf, "rb").read()).hexdigest() != m["taxonomy_sha256"]: print("FAILED: taxonomy hash"); return 1
    cap = {r["trace_id"]: r for line in open(B / "traces" / m["capture"] / "index.jsonl") for r in [json.loads(line)]}
    rows = {r["trace_id"]: r for line in open(d / "mapping.jsonl") for r in [json.loads(line)]}
    problems, seen, st = [], set(), Counter()
    for cid, meta in m["judge_records"].items():
        f = d / meta["file"]
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != meta["sha256"]: problems.append(f"{meta['file']}: hash differs")
        n = 0
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line); n += 1; t = rec["trace_id"]; row = rows.get(t)
                if row is None: problems.append(f"{t}: record without row"); continue
                c = cap.get(t)
                if c is None: problems.append(f"{t}: not in capture")
                elif (c["candidate_id"], c["task_id"]) != (row["candidate_id"], row["task_id"]) or row["candidate_id"] != cid: problems.append(f"{t}: identity mismatch")
                if row["status"] == "judged" and set(row["codes"] or {}) - codes: problems.append(f"{t}: codes outside taxonomy")
                if scan(rec): problems.append(f"{t}: gold key in record")
                st[row["status"]] += 1; seen.add(t)
        if n != meta["rows"]: problems.append(f"{meta['file']}: rows differ")
    if set(rows) - seen: problems.append("rows without records")
    if st.get("judged", 0) != m["counts"]["judged"]: problems.append("judged count differs from manifest")
    print(f"{b} {mid}: {m['taxonomy']} over {m['capture']}: {st.get('judged',0)} judged, coverage {m['counts']['coverage']:.0%}")
    if problems: print("FAILED"); [print("  -", p) for p in problems[:15]]; return 1
    print("OK: rows↔records, hashes, capture membership, codes within taxonomy, no gold keys"); return 0
if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
