#!/usr/bin/env python3
"""Sharing copy of a taxonomy: the codes with at most N evidence quotes each, and no run bookkeeping.

    python3 sharing/scripts/trim_taxonomy.py <taxonomy.json> --out <file> [--evidence 3]

Kept per code: id, column, name, definition, when_to_use, when_not_to_use, consequence, the
hand-authored flag where set, and the first N evidence entries as {quote, missing} (trace ids
dropped -- they mean nothing outside the repository). Kept at the top: benchmark, code count.
Dropped: the generation run's operation log (provenance, amendments, split/finding counters).
"""
import argparse, json
from pathlib import Path

KEEP = ["id", "column", "name", "definition", "when_to_use", "when_not_to_use", "consequence"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--evidence", type=int, default=3)
    a = ap.parse_args(); t = json.load(open(a.src)); codes = []
    for c in t["codes"]:
        d = {k: c[k] for k in KEEP if k in c and c[k] not in (None, "")}
        if c.get("hand_authored") or c.get("authored") == "hand": d["hand_authored"] = True
        ev = [{k: e[k] for k in ("quote", "missing") if e.get(k)} for e in (c.get("evidence") or [])[: a.evidence]]
        if ev: d["evidence"] = ev
        codes.append(d)
    out = {"benchmark": t.get("benchmark"), "codes_count": len(codes),
           "note": f"sharing copy: at most {a.evidence} evidence quotes per code; the generation run's provenance is not included", "codes": codes}
    a.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"{a.out}: {len(codes)} codes, {sum(len(c.get('evidence', [])) for c in codes)} evidence entries, {len(json.dumps(out)):,} chars (was {len(json.dumps(t)):,})")


if __name__ == "__main__":
    main()
