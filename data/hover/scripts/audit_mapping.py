#!/usr/bin/env python3
"""Re-check a mapping in data/hover from the new tree alone.

    python3 data/hover/scripts/audit_mapping.py map-1

Checks: every mapping row has a judge record and vice versa; every judged
trace exists in the mapping's capture with the same candidate and task; every
code fired is a code of the mapping's taxonomy; counts match the manifest; no
gold-bearing key appears in any record (the judge's own empty
`gold_stripped` list is the one allowed key). Non-zero exit on any failure.
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


def scan(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if k == "gold_stripped":
                if v != []:
                    hits.append(f"{path}/gold_stripped non-empty")
                continue
            if kl in GOLD_KEY_EXACT or any(p in kl for p in GOLD_KEY_PATTERNS):
                hits.append(f"{path}/{k}")
            hits.extend(scan(v, f"{path}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(scan(v, f"{path}[{i}]"))
    return hits


def main(mid: str) -> int:
    d = HOVER / "mappings" / mid
    m = json.load(open(d / "manifest.json"))
    tax = json.load(open(HOVER / "taxonomies" / m["taxonomy"] / "taxonomy.json"))
    codes = {c["id"] for c in tax["codes"]}
    if hashlib.sha256(open(HOVER / "taxonomies" / m["taxonomy"] / "taxonomy.json", "rb").read()).hexdigest() != m["taxonomy_sha256"]:
        print("FAILED: taxonomy file hash differs from manifest"); return 1
    cap = {r["trace_id"]: r for line in open(HOVER / "traces" / m["capture"] / "index.jsonl") for r in [json.loads(line)]}
    rows = {r["trace_id"]: r for line in open(d / "mapping.jsonl") for r in [json.loads(line)]}
    problems, seen, status = [], set(), Counter()
    for cid, meta in m["judge_records"].items():
        f = d / meta["file"]
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != meta["sha256"]:
            problems.append(f"{meta['file']}: hash differs from manifest")
        n = 0
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line); n += 1
                tid = rec["trace_id"]
                row = rows.get(tid)
                if row is None:
                    problems.append(f"{tid}: record without mapping row"); continue
                if rec["candidate_id"] != cid or row["candidate_id"] != cid:
                    problems.append(f"{tid}: filed under wrong candidate")
                c = cap.get(tid)
                if c is None:
                    problems.append(f"{tid}: not in capture {m['capture']}")
                elif (c["candidate_id"], c["task_id"]) != (row["candidate_id"], row["task_id"]):
                    problems.append(f"{tid}: candidate/task differ from capture")
                if row["status"] == "judged":
                    bad = set(row["codes"] or {}) - codes
                    if bad:
                        problems.append(f"{tid}: codes outside taxonomy {sorted(bad)}")
                if scan(rec):
                    problems.append(f"{tid}: gold-bearing key in record")
                status[row["status"]] += 1
                seen.add(tid)
        if n != meta["rows"]:
            problems.append(f"{meta['file']}: {n} rows, manifest says {meta['rows']}")
    if set(rows) - seen:
        problems.append(f"{len(set(rows) - seen)} mapping rows without a record")
    if status.get("judged", 0) != m["counts"]["judged"] or status.get("failed", 0) != m["counts"]["failed"]:
        problems.append(f"status counts {dict(status)} differ from manifest {m['counts']}")
    print(f"{mid}: {m['taxonomy']} over {m['capture']}: {status.get('judged',0)} judged, {status.get('failed',0)} failed, "
          f"coverage {m['counts']['coverage']:.0%}")
    if problems:
        print("FAILED"); [print("  -", p) for p in problems[:20]]; return 1
    print("OK: rows↔records, hashes, capture membership, codes within taxonomy, no gold keys")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "map-1"))
