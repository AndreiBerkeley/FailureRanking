"""pointjudge-1-tax2: the pointjudge-1 mapping with its 22 none_fits points hand-assigned
to tax-2 codes (taxonomies/tax-2/assignments.json). No model call; no re-judge.

Writes a new run directory; pointjudge-1 is not modified. Every touched point carries
"source": "hand-assigned 2026-09-11" and keeps the decider's gap note under "gap_note".
"""
import json, shutil, sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from new_pipeline.pointjudge.judge import counts_from_points  # noqa: E402

BASE = REPO / "runs/new_pipeline/lcb-models/pointjudge-1"
OUT = REPO / "runs/new_pipeline/lcb-models/pointjudge-1-tax2"
TAX = "data/livecodebench/taxonomies/tax-2/taxonomy.json"
assign = {(a["trace_id"], a["point"]): a["code"] for a in
          json.loads((REPO / "data/livecodebench/taxonomies/tax-2/assignments.json").read_text())}

if OUT.exists():
    sys.exit(f"{OUT} exists; artifacts are append-only")
(OUT / "traces").mkdir(parents=True)
stats = Counter(); used = set()
for bp in sorted(BASE.glob("traces/*.json")):
    b = json.loads(bp.read_text())
    for i, p in enumerate(b["points"]):
        key = (b["trace_id"], i)
        if key in assign:
            assert p["none_fits"] and not p["codes"], key
            p["codes"] = [assign[key]]; p["none_fits"] = False
            p["gap_note"] = p["missing"]; p["missing"] = None
            p["source"] = "hand-assigned 2026-09-11"
            used.add(key); stats["assigned"] += 1; stats[assign[key]] += 1
        elif p["none_fits"]:
            stats["still_uncovered"] += 1
    before = b["codes"]; b["codes"] = counts_from_points(b["points"])
    if before != b["codes"]: stats["traces_changed"] += 1
    b["coverage"] = {**(b.get("coverage") or {}), "hand_assigned": sum(1 for p in b["points"] if p.get("source"))}
    b["derived"] = {"from": "runs/new_pipeline/lcb-models/pointjudge-1", "taxonomy": TAX,
                    "operation": "none_fits points hand-assigned, no re-judge"}
    (OUT / "traces" / bp.name).write_text(json.dumps(b, indent=2))
assert used == set(assign), set(assign) - used

s = json.loads((BASE / "summary.json").read_text())
s["taxonomy"] = TAX
s["judge"] = s["judge"] + "; then 22 none_fits points hand-assigned to tax-2 codes (no re-judge)"
fired = Counter()
for f in (OUT / "traces").glob("*.json"):
    for c in json.loads(f.read_text())["codes"]: fired[c] += 1
s["traces_firing_each_code"] = dict(fired.most_common())
s["codes_never_fired"] = [c["id"] for c in json.loads((REPO / TAX).read_text())["codes"] if c["id"] not in fired]
s["uncovered_points"] = stats["still_uncovered"]; s.pop("uncovered_described", None)
s["derived"] = {"from": "runs/new_pipeline/lcb-models/pointjudge-1",
                "assignments": "data/livecodebench/taxonomies/tax-2/assignments.json",
                "note": ("The 22 points the decider could not place under tax-1 were assigned tax-2 codes by hand "
                         "so experiments can run before a re-judge. SP_08/SP_09/SP_10 counts here come from a "
                         "different process than SP_01-SP_07 (a decider with the code in view) and must be "
                         "cited as hand-assigned. Everything else is pointjudge-1 unchanged."),
                "stats": dict(stats)}
(OUT / "summary.json").write_text(json.dumps(s, indent=2))
shutil.copy(BASE / "profiles.json", OUT / "profiles.json")
print(dict(stats)); print("firing:", s["traces_firing_each_code"]); print("never fired:", s["codes_never_fired"])
