#!/usr/bin/env python3
"""The recovery pass: one call per trace over a finished judge run.

    python3 -m new_pipeline.recovery.run --traces <pool dir> --mapping <pointjudge run dir> \
        --out <dir> [--model openrouter/anthropic/claude-sonnet-5] [--workers 12] [--limit N] [--dry-run]

Reads each judged trace of the mapping, shows the recovery reader the trace and the
judge's failure points (codes hidden), and writes <out>/traces/<trace_id>.json: the
mapping's record with, on every point, `recovery` (the verdict) and `recovery_evidence`
(what the reader claimed, what was verified, what was dropped and why). The mapping is
never modified; a scoring path reads the recovery run and filters points by verdict.

Traces with no points are copied through with nothing to do (no call). Gold is stripped
at the boundary as the judge does. Resumable: a trace already `judged` is skipped;
failed ones are retried up to --max-attempts.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from new_pipeline import goldfree                              # noqa: E402
from new_pipeline.llm import llm_call, log                     # noqa: E402
from new_pipeline.pointjudge import judge, prompts as jprompts  # noqa: E402
from new_pipeline.recovery import prompts, recovery            # noqa: E402


def build_prompt(trace_text: str, points: list, program: str = "") -> str:
    """program: the program's success rule (jprompts.program_block), the same section the
    judge's passes see; empty when the structure declares none."""
    return prompts.RECOVERY.format(layout=jprompts.TURN_LAYOUT, program=program,
                                   points=recovery.render_points(points), trace=trace_text)


