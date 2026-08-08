#!/usr/bin/env python3
"""Convert legacy HoVer run-export traces into AdaMAST-acceptable trace files
for taxonomy regeneration (`adamast generate`).

Trial: trials/2026-08-07-adamast-taxonomy-regen (see README.md).

Sampling (deterministic, no RNG): for each of the 12 candidates, the first
N_PER_CANDIDATE tasks in sorted source_id order among held-out tasks NOT in
the 50-task scored subset, repeat 0 only. Freeze discipline: the taxonomy is
generated only from traces of tasks that Φ never scores.

Output: one JSON per trace with top-level `trace_id` and `messages`
(role/content), which `adamast validate` accepts.
"""
import argparse
import json
from pathlib import Path

RUN = Path.home() / "Desktop/GEPA_Experiments/runs/plain_gepa_hover_seed0_20260804T003430Z"
SUBSET = (Path.home() / "Desktop/FailureRank/data/legacy-hover-shakedown/"
          "grading/evaluation_subset.json")
N_PER_CANDIDATE = 5


def _retrieval_event(pred: dict, hop: int) -> dict:
    docs = pred.get(f"hop{hop}_docs") or []
    return {
        "role": "user",
        "content": (f"RETRIEVAL EVENT — hop {hop} of 3 executed. "
                    f"{len(docs)} documents returned:\n"
                    + "\n".join(str(t) for t in docs)),
    }


def convert(trace: dict) -> dict:
    """Render the trace with each hop's retrieval as an EXPLICIT event
    message, so judges can count retrieval executions directly instead of
    inferring them from passage text embedded in later prompts (the
    implicit rendering caused inconsistent hop counting — see README)."""
    pred = trace.get("prediction", {})
    messages = [{
        "role": "user",
        "content": ("Task: three-hop HoVer retrieval over Wikipedia abstracts. "
                    "Perform exactly three retrievals and return everything "
                    f"retrieved.\nClaim to verify: {trace['input']['claim']}"),
    }, _retrieval_event(pred, 1)]
    # lm_calls order: summarize1, create_query_hop2, summarize2, create_query_hop3
    for i, call in enumerate(trace["lm_calls"]):
        for m in call.get("messages") or []:
            messages.append({"role": m.get("role", "user"),
                             "content": str(m.get("content", ""))})
        out = call.get("outputs")
        text = "\n".join(str(o) for o in out) if isinstance(out, list) else str(
            out if out is not None else call.get("response", ""))
        messages.append({"role": "assistant", "content": text})
        if i == 1:
            messages.append(_retrieval_event(pred, 2))
        elif i == 3:
            messages.append(_retrieval_event(pred, 3))
    messages.append({
        "role": "assistant",
        "content": ("FINAL OUTPUT — concatenation of all retrieved documents:\n"
                    + "\n".join(str(t) for t in pred.get("retrieved_docs", []))),
    })
    return {"trace_id": trace["trace_id"], "messages": messages,
            "metadata": {"candidate_index": trace["candidate_index"],
                         "task_source_id": trace["task"]["source_id"],
                         "evaluation_repeat": trace["evaluation_repeat"],
                         "origin": str(RUN)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-candidate", type=int, default=N_PER_CANDIDATE)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    scored = set(json.loads(SUBSET.read_text())["task_ids"])

    written = 0
    for cdir in sorted((RUN / "evaluation/traces").glob("candidate_*")):
        picked = 0
        # sort by task source_id for determinism; repeat 0 only, non-scored only
        entries = []
        for f in cdir.glob("*.json"):
            t = json.loads(f.read_text())
            if t["evaluation_repeat"] != 0 or t["task"]["source_id"] in scored:
                continue
            entries.append((t["task"]["source_id"], t))
        for _, t in sorted(entries)[: args.per_candidate]:
            (out / f"{t['trace_id']}.json").write_text(
                json.dumps(convert(t), indent=1))
            written += 1
            picked += 1
        assert picked == args.per_candidate, (cdir.name, picked)
    print(f"wrote {written} converted traces to {out}")


if __name__ == "__main__":
    main()
