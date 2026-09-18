#!/usr/bin/env python3
"""Admit the gap-test proposals that survived stage 6 into the taxonomy.

    python -m new_pipeline.generation.apply_proposals --taxonomy <t.json> --proposals <proposals.json> --out <t.json>

Every surviving proposal becomes a code with the next stable id in the taxonomy's own
series (SP_08 after SP_07). The proposal's evidence (the gap-test findings it was grouped
from) is kept on the code as grounding. Provenance records the operation as
"propose" with the gap-test file and the finding count, so the final taxonomy says which
codes the generator induced from its corpus and which it added after measuring its own
gaps. Nothing else in the taxonomy is touched.
"""
from __future__ import annotations

import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from new_pipeline.llm import log     # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--proposals", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    tax = json.loads(a.taxonomy.read_text())
    props = json.loads(a.proposals.read_text())
    surviving = props.get("surviving") or []
    codes = tax["codes"]
    ids = [c["id"] for c in codes]
    prefix = re.match(r"([A-Za-z]+)_", ids[0]).group(1) if ids else "SP"
    width = len(ids[0].split("_")[1]) if ids else 2
    n = max(int(i.split("_")[1]) for i in ids) if ids else 0
    added = []
    by_id = {x.get("id"): x for x in props.get("proposals") or []}
    for x in surviving:
        n += 1
        new_id = f"{prefix}_{n:0{width}d}"
        src = by_id.get(x.get("id"), x)
        code = {"id": new_id, "column": x.get("column") or src.get("column"),
                "name": x.get("name") or src.get("name"),
                "definition": x.get("definition") or src.get("definition"),
                "when_to_use": x.get("when_to_use") or src.get("when_to_use"),
                "when_not_to_use": x.get("when_not_to_use") or src.get("when_not_to_use"),
                "consequence": x.get("consequence") or src.get("consequence"),
                "evidence": src.get("evidence") or x.get("evidence") or [],
                "admitted": {"from": "gap-test proposal", "proposal_id": x.get("id"),
                             "findings": len(src.get("evidence") or []), "proposals_file": str(a.proposals)}}
        codes.append(code); added.append(code)
        tax.setdefault("provenance", []).append({"from": f"gap test ({props.get('findings_considered')} findings under FIT_GOOD)",
                                                  "to": new_id, "operation": "propose",
                                                  "why": f"grouped from {code['admitted']['findings']} findings; survived stage 6"})
    tax.setdefault("counts", {})
    tax["counts"]["proposed_and_admitted"] = len(added)
    tax["counts"]["codes"] = len(codes)
    tax["counts"]["general"] = sum(1 for c in codes if c.get("column") == "general")
    tax["counts"]["domain"] = sum(1 for c in codes if c.get("column") == "domain")
    a.out.write_text(json.dumps(tax, indent=2))
    log(f"apply_proposals: admitted {len(added)} of {len(surviving)} surviving proposals -> {a.out} ({len(codes)} codes)")
    for c in added:
        log(f"  {c['id']} [{c['column']}] {c['name']}")


if __name__ == "__main__":
    main()
