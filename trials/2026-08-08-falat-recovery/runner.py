#!/usr/bin/env python3
"""Stage-2 recovery runner (SPEC.md): occurrence enumeration + edge typing
via Bedrock, then deterministic verdicts via recovery_graph.

Modes:
  --build-only   construct and save every prompt, run quote localization
                 on the Stage-1 findings, NO API calls (free; verifies
                 plumbing end-to-end minus the model)
  (default)      one cached prior call + one edge call per trace (billed;
                 Andrei launches per hard rule 1)

Inputs:
  --traces   dir of converted traces (messages format)
  --stage1   adamast judge output JSON (mode=default) over those traces
  --out      output dir: per-trace stage2 JSONs + recovery.json summary

Output recovery.json rows feed the Phi harness:
  {candidate, task, mode -> fully_recovered|unrecovered}
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from recovery_graph import analyze, task_mode_recovery  # noqa: E402

MODEL_DEFAULT = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


# ---------------------------------------------------------------- trace prep

def numbered_steps(trace: dict) -> list[str]:
    return [f"[STEP {i}] ({m['role']}) {m['content']}"
            for i, m in enumerate(trace["messages"], start=1)]


def locate_quote(quote: str, trace: dict):
    """Return the 1-based step containing `quote` (exact, then fuzzy)."""
    norm = " ".join(quote.split()).lower()
    if not norm:
        return None
    contents = [" ".join(m["content"].split()).lower()
                for m in trace["messages"]]
    for i, c in enumerate(contents, start=1):
        if norm in c:
            return i
    # fuzzy fallback: best-matching step by longest common block coverage
    best, best_score = None, 0.0
    probe = norm[:300]
    for i, c in enumerate(contents, start=1):
        m = difflib.SequenceMatcher(None, probe, c).find_longest_match(
            0, len(probe), 0, len(c))
        score = m.size / max(1, len(probe))
        if score > best_score:
            best, best_score = i, score
    return best if best_score >= 0.6 else None


# ---------------------------------------------------------------- model I/O

def bedrock_call(prompt: str, model: str, region: str | None, max_tokens: int):
    import boto3
    kwargs = {"region_name": region} if region else {}
    client = boto3.client("bedrock-runtime", **kwargs)
    resp = client.converse(
        modelId=model,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens},
    )
    return resp["output"]["message"]["content"][0]["text"]


def parse_json(text: str):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start:text.rfind("}") + 1])


# ---------------------------------------------------------------- pipeline

def stage2_for_trace(trace, findings, prior_text, args, out_dir):
    tid = trace["trace_id"]
    steps = numbered_steps(trace)
    diagnostics = {"unlocated_findings": 0, "unverified_occurrences": 0}

    findings_block = []
    for f in findings:
        step = locate_quote(f.get("evidence", ""), trace)
        if step is None:
            diagnostics["unlocated_findings"] += 1
        findings_block.append(
            f"- code {f['code']} ({f.get('name', '')}), "
            f"anchored near step {step if step else 'UNKNOWN'}: "
            f"evidence: {f.get('evidence', '')[:400]}")

    prompt = (HERE / "prompts/edges.txt").read_text()
    prompt = (prompt.replace("{prior}", prior_text)
              .replace("{trace_steps}", "\n".join(steps))
              .replace("{findings}", "\n".join(findings_block) or "(none)"))
    (out_dir / f"{tid}.prompt.txt").write_text(prompt)

    if args.build_only:
        return {"trace_id": tid, "built": True, "diagnostics": diagnostics}

    payload = parse_json(bedrock_call(prompt, args.model, args.aws_region,
                                      args.max_output_tokens))
    occurrences, occ_modes = [], {}
    for o in payload.get("occurrences", []):
        step = locate_quote(o.get("quote", ""), trace)
        if step is None:
            diagnostics["unverified_occurrences"] += 1
            step = int(o.get("step", 0)) or 1
        occurrences.append({"id": o["id"], "step": step})
        occ_modes[o["id"]] = o["code"]
    edges = [{"src": e["src"],
              "dst": "OUTPUT" if e.get("dst") in ("OUT", "OUTPUT") else e["dst"],
              "label": e["label"],
              "consume_step": e.get("consume_step")}
             for e in payload.get("edges", [])
             if e.get("src") in occ_modes
             and (e.get("dst") in ("OUT", "OUTPUT") or e.get("dst") in occ_modes)]

    results = analyze(occurrences, edges)
    modes = task_mode_recovery(occ_modes, results)
    record = {"trace_id": tid,
              "candidate_index": trace["metadata"]["candidate_index"],
              "task_source_id": trace["metadata"]["task_source_id"],
              "occurrences": payload.get("occurrences", []),
              "edges": payload.get("edges", []),
              "statuses": {k: v for k, v in results.items() if k != "_summary"},
              "mode_recovery": modes,
              "diagnostics": {**diagnostics, **results["_summary"]}}
    (out_dir / f"{tid}.json").write_text(json.dumps(record, indent=1))
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", required=True)
    ap.add_argument("--stage1", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--aws-region", default=None)
    ap.add_argument("--max-output-tokens", type=int, default=4000)
    ap.add_argument("--build-only", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stage1 = json.loads(Path(args.stage1).read_text())
    by_trace = {d["trace_id"]: d.get("failure_modes") or []
                for d in stage1["diagnoses"]}

    prior_path = out_dir / "program_prior.json"
    if args.build_only:
        prior_text = "(prior placeholder — build-only mode)"
        (out_dir / "prior.prompt.txt").write_text(
            (HERE / "prompts/prior.txt").read_text())
    elif prior_path.exists():
        prior_text = prior_path.read_text()
    else:
        prior_text = bedrock_call((HERE / "prompts/prior.txt").read_text(),
                                  args.model, args.aws_region,
                                  args.max_output_tokens)
        prior_path.write_text(prior_text)

    records, skipped = [], 0
    for f in sorted(Path(args.traces).glob("*.json")):
        trace = json.loads(f.read_text())
        findings = by_trace.get(trace["trace_id"])
        if findings is None:
            skipped += 1
            continue
        records.append(stage2_for_trace(trace, findings, prior_text,
                                        args, out_dir))

    if not args.build_only:
        (out_dir / "recovery.json").write_text(json.dumps(
            {"records": records, "skipped_no_stage1": skipped}, indent=1))
    print(f"{'built prompts for' if args.build_only else 'processed'} "
          f"{len(records)} traces; skipped (no stage-1 entry): {skipped}")


if __name__ == "__main__":
    main()
