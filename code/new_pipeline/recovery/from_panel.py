"""Give a panel-judge mapping (map-N) the point shape the recovery pass reads.

    python3 -m new_pipeline.recovery.from_panel --mapping data/hover/mappings/map-5 --out <dir>

The panel judge records codes per trace, not failure points with evidence spans. Its
judge records do hold where each code was reported: the open reader's problems carry a
turn, an agent and a description; the annotators' votes are per turn. This writes a
pointjudge-shaped mapping whose points are

  * one per open-reader problem mapped to a counted code (turn, agent, the problem text as
    "what was wrong", no verbatim quote -- the panel judge kept none), and
  * for a counted code no open problem covers, one per turn an annotator reported it at,
    with the code's name as the description.

So every counted code is represented at every turn it was placed, and the recovery reader
sees what was wrong and where, as it does for a pointjudge mapping. `source` on each point
says which. Append-only: a new directory beside the mapping.
"""
import argparse, gzip, json
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from new_pipeline.pointjudge.judge import counts_from_points, FIT_GOOD   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--mapping", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--taxonomy", type=Path, default=Path("data/hover/taxonomies/tax-10/taxonomy.json"))
a = ap.parse_args()
if a.out.exists():
    raise SystemExit(f"{a.out} exists; mappings are append-only")
(a.out / "traces").mkdir(parents=True)
names = {c["id"]: c["name"] for c in json.loads(a.taxonomy.read_text())["codes"]}
rows = {json.loads(l)["trace_id"]: json.loads(l) for l in open(a.mapping / "mapping.jsonl")}
n = 0; src = Counter(); pts_total = 0
for b in sorted((a.mapping / "judge_records").glob("*.jsonl.gz")):
    with gzip.open(b, "rt") as fh:
        for line in fh:
            r = json.loads(line); m = rows[r["trace_id"]]
            counted = set(m["codes"]); turns = [{"turn": t["turn"], "agent": t["agent"]} for t in r["turns"]]
            at = {t["agent"]: t["turn"] for t in r["turns"]}
            points = []; covered = set()
            for det in ((r.get("open") or {}).get("details") or []):
                turn = det.get("turn") or at.get(det.get("agent"))
                codes = [c["code"] for c in det.get("codes") or [] if c.get("fitness", 0) >= FIT_GOOD and c["code"] in counted]
                if not codes or turn is None:
                    continue
                points.append({"turn": turn, "agent": det.get("agent"), "evidence": "", "problem": det.get("problem", ""),
                               "codes": codes, "none_fits": False, "missing": None, "from_a": None, "from_b": 0, "source": "open"})
                covered.update((turn, c) for c in codes); src["open"] += 1
            for key, votes in (r.get("votes_by_turn") or {}).items():
                turn = int(key.split(":")[0]); agent = key.split(":", 1)[1]
                for code in votes:
                    if code in counted and (turn, code) not in covered:
                        points.append({"turn": turn, "agent": agent, "evidence": "",
                                       "problem": f"{names.get(code, code)}: the annotators placed this failure mode at this turn",
                                       "codes": [code], "none_fits": False, "missing": None, "from_a": 0, "from_b": None, "source": "panel"})
                        covered.add((turn, code)); src["panel"] += 1
            points.sort(key=lambda p: p["turn"])
            rec = {"trace_id": r["trace_id"], "task_id": r["task_id"], "candidate_index": r.get("legacy_candidate_index"),
                   "candidate_id": r["candidate_id"], "status": "judged" if r["status"] == "judged" else "failed",
                   "codes": counts_from_points(points), "points": points, "turns": turns, "error": r.get("error"),
                   "derived": {"from": str(a.mapping), "rule": "open-reader problems + per-turn votes as points; no verbatim evidence"}}
            (a.out / "traces" / f"{r['trace_id']}.json").write_text(json.dumps(rec, indent=1)); n += 1; pts_total += len(points)
(a.out / "summary.json").write_text(json.dumps({"derived_from": str(a.mapping), "taxonomy": str(a.taxonomy), "traces": n,
                                                  "points": pts_total, "point_sources": dict(src)}, indent=2))
print(f"{a.out}: {n} traces, {pts_total} points ({dict(src)})")
