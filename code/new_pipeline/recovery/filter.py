"""Derive an unrecovered-only mapping from a recovery run.

    python3 -m new_pipeline.recovery.filter --recovery <recovery run> --out <new mapping dir>

Every trace record is copied with only the points the recovery pass did not find
recovered (unrecovered and unassessable; unrecorded points count as unrecovered); the
per-trace code map is recomputed. The result has the pointjudge mapping shape, so every
method, draw and sweep script reads it unchanged. Append-only: a new directory beside the
originals, never an edit of either.
"""
import argparse, json, shutil
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from new_pipeline.pointjudge.judge import counts_from_points   # noqa: E402
from new_pipeline.recovery.recovery import RECOVERED           # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--recovery", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
if a.out.exists():
    raise SystemExit(f"{a.out} exists; mappings are append-only")
(a.out / "traces").mkdir(parents=True)
kept = dropped = 0; verdicts = Counter()
for f in sorted((a.recovery / "traces").glob("*.json")):
    d = json.loads(f.read_text())
    if d.get("status") == "judged":
        pts = [p for p in d["points"] if p.get("recovery") not in RECOVERED]
        dropped += len(d["points"]) - len(pts); kept += len(pts)
        for p in d["points"]: verdicts[p.get("recovery")] += 1
        d["points"] = pts; d["codes"] = counts_from_points(pts)
        d["derived"] = {"from": str(a.recovery), "rule": "points with recovery in RECOVERED removed; unassessable and unrecorded kept"}
    (a.out / "traces" / f.name).write_text(json.dumps(d, indent=1))
s = json.loads((a.recovery / "summary.json").read_text())
s["derived"] = {"from": str(a.recovery), "kept_points": kept, "removed_points": dropped, "verdicts": dict(verdicts)}
s["taxonomy"] = json.loads(next((a.recovery / "traces").glob("*.json")).read_text()).get("taxonomy", s.get("taxonomy"))
(a.out / "summary.json").write_text(json.dumps(s, indent=2))
print(f"{a.out}: kept {kept} points, removed {dropped} recovered; verdicts {dict(verdicts)}")