def recover_one(rec: dict, trace_path: Path, call, model, agents, attempts_before: int, program: str = "") -> dict:
    """The mapping record for one trace, with recovery on every point."""
    out = dict(rec)
    out["attempts"] = attempts_before + 1
    out["status"] = "failed"
    points = rec.get("points") or []
    if rec.get("status") != "judged":
        out["error"] = "mapping record is not judged"; return out
    if not points:
        out["status"] = "judged"; out["recovery_calls"] = 0
        out["recovery_summary"] = {"points": 0}
        return out

    raw = json.loads(trace_path.read_text())
    clean, _ = goldfree.strip(raw)
    trace_text, turns = judge.render_turns(clean, agents)
    if not turns:
        out["error"] = "trace renders with no agent turns"; return out
    turn_blocks = {t["turn"]: recovery.split_turn(t["block"]) for t in turns}
    out_text = recovery.final_output(trace_text, turns)

    prompt = build_prompt(trace_text, points, program)
    d = None; problem = "no answer"
    for attempt in range(2):
        text = prompt if attempt == 0 else (
            prompt + f"\n\nYour previous answer was rejected: {problem}. Return the full JSON again, correcting exactly that.")
        d = recovery.parse(call(text, model))
        problem = recovery.answer_ok(d, len(points)) if d is not None else "the response was not JSON"
        if problem is None:
            break
    if problem is not None:
        out["error"] = f"recovery reader: {problem}"; return out

    by_index = {e["index"]: e for e in d["points"]}
    new_points = []
    for i, p in enumerate(points):
        kept = recovery.check_point(by_index[i], p, turn_blocks, out_text)
        q = dict(p)
        q["recovery"] = recovery.verdict(kept)
        q["recovery_evidence"] = kept
        q["recovery_raw"] = by_index[i]          # the reader's answer as given, for re-derivation and audit
        new_points.append(q)
    out["points"] = new_points
    out["status"] = "judged"
    out["recovery_calls"] = 1
    out["final_output_chars"] = len(out_text)
    from collections import Counter
    out["recovery_summary"] = dict(Counter(q["recovery"] for q in new_points))
    out["error"] = None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--traces", type=Path, required=True, help="the pool the mapping was judged on")
    ap.add_argument("--mapping", type=Path, required=True, help="a pointjudge run dir (traces/*.json)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="openrouter/anthropic/claude-sonnet-5")
    ap.add_argument("--structure", type=Path, default=None, help="benchmark structure json (agent names)")
    ap.add_argument("--thinking", choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"], default="HIGH")
    ap.add_argument("--max-output", type=int, default=65536)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true", help="print the first prompt; spend nothing; write nothing")
    a = ap.parse_args()

    agents = None; program = ""
    if a.structure:
        structure = json.loads(a.structure.read_text())
        agents = list(structure["discovered_agents"]["agents"])
        program = jprompts.program_block(structure)      # the program's success rule, if declared
    log(f"  program success rule in view: {'yes' if program else 'no (structure declares none)'}")
    recs = sorted((a.mapping / "traces").glob("*.json"))
    if a.limit:
        recs = recs[:a.limit]
    if not recs:
        raise SystemExit(f"no records in {a.mapping}/traces")

    if a.dry_run:
        for f in recs:
            rec = json.loads(f.read_text())
            if rec.get("status") == "judged" and rec.get("points"):
                raw = json.loads((a.traces / f.name).read_text()); clean, _ = goldfree.strip(raw)
                tt, turns = judge.render_turns(clean, agents)
                print(f"trace {rec['trace_id']}: {len(rec['points'])} points, {len(turns)} turns, "
                      f"final output {len(recovery.final_output(tt, turns)):,} chars, prompt {len(build_prompt(tt, rec['points'], program)):,} chars\n")
                print(build_prompt(tt, rec["points"], program))
                break
        n_pts = sum(len(json.loads(f.read_text()).get("points") or []) for f in recs)
        n_call = sum(1 for f in recs if json.loads(f.read_text()).get("points"))
        print(f"\ndry run: {len(recs)} records, {n_call} would be called (one call each), {n_pts} points; nothing spent")
        return

    tdir = a.out / "traces"; tdir.mkdir(parents=True, exist_ok=True)

    def prior(f):
        p = tdir / f.name
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:                                      # noqa: BLE001
            return None

    pending = []
    for f in recs:
        pr = prior(f)
        if pr is None:
            pending.append((f, 0))
        elif pr.get("status") != "judged" and int(pr.get("attempts", 1)) < a.max_attempts:
            pending.append((f, int(pr.get("attempts", 1))))
    log(f"recovery: {len(recs)} records, {len(pending)} to do, {len(recs) - len(pending)} already done")
    call, model = llm_call(a.model, temperature=a.temperature, retries=5, max_output=a.max_output,
                           thinking=a.thinking, timeout=a.timeout)
    log(f"  reader {model} | thinking {a.thinking} | {a.workers} workers | one call per trace with points")
    t0, done = time.time(), 0

    def work(item):
        f, att = item
        rec = json.loads(f.read_text())
        try:
            r = recover_one(rec, a.traces / f.name, call, model, agents, att, program)
        except Exception as e:                                 # noqa: BLE001
            r = dict(rec); r.update({"status": "failed", "error": f"{type(e).__name__}: {e}", "attempts": att + 1})
        (tdir / f.name).write_text(json.dumps(r, indent=1))
        return r

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(work, it) for it in pending]
        for fu in as_completed(futs):
            r = fu.result(); done += 1
            if r["status"] != "judged":
                log(f"    [!] {r.get('trace_id')}: {r.get('error')}")
            if done % 25 == 0 or done == len(pending):
                log(f"  {done}/{len(pending)}  ({time.time() - t0:.0f}s)")

    results = [json.loads(p.read_text()) for p in sorted(tdir.glob("*.json"))]
    summary = {
        "mapping": str(a.mapping), "traces": str(a.traces), "model": model, "thinking": a.thinking,
        "success_rule_in_view": bool(program),
        "counts": {"total": len(results), "judged": sum(1 for r in results if r["status"] == "judged"),
                   "failed": sum(1 for r in results if r["status"] != "judged")},
        **recovery.summarise(results),
        "minutes": round((time.time() - t0) / 60, 1),
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2))
    log(f"recovery: judged {summary['counts']['judged']}/{len(results)}  failed {summary['counts']['failed']}  {summary['minutes']} min")
    log(f"  points {summary['points']}: {summary['verdicts']}  recovered {summary['recovered']}")
    log(f"  effect quotes {summary['effect_quotes']}  dropped claims {summary['dropped_claims']}")
    log(f"  -> {a.out}/summary.json, traces/")


if __name__ == "__main__":
    main()
