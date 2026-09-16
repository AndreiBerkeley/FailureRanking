#!/usr/bin/env python3
"""Materialise the taxonomy that a granularity run proposed.

    apply_splits.py --taxonomy <tax.json> --granularity <granularity.json> --out <new tax.json>

`granularity.py` decides which codes are more than one mechanism and verifies
each proposal against the data, but it writes only the verdict. This turns an
accepted verdict into a taxonomy a judge can be pointed at: every accepted
split's parts replace their parent, every other code is carried through
unchanged, and each new code records the parent it came from.

Parts inherit their parent's column: a split divides one mechanism into
several, and where in an agent's execution the mistake happens does not change
by naming it more precisely. IDs are a fresh namespace (SP_01...) so a result
computed under this taxonomy can never be silently compared with one computed
under the parent's FM_ ids.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--granularity", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--prefix", default="SP", help="id prefix for the new namespace")
    ap.add_argument("--include-rejected", action="store_true",
                    help="also apply splits the independence test rejected "
                         "(default: only accepted ones)")
    a = ap.parse_args()

    if a.out.exists():
        raise SystemExit(f"{a.out} exists; taxonomies are append-only, use a new name")

    tax = json.loads(a.taxonomy.read_text())
    gran = json.loads(a.granularity.read_text())
    by_name = {o["code"]: o for o in gran["results"]}

    codes, provenance = [], []
    for c in tax["codes"]:
        entry = by_name.get(c["name"])
        take = entry and entry.get("parts") and (
            entry.get("accepted") or a.include_rejected)
        if not take:
            codes.append(dict(c, _origin=("kept", c["name"])))
            provenance.append({"from": c["name"], "to": None, "operation": "keep",
                               "why": (entry or {}).get("reason")
                                      or "not examined (too few findings)"})
            continue
        for p in entry["parts"]:
            codes.append({
                "column": c["column"],          # a split does not move a mechanism
                "name": p["name"],
                "definition": p["definition"],
                "when_to_use": p["when_to_use"],
                "when_not_to_use": p["when_not_to_use"],
                "split_from": c["name"],
                "split_from_id": c["id"],
                "n_findings": len(p.get("finding_indices") or []),
                "_origin": ("split", c["name"]),
            })
        provenance.append({"from": c["name"], "to": [p["name"] for p in entry["parts"]],
                           "operation": "split", "why": entry.get("reason"),
                           "confidence": entry.get("confidence")})

    for i, c in enumerate(codes, 1):
        c["id"] = f"{a.prefix}_{i:02d}"
        c.pop("_origin", None)

    out = {
        "benchmark": tax.get("benchmark"),
        "framework": tax.get("framework"),
        "produced_by": "new_pipeline.generation.apply_splits",
        "derives_from": {"taxonomy": str(a.taxonomy), "granularity": str(a.granularity),
                         "mode": gran.get("mode"),
                         "records_the_splits_were_verified_on": gran.get("records")},
        "codes": codes,
        "provenance": provenance,
        "counts": {"parent_codes": len(tax["codes"]), "codes": len(codes),
                   "split": sum(1 for p in provenance if p["operation"] == "split"),
                   "kept": sum(1 for p in provenance if p["operation"] == "keep")},
    }
    a.out.write_text(json.dumps(out, indent=2) + "\n")
    print(f"{len(tax['codes'])} -> {len(codes)} codes "
          f"({out['counts']['split']} split, {out['counts']['kept']} kept) -> {a.out}")
    for p in provenance:
        if p["operation"] == "split":
            print(f"  {p['from']}")
            for n in p["to"]:
                print(f"     -> {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
