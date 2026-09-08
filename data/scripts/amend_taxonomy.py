#!/usr/bin/env python3
"""Write the next taxonomy artifact from an existing one plus hand amendments to code text.

    python3 data/scripts/amend_taxonomy.py --benchmark ifbench --from tax-1 --to tax-2 --amendments <json> --why "<one line>"

Amendments change definition / when_to_use / when_not_to_use / name of existing codes only;
ids, columns and the code set stay, so a result under the amended taxonomy is the same
vocabulary read with tighter wording. Each amendment is recorded (code, field, before, after,
reason) in the new artifact's provenance and README. Append-only: refuses to overwrite.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]; TODAY = datetime.date.today().isoformat()
FIELDS = ("name", "definition", "when_to_use", "when_not_to_use")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True); ap.add_argument("--from", dest="src", required=True); ap.add_argument("--to", required=True)
    ap.add_argument("--amendments", type=Path, required=True, help="JSON list of {code, field, new, reason}")
    ap.add_argument("--why", required=True, help="what prompted the amendments")
    a = ap.parse_args(); b = a.benchmark; D = REPO / "data" / b / "taxonomies"; src = D / a.src; dst = D / a.to
    if dst.exists(): raise SystemExit(f"{dst} exists; taxonomies are append-only")
    t = json.loads((src / "taxonomy.json").read_text()); by_id = {c["id"]: c for c in t["codes"]}
    amendments = json.loads(a.amendments.read_text()); log = []
    for am in amendments:
        c = by_id[am["code"]]; f = am["field"]; assert f in FIELDS, f
        log.append({"code": am["code"], "name": c["name"], "field": f, "before": c.get(f), "after": am["new"], "reason": am["reason"]}); c[f] = am["new"]
        c.setdefault("amended", []).append({"in": a.to, "field": f, "on": TODAY})
    t["produced_by"] = f"{t.get('produced_by')} ; hand amendments to code text, data/scripts/amend_taxonomy.py ({a.to})"
    t["derives_from"] = [f"data/{b}/taxonomies/{a.src}"]; t["amendments"] = log
    dst.mkdir(parents=True); (dst / "taxonomy.json").write_text(json.dumps(t, indent=2, ensure_ascii=False))
    prov = {"id": a.to, "kind": "taxonomy", "benchmark": b, "created": TODAY, "produced_by": "hand amendments to code text (data/scripts/amend_taxonomy.py)", "derives_from": [f"data/{b}/taxonomies/{a.src}"],
            "why": a.why, "amendments": log, "counts": {"codes": len(t["codes"]), "codes_amended": len({x['code'] for x in log}), "fields_amended": len(log)},
            "checks": {"code_set_unchanged": True, "ids_unchanged": True, "columns_unchanged": True, "source_sha256": hashlib.sha256((src / "taxonomy.json").read_bytes()).hexdigest()}}
    (dst / "provenance.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False))
    rows = "\n".join(f"| `{c['id']}` | {c['column']} | {c['name']} | {str(c.get('definition','')).replace('|','/')} |" for c in t["codes"])
    am_rows = "\n".join(f"| `{x['code']}` | {x['field']} | {str(x['before']).replace('|','/')} | {str(x['after']).replace('|','/')} | {x['reason']} |" for x in log)
    (dst / "README.md").write_text(f"""# {a.to} — {a.src} with {len(log)} hand amendments to code text ({len({x['code'] for x in log})} codes)

Same {len(t['codes'])} codes, ids and columns as `{a.src}`; only the wording of the codes below changed.
Made {TODAY}. {a.why}

| code | field | before | after | reason |
|---|---|---|---|---|
{am_rows}

## The taxonomy

| id | column | name | definition |
|---|---|---|---|
{rows}
""")
    print(f"{b} {a.to}: {len(t['codes'])} codes, {len(log)} amendments on {len({x['code'] for x in log})} codes")


if __name__ == "__main__":
    main()
