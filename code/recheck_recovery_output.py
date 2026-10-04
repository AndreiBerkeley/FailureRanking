#!/usr/bin/env python3
"""Re-check a recovery run's output claims against the run's real output, from the stored answers.

    python3 data/scripts/recheck_recovery_output.py --recovery runs/new_pipeline/swebench/recovery-2 \
        --traces data/swebench/traces/view-1/source/test --structure data/swebench/program/structure.json \
        --out runs/new_pipeline/swebench/recovery-2-patch

RedoAdamast's recovery pass (data/redo_adamast/code-1/recovery) verifies the reader's quotes about the
output against `final_output`: a harness block after the last turn, else the last turn's own output. On
SWE-bench the run's output -- the submitted patch -- is the environment message after the last turn, so
the check saw only the 100-character submit command and dropped every quote the reader took from the patch.
The reader's prompt did contain the patch; only the check was wrong.

This re-runs the same check (code-1's `recovery.check_point`, unchanged) on every point's stored
`recovery_raw` with the output set to that environment block, and writes a new run beside the old one
(append-only). No model call. Records without points, or not judged, are copied through unchanged. A
trace with no environment block after its last turn stops the script: the rule would not apply to it.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "data" / "redo_adamast" / "code-1"
sys.path.insert(0, str(CODE))
from recovery import goldfree, render, recovery   # noqa: E402  (code-1, unchanged)


def env_output(trace_text: str, turns: list) -> str | None:
    """The environment block after the last turn: on SWE-bench, the submitted patch."""
    tail = trace_text[trace_text.rfind(render.TURN_CLOSE.format(k=turns[-1]["turn"])):]
    i = tail.find(render.ENV)
    return tail[i + len(render.ENV):] if i >= 0 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recovery", type=Path, required=True)
    ap.add_argument("--traces", type=Path, required=True)
    ap.add_argument("--structure", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists; recovery runs are append-only")
    agents = list(json.loads(a.structure.read_text())["discovered_agents"]["agents"])
    recs = sorted((a.recovery / "traces").glob("*.json"))
    flips, dropped = collections.Counter(), collections.Counter()
    verdicts, copied = collections.Counter(), 0
    out_recs = []
    for f in recs:
        d = json.loads(f.read_text())
        if d.get("status") != "judged" or not d.get("points") or not d.get("recovery_calls"):
            out_recs.append((f.name, d)); copied += 1
            continue
        clean, _ = goldfree.strip(json.loads((a.traces / f.name).read_text()))
        text, turns = render.render_turns(clean, agents)
        blocks = {t["turn"]: recovery.split_turn(t["block"]) for t in turns}
        out_text = env_output(text, turns)
        if out_text is None:
            raise SystemExit(f"{d['trace_id']}: no environment block after the last turn; the rule does not apply")
        old_text = recovery.final_output(text, turns)
        pts = []
        for p in d["points"]:
            old = recovery.check_point(p["recovery_raw"], p, blocks, old_text)
            assert recovery.coarse(recovery.verdict_detail(old)) == p["recovery"], f"{d['trace_id']}: stored verdict not reproduced"
            kept = recovery.check_point(p["recovery_raw"], p, blocks, out_text)
            q = dict(p)
            q["recovery_detail"] = recovery.verdict_detail(kept)
            q["recovery"] = recovery.coarse(q["recovery_detail"])
            q["recovery_evidence"] = kept
            flips[(p["recovery"], q["recovery"])] += 1
            dropped["before"] += len(old["dropped"]); dropped["after"] += len(kept["dropped"])
            verdicts[q["recovery"]] += 1
            pts.append(q)
        e = dict(d, points=pts, final_output_chars=len(out_text),
                 recovery_summary=dict(collections.Counter(q["recovery"] for q in pts)),
                 rechecked={"from": str(a.recovery), "final_output": "environment block after the last turn",
                            "final_output_chars_before": len(old_text)})
        out_recs.append((f.name, e))
    (a.out / "traces").mkdir(parents=True)
    for name, d in out_recs:
        (a.out / "traces" / name).write_text(json.dumps(d, indent=1))
    s = json.loads((a.recovery / "summary.json").read_text()) if (a.recovery / "summary.json").exists() else {}
    s["rechecked"] = {"from": str(a.recovery), "script": "data/scripts/recheck_recovery_output.py",
                      "final_output": "environment block after the last turn (the submitted patch)",
                      "records": len(recs), "copied_through": copied,
                      "dropped_claims": dict(dropped),
                      "verdict_changes": {f"{o} -> {n}": c for (o, n), c in sorted(flips.items()) if o != n},
                      "verdicts": dict(verdicts)}
    (a.out / "summary.json").write_text(json.dumps(s, indent=2))
    print(json.dumps(s["rechecked"], indent=1))


if __name__ == "__main__":
    main()
