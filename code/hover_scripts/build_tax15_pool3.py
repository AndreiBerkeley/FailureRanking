#!/usr/bin/env python3
"""tax-15-pool3: tax-13 plus two hand-authored codes for what the tax-13 judge on the GEPA 50
(pointjudge-1, 2026-09-18) found and could not name: 170 points fit no code, 138 of them
unrecovered (16% of all unrecovered points). Read by hand, they are two mechanisms:

  SP_14  the query is issued for a known required page and retrieval does not return it
         (over-constrained / bundled / too broad / neighbours ranked above it)
  SP_15  the summary leaves a required document unidentified (placeholder, generic
         description, omitted from the missing list), so the next query has no exact target

Also writes assignments.json: the uncoded points of pointjudge-1 mapped to these codes by
rule (query turns -> SP_14, summary turns -> SP_15) with seven set aside by hand (three
instruction-compliance items, one empty, three that are neither mechanism). No re-judge:
data/hover/scripts/assign_uncoded_pool3.py applies the assignments to the mapping and to
its recovery run. Suffix on the id because tax-15 (models-1 set) already holds the count.
"""
import json, datetime, hashlib, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "data/hover/taxonomies/tax-13/taxonomy.json"
OUT = REPO / "data/hover/taxonomies/tax-15-pool3"
PJ = REPO / "runs/new_pipeline/hover/pointjudge-1"
TODAY = datetime.date.today().isoformat()

NEW = [
 {"id": "SP_14", "column": "domain", "name": "Required Page Not Retrieved by a Targeted Query",
  "definition": "The agent issues a search query for a required page whose identity it knows or could take from its context, and the retrieval does not return that page's own document: the query bundles the target with a second target or with already-resolved terms, is phrased as a broad comparison or question, or ranks neighbouring pages above the target.",
  "when_to_use": "Use when the required entity is named in the query (or resolvable from the reasoning) and the hop's results contain pages about or near it but not its own-title page, and the cause lies in how the query was composed.",
  "when_not_to_use": "Do not use when the entity was left out of the query (SP_08), when the query is syntactically unusable (SP_11), when no query was issued (SP_04), or when the summary never identified the entity at all (SP_15).",
  "consequence": "A retrieval hop is spent without obtaining the required document; with a fixed hop budget the page is usually never obtained and the task fails on that title.",
  "evidence": [], "hand_authored": True, "authored": TODAY,
  "grounded_in": "132 uncoded points of runs/new_pipeline/hover/pointjudge-1 (query turns), listed in assignments.json"},
 {"id": "SP_15", "column": "domain", "name": "Required Document Left Unidentified in Summary",
  "definition": "The summary does not resolve a required evidence document to its exact title: it leaves a placeholder or generic description in place of the entity, omits it from the list of missing documents, or describes the kind of fact needed instead of the page, so the next query turn has no exact target.",
  "when_to_use": "Use when a required page is still unretrieved and the summary's missing-document list or reasoning does not name it (or names a description in its place).",
  "when_not_to_use": "Do not use when the summary names the wrong status for a document it does identify (SP_06), nor for missing headers or formatting of the list (SP_10, SP_13).",
  "consequence": "The following query turn inherits no target for the missing page; the hop is spent on already-resolved material and the page is not obtained.",
  "evidence": [], "hand_authored": True, "authored": TODAY,
  "grounded_in": "31 uncoded points of runs/new_pipeline/hover/pointjudge-1 (summary turns), listed in assignments.json"},
]
SET_ASIDE = {("0e56eef3", 1): "instruction compliance: omitted claim descriptors", ("e6426d32", 3): "instruction compliance: omitted claim descriptors",
             ("35c8e7bd", 2): "empty problem text", ("87e6a551", 4): "no exhaustive comparison performed (neither mechanism)",
             ("984da484", 0): "omits evaluation of a claim component (neither mechanism)", ("d814231d", 2): "fails to address a claim component (neither mechanism)",
             ("d814231d", 6): "fails to address a claim component (neither mechanism)"}

