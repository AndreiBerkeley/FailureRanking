#!/usr/bin/env python3
"""Convert the traces the Stage-1/Stage-2 pipeline will run on, reusing the
generation trial's converter (explicit RETRIEVAL EVENT rendering).

Two sets:
  --set scored : the 600 scored-subset executions (repeat 0, tasks in the
                 50-task evaluation subset, all 12 candidates) — the traces
                 behind annotations_v3, re-annotated under the frozen
                 taxonomy by the upcoming re-judge.
  --set slice  : the 24 refinement-slice traces (dry-run set; SPEC.md
                 validation plan step 2). Gold quarantine untouched — only
                 traces/ is read, never gold_do_not_pass_to_judge/.
"""
import argparse
import json
import sys
from pathlib import Path

HOME = Path.home()
GEN_TRIAL = HOME / "Desktop/FailureRank/trials/2026-08-07-adamast-taxonomy-generation"
sys.path.insert(0, str(GEN_TRIAL))
from convert_traces import convert, RUN, SUBSET  # noqa: E402

SLICE = (HOME / "Desktop/FailureRank/data/legacy-hover-shakedown/"
         "grading/refinement_slice/traces")
GOLD_MARKER = "gold_do_not_pass_to_judge"


def emit(trace_files, out):
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in trace_files:
        assert GOLD_MARKER not in str(f), f"gold quarantine violated: {f}"
        t = json.loads(f.read_text())
        (out / f"{t['trace_id']}.json").write_text(json.dumps(convert(t), indent=1))
        n += 1
    print(f"wrote {n} converted traces to {out}")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["scored", "slice"], required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)

    if args.set == "slice":
        files = sorted(SLICE.glob("candidate_*/*.json"))
        assert len(files) == 24, len(files)
        emit(files, out)
        return

    scored = set(json.loads(SUBSET.read_text())["task_ids"])
    files = []
    for cdir in sorted((RUN / "evaluation/traces").glob("candidate_*")):
        picked = 0
        for f in sorted(cdir.glob("*.json")):
            t = json.loads(f.read_text())
            if (t["evaluation_repeat"] == 0
                    and t["task"]["source_id"] in scored):
                files.append(f)
                picked += 1
        assert picked == 50, (cdir.name, picked)
    n = emit(files, out)
    assert n == 600, n


if __name__ == "__main__":
    main()
