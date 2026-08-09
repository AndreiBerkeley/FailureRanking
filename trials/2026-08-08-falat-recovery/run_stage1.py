#!/usr/bin/env python3
"""Stage-1 driver: run `adamast judge` one trace at a time.

The AdaMAST CLI buffers every diagnosis and writes a single file at the
end, so a 600-trace run is silent for ~3h and loses everything if it
dies. This driver shards it per trace, which gives:
  * per-trace progress with elapsed/ETA,
  * resumability — re-running skips traces already judged,
  * failure isolation — one bad trace does not end the run.
CLI startup is ~0.07s, so sharding costs well under a minute overall.

Outputs per-trace parts, then merges them into one file in the same
schema `runner.py` consumes.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ADAMAST = str(Path.home() / ".local/share/uv/tools/adamast/bin/adamast")
MODEL_DEFAULT = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def judged_ok(part: Path) -> bool:
    try:
        d = json.loads(part.read_text())
        return bool(d.get("diagnoses"))
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", required=True)
    ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--parts", required=True, help="per-trace output dir")
    ap.add_argument("--merged", required=True, help="combined stage-1 json")
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--max-trace-chars", type=int, default=40000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    parts = Path(args.parts)
    parts.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(args.traces).glob("*.json"))
    if not files:
        raise SystemExit(f"no traces in {args.traces}")

    todo = [f for f in files if not judged_ok(parts / f.name)]
    done_already = len(files) - len(todo)
    print(f"{len(files)} traces | already judged: {done_already} | to run: {len(todo)}",
          flush=True)
    if args.dry_run:
        print("dry run: no API calls made")
        return

    t0 = time.time()
    failures = []
    for i, f in enumerate(todo, start=1):
        part = parts / f.name
        cmd = [ADAMAST, "judge", "--taxonomy", args.taxonomy,
               "--traces", str(f), "--output", str(part),
               "--mode", "default", "--max-trace-chars", str(args.max_trace_chars),
               "--provider", "bedrock", "--model", args.model]
        r = subprocess.run(cmd, capture_output=True, text=True)
        el = time.time() - t0
        eta = (el / i) * (len(todo) - i)
        done = done_already + i
        if r.returncode == 0 and judged_ok(part):
            d = json.loads(part.read_text())
            nfm = len(d["diagnoses"][0].get("failure_modes") or [])
            print(f"[{done}/{len(files)}] {f.stem[:12]} ok  {nfm} findings  "
                  f"elapsed {el/60:.0f}m  eta {eta/60:.0f}m", flush=True)
        else:
            err = (r.stderr or r.stdout or "no output").strip().splitlines()
            failures.append({"trace": f.stem, "error": err[-1][:200] if err else "?"})
            print(f"[{done}/{len(files)}] {f.stem[:12]} FAILED: "
                  f"{failures[-1]['error']}", flush=True)

    # merge every available part into the schema runner.py expects
    diagnoses, meta = [], None
    for f in files:
        part = parts / f.name
        if judged_ok(part):
            d = json.loads(part.read_text())
            meta = meta or d
            diagnoses.extend(d["diagnoses"])
    merged = {"schema_version": 2, "mode": "default",
              "taxonomy": str(Path(args.taxonomy).resolve()),
              "judge": (meta or {}).get("judge", {}),
              "trace_count": len(diagnoses), "diagnoses": diagnoses,
              "failures": failures}
    Path(args.merged).write_text(json.dumps(merged, indent=1))
    print(f"\nmerged {len(diagnoses)}/{len(files)} traces -> {args.merged}; "
          f"failed {len(failures)}")
    if len(diagnoses) < len(files):
        print("re-run the same command to retry the missing traces "
              "(finished traces are skipped)")
        sys.exit(1)


if __name__ == "__main__":
    main()