def main():
    if (OUT / "taxonomy.json").exists(): sys.exit(f"{OUT} exists; artifacts are append-only")
    tax = json.loads(SRC.read_text()); assert [c["id"] for c in tax["codes"]][-1] == "SP_13"
    tax["codes"].extend(NEW)
    tax.setdefault("provenance", []).extend({"from": None, "to": c["id"], "operation": "hand-author", "why": c["grounded_in"]} for c in NEW)
    tax["counts"] = {"codes": len(tax["codes"]), "general": sum(c["column"] == "general" for c in tax["codes"]), "domain": sum(c["column"] == "domain" for c in tax["codes"]),
                     "hand_authored": 2, "from_tax_13": 13}
    tax["derives_from"] = ["data/hover/taxonomies/tax-13"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "taxonomy.json").write_text(json.dumps(tax, indent=2))
    # assignments
    rows = []; counts = {"SP_14": 0, "SP_15": 0, "set_aside": 0}
    for p in sorted(PJ.glob("traces/*.json")):
        d = json.loads(p.read_text())
        for i, q in enumerate(d["points"]):
            if q["codes"]: continue
            key = (d["trace_id"][:8], i)
            if key in SET_ASIDE:
                rows.append({"trace_id": d["trace_id"], "point": i, "code": None, "why": SET_ASIDE[key], "problem": q["problem"]}); counts["set_aside"] += 1; continue
            code = "SP_14" if q["agent"].startswith("create_query") else "SP_15"
            rows.append({"trace_id": d["trace_id"], "point": i, "code": code, "why": "by turn kind: query turn -> SP_14, summary turn -> SP_15", "problem": q["problem"]}); counts[code] += 1
    (OUT / "assignments.json").write_text(json.dumps(rows, indent=1))
    prov = {"id": "tax-15-pool3", "kind": "taxonomy", "benchmark": "hover", "created": TODAY, "candidate_set": "pool-3",
            "derives_from": {"taxonomy": "data/hover/taxonomies/tax-13/taxonomy.json", "operation": "append two hand-authored codes; the 13 others byte-identical"},
            "motivated_by": {"run": "runs/new_pipeline/hover/pointjudge-1", "uncoded_points": sum(counts.values()), "assigned": counts},
            "hand_authored": ["SP_14", "SP_15"], "counts": tax["counts"],
            "naming": "tax-<codes> with a set suffix: tax-15 is the models-1 taxonomy",
            "rates_valid_from": "assignments only (no re-judge): the SP_14/SP_15 rates are the decider's uncoded points, not a judge pass with the codes in view",
            "checks": {"first_13_codes_identical_to_tax_13": json.loads(SRC.read_text())["codes"] == tax["codes"][:13]}}
    (OUT / "provenance.json").write_text(json.dumps(prov, indent=2))
    rows_md = "\n".join(f"| `{c['id']}` | {c['column']} | {c['name']} | {c['definition'][:200]} |" for c in tax["codes"])
    (OUT / "README.md").write_text(f"""# tax-15-pool3 — tax-13 plus two hand-authored codes (GEPA candidate set)

Made {TODAY}. `tax-13`'s 13 codes byte-identical, plus `SP_14` and `SP_15`, written by hand from
the 170 points the tax-13 judge on the GEPA 50 (`runs/new_pipeline/hover/pointjudge-1`) kept but
could not name — 138 of them unrecovered, 16% of that run's unrecovered evidence. Read by hand they
are two mechanisms: a query issued for a known required page that retrieval does not return
(over-constrained, bundled, too broad), and a summary that leaves a required document unidentified.
The nearest existing code, `SP_08`, is the *omission* of the target from the query; these queries
include it and still miss. The suffix on the id is because `tax-15` (models-1) already holds the count.

`assignments.json` maps the uncoded points by turn kind — query turns → SP_14 ({counts['SP_14']}),
summary turns → SP_15 ({counts['SP_15']}) — with {counts['set_aside']} set aside by hand (instruction-compliance
items, one empty, three that are neither mechanism). No re-judge: `scripts/assign_uncoded_pool3.py`
applies them to the mapping and its recovery run. The rates of SP_14/SP_15 are therefore the
decider's "nothing fits" points, not a judge pass with these codes in view; a pass with them in
view would also catch instances the decider filed under neighbouring codes.

| id | column | name | definition |
|---|---|---|---|
{rows_md}
""")
    print(f"tax-15-pool3: {len(tax['codes'])} codes; assignments {counts}")

if __name__ == "__main__":
    main()
