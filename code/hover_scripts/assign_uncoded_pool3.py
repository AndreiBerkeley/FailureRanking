#!/usr/bin/env python3
"""Apply tax-15-pool3/assignments.json to pointjudge-1 and to its recovery run, without a model call.

Writes runs/new_pipeline/hover/pointjudge-1-tax15 (judge shape) and runs/new_pipeline/hover/recovery-2-tax15
(recovery shape: the same points with their recovery verdicts, so recovery.filter can derive the
unrecovered-only mapping). Neither source is modified. Every touched point carries
"source": "hand-assigned <date>" and keeps the decider's gap note under "gap_note".
"""
import json, sys, datetime
from collections import Counter
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from new_pipeline.pointjudge.judge import counts_from_points  # noqa: E402

TAX = "data/hover/taxonomies/tax-15-pool3/taxonomy.json"
assign = {(a["trace_id"], a["point"]): a["code"] for a in json.loads((REPO / "data/hover/taxonomies/tax-15-pool3/assignments.json").read_text()) if a["code"]}
TODAY = datetime.date.today().isoformat()

def apply(base: Path, out: Path):
    if out.exists(): sys.exit(f"{out} exists; artifacts are append-only")
    (out / "traces").mkdir(parents=True); stats = Counter()
    for bp in sorted(base.glob("traces/*.json")):
        b = json.loads(bp.read_text())
        for i, p in enumerate(b["points"]):
            key = (b["trace_id"], i)
            if key in assign:
                assert not p["codes"], key
                p["codes"] = [assign[key]]; p["none_fits"] = False
                p["gap_note"] = p.get("missing"); p["missing"] = None; p["source"] = f"hand-assigned {TODAY}"
                stats["assigned"] += 1; stats[assign[key]] += 1
            elif not p["codes"]: stats["still_uncoded"] += 1
        b["codes"] = counts_from_points(b["points"])
        b["derived"] = {"from": str(base.relative_to(REPO)), "taxonomy": TAX, "rule": "tax-15-pool3/assignments.json applied; no re-judge"}
        (out / "traces" / bp.name).write_text(json.dumps(b, indent=2))
    sm = json.loads((base / "summary.json").read_text())
    sm.update({"taxonomy": TAX, "derived_from": str(base.relative_to(REPO)), "hand_assigned": dict(stats), "note": "tax-15-pool3 assignments applied to every point that fit no tax-13 code; no model call"})
    (out / "summary.json").write_text(json.dumps(sm, indent=2))
    print(f"{out.relative_to(REPO)}: {dict(stats)}")

apply(REPO / "runs/new_pipeline/hover/pointjudge-1", REPO / "runs/new_pipeline/hover/pointjudge-1-tax15")
apply(REPO / "runs/new_pipeline/hover/recovery-2", REPO / "runs/new_pipeline/hover/recovery-2-tax15")
