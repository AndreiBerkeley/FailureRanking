"""Append SP_15 assignments from pointjudge-2 onto the pointjudge-1 mapping.

pointjudge-1 is the base (tax-14, two readers + decider). pointjudge-2 read the
same 450 traces with tax-15, whose other 14 codes are byte-identical, so its
SP_15 points are the only thing tax-14 could not express. Everything else in
pointjudge-2 is discarded here.

Writes a new run directory; pointjudge-1 is not modified.
"""
import json, sys, shutil
from pathlib import Path

BASE = Path("runs/new_pipeline/hover-models/pointjudge-1")
ADD  = Path("runs/new_pipeline/hover-models/pointjudge-2")
OUT  = Path(sys.argv[1] if len(sys.argv) > 1
            else "runs/new_pipeline/hover-models/pointjudge-1-sp15")
CODE = "SP_15"

(OUT / "traces").mkdir(parents=True, exist_ok=True)
stats = {"traces": 0, "base_failed": 0, "sp15_points_added": 0,
         "traces_gaining_sp15": 0, "on_a_step_base_already_coded": 0,
         "on_a_step_base_marked_none_fits": 0, "on_a_step_base_saw_nothing": 0}

for bp in sorted(BASE.glob("traces/*.json")):
    b = json.loads(bp.read_text())
    ap = ADD / "traces" / bp.name
    if b.get("status") != "judged":
        stats["base_failed"] += 1
        (OUT / "traces" / bp.name).write_text(json.dumps(b, indent=2))
        continue
    stats["traces"] += 1
    add = json.loads(ap.read_text()) if ap.exists() else {}
    new = [q for q in (add.get("points") or []) if CODE in (q.get("codes") or [])]
    if new:
        base_coded = {q["turn"] for q in b["points"] if q.get("codes")}
        base_none  = {q["turn"] for q in b["points"] if q.get("none_fits")}
        for q in new:
            t = q["turn"]
            if t in base_coded: stats["on_a_step_base_already_coded"] += 1
            elif t in base_none: stats["on_a_step_base_marked_none_fits"] += 1
            else: stats["on_a_step_base_saw_nothing"] += 1
            r = dict(q)
            r["codes"] = [CODE]                      # only SP_15 is carried over
            r["source"] = "pointjudge-2"             # provenance on every added point
            r.pop("from_a", None); r.pop("from_b", None)
            b["points"].append(r)
            stats["sp15_points_added"] += 1
        stats["traces_gaining_sp15"] += 1
        b["codes"][CODE] = len({q["turn"] for q in new})
        b["codes"] = {k: b["codes"][k] for k in sorted(b["codes"])}
    b["appended"] = {"code": CODE, "from": str(ADD), "taxonomy":
                     "data/hover/taxonomies/tax-15/taxonomy.json"}
    (OUT / "traces" / bp.name).write_text(json.dumps(b, indent=2))

summary = json.loads((BASE / "summary.json").read_text())
summary["appended"] = {
    "code": CODE, "from": str(ADD),
    "note": ("SP_15 assignments lifted from pointjudge-2 (tax-15, one reader, no "
             "decider) onto the pointjudge-1 mapping. The two runs used different "
             "judge shapes, so SP_15's counts here were produced by a different "
             "process than the other 14 codes' and are not on the same footing."),
    "stats": stats}
fired = summary["traces_firing_each_code"]
fired[CODE] = stats["traces_gaining_sp15"]
summary["traces_firing_each_code"] = dict(sorted(fired.items(), key=lambda x: -x[1]))
summary["taxonomy"] = "data/hover/taxonomies/tax-15/taxonomy.json"
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
if (BASE / "profiles.json").exists():
    shutil.copy(BASE / "profiles.json", OUT / "profiles.json.base")
print(json.dumps(stats, indent=2))
print(f"-> {OUT}")
