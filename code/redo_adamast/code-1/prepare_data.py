#!/usr/bin/env python3
"""Export one model's traces from data/<benchmark>/traces/, plus a random sample for generation.

    python generation/prepare_data.py --benchmark swebench --model swe-gpt-5-mini --fraction 0.05 --seed 0

Writes data/<benchmark>/<model>/
  corpus/<trace_id>.json   every trace of that model (judge view only, no outcomes)
  sample/<trace_id>.json   the random sample used for generation
  manifest.json            source, counts, seed, sampled trace ids
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data"
OUTCOME_KEYS = {"score", "resolved", "outcome", "reward", "gold", "passed"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--model", required=True, help="candidate id, e.g. swe-gpt-5-mini")
    ap.add_argument("--fraction", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--validation", type=int, default=5, help="unseen traces for the final validation round")
    a = ap.parse_args()

    src = OUT / a.benchmark / "traces" / f"{a.model}.jsonl.gz"
    rows = [json.loads(l) for l in gzip.open(src, "rt")]
    for r in rows:
        bad = OUTCOME_KEYS & set(r["judge_view"])
        if bad:
            raise SystemExit(f"trace {r['trace_id']} carries outcome keys {bad}; refusing to export")

    out = OUT / a.benchmark / a.model
    (out / "corpus").mkdir(parents=True, exist_ok=True)
    (out / "sample").mkdir(parents=True, exist_ok=True)
    for r in rows:
        keep = {"trace_id": r["trace_id"], "task_id": r["task_id"], "messages": r["judge_view"]["messages"]}
        (out / "corpus" / f"{r['trace_id']}.json").write_text(json.dumps(keep))

    k = max(1, round(a.fraction * len(rows)))
    sample = sorted(random.Random(a.seed).sample(rows, k), key=lambda r: r["trace_id"])
    picked = {r["trace_id"] for r in sample}
    held = sorted(random.Random(a.seed + 1).sample([r for r in rows if r["trace_id"] not in picked], a.validation),
                  key=lambda r: r["trace_id"])
    (out / "validation").mkdir(parents=True, exist_ok=True)
    for r in held:
        (out / "validation" / f"{r['trace_id']}.json").write_text(
            (out / "corpus" / f"{r['trace_id']}.json").read_text())
    for r in sample:
        (out / "sample" / f"{r['trace_id']}.json").write_text(
            (out / "corpus" / f"{r['trace_id']}.json").read_text())

    manifest = {"benchmark": a.benchmark, "model": a.model, "source": str(src),
                "corpus_traces": len(rows), "corpus_tasks": len({r["task_id"] for r in rows}),
                "fraction": a.fraction, "seed": a.seed, "sample_traces": k,
                "sample": [{"trace_id": r["trace_id"], "task_id": r["task_id"]} for r in sample],
                "validation": [{"trace_id": r["trace_id"], "task_id": r["task_id"]} for r in held],
                "note": "Judge view only. Outcomes were not copied."}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"{a.benchmark}/{a.model}: corpus {len(rows)} traces, sample {k} -> {out}")


if __name__ == "__main__":
    main()
