#!/usr/bin/env python3
"""Map human failure labels onto a taxonomy: does each failure a human marked fit one of its modes?

    python map_labels.py --taxonomy <taxonomy.json> --labels <labels.json> --out <dir> --model <provider/model> \
        [--as-given] [--judge <judge dir>] [--workers W] [--dry-run]

--labels is a list of items, one per human label:
    {"id", "trace_id", "step", "task",
     "step_before": {"step", "agent", "text"} or null, "marked_step": {"step", "agent", "text"},
     "annotator": {"agent", "reason"}, "messages": [message indexes of the marked step] (optional)}
One call per item, W in parallel. The model checks the annotator's reason against the step text and answers
AGENT (a wrong action by the agent at that step) with the one mode that fits, or NONE with what kind of failure
it is; or NOT_AGENT (only a tool or environment problem, or only an outcome).
With --as-given every label is taken as a failure, as the annotator says; the model only gives the mode that
fits, or NONE with what kind of failure it is (prompt map_labels_given.md).

With --judge (a judge.py output dir on the same traces), each item also gets the modes the judge gave at the
marked step (its points whose message is one of the item's "messages", or whose turn is its "step" when the item
has no "messages"), and the summary counts how often the two agree.

Written:
    <out>/labels_mapped.json   each item: its label, the verdict, mode, what went wrong, why; judge modes at the step
    <out>/summary.json         verdict counts, coverage (share of failures with a mode: AGENT items, or every
                               item with --as-given), items per mode,
                               the NONE items, and agreement with the judge
Rerunning the same command replays saved replies.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import run as gen  # model calls, caching, JSON helpers

MAP = (gen.PROMPTS / "map_labels.md").read_text().strip()
MAP_GIVEN = (gen.PROMPTS / "map_labels_given.md").read_text().strip()  # --as-given: every label is a failure
SHOWN = ("id", "task", "step_before", "marked_step", "annotator")


def build(taxonomy_text: str, item: dict, given: bool = False) -> str:
    return gen.SEP.join([gen.CONCEPTS, (MAP_GIVEN if given else MAP).replace("{taxonomy}", taxonomy_text)
                         .replace("{item}", gen.dump({k: item.get(k) for k in SHOWN}))])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--judge", type=Path, default=None, help="optional judge.py output dir on the same traces")
    ap.add_argument("--as-given", action="store_true",
                    help="take every label as a failure; only ask which mode fits, or NONE")
    ap.add_argument("--workers", type=int, default=6, help="W: calls in parallel")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--context-tokens", type=int, default=1_000_000)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-output", type=int, default=32768)
    ap.add_argument("--price-in", type=float, default=None, help="USD per million input tokens, for the estimate")
    a = ap.parse_args()
    if not a.dry_run and not a.model:
        raise SystemExit("--model is required unless --dry-run")
    a.prompt_chars = (a.context_tokens - a.max_output) * 3

    tax = json.loads(a.taxonomy.read_text())
    tax = list(tax["taxonomy"] if isinstance(tax, dict) else tax)
    ids = {m["id"] for m in tax}
    tax_text = gen.dump(gen.slim(tax))
    items = json.loads(a.labels.read_text())
    gen.log(f"{len(items)} labels from {a.labels}; {len(tax)} modes from {a.taxonomy}; model {a.model}; "
            f"{'DRY RUN' if a.dry_run else 'LIVE'}")

    r = gen.Runner(a)

    def one(item):
        try:
            return r.ask(f"map_{item['id']}", "map", build(tax_text, item, a.as_given))
        except SystemExit as e:
            return {"_error": str(e)}

    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        replies = list(ex.map(one, items))

    if not a.dry_run:
        out = []
        for item, res in zip(items, replies):
            res = res or {}
            verdict = "GIVEN" if a.as_given else str(res.get("verdict") or "").strip().upper()
            mode = gen.norm_mode(res.get("mode")) if verdict in ("AGENT", "GIVEN") and "_error" not in res else None
            rec = {"id": item["id"], "trace_id": item["trace_id"], "step": item["step"],
                   "agent": item["marked_step"]["agent"], "reason": item["annotator"]["reason"],
                   "error": res.get("_error"), "verdict": verdict or None,
                   "mode": mode if mode in ids or mode == "NONE" else None,
                   "unknown_mode": mode if mode and mode not in ids and mode != "NONE" else None,
                   "none_fits": res.get("none_fits") if mode == "NONE" else None,
                   "what_went_wrong": res.get("what_went_wrong"), "why": res.get("why")}
            if a.judge:
                f = a.judge / "traces" / f"{item['trace_id']}.json"
                pts = json.loads(f.read_text())["points"] if f.exists() else []
                at = (lambda p: p["message"] in item["messages"]) if item.get("messages") else \
                    (lambda p: p["turn"] == item["step"])
                rec["judge_modes_at_step"] = [(p["codes"] or ["NONE"])[0] for p in pts if at(p)]
            out.append(rec)

        agent = [x for x in out if x["verdict"] in ("AGENT", "GIVEN") and x["mode"]]  # an unknown mode id is left out, listed below
        none = [x for x in agent if x["mode"] == "NONE"]
        summary = {
            "taxonomy": str(a.taxonomy), "labels": str(a.labels), "model": a.model, "as_given": a.as_given,
            "items": len(out),
            "failed": [x["id"] for x in out if x["error"]],
            "verdicts": dict(Counter(x["verdict"] for x in out)),
            "coverage": round(1 - len(none) / len(agent), 3) if agent else None,
            "items_per_mode": dict(Counter(x["mode"] for x in agent).most_common()),
            "unknown_mode_ids": [x["id"] for x in out if x["unknown_mode"]],
            "none": [{k: x[k] for k in ("id", "step", "agent", "reason", "what_went_wrong", "none_fits")} for x in none]}
        if a.judge:
            flagged = [x for x in out if x["judge_modes_at_step"]]
            summary["judge"] = {"dir": str(a.judge), "flagged_marked_step": len(flagged),
                                "same_mode": sum(x["mode"] in x["judge_modes_at_step"] for x in flagged),
                                "flagged_but_not_agent": sum(x["verdict"] == "NOT_AGENT" for x in flagged)}
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "labels_mapped.json").write_text(gen.dump(out))
        from call_report import billed, report as call_report
        summary["cost"] = billed(a.out)
        (a.out / "summary.json").write_text(gen.dump(summary))
        (a.out / "call_report.txt").write_text(call_report(a.out) + "\n")
        gen.log(f"{summary['verdicts']}; coverage of failures {summary['coverage']}; {len(none)} NONE; "
                f"{len(summary['failed'])} failed" + (f"; judge {summary['judge']}" if a.judge else ""))

    total = sum(s["input_tokens_est"] for s in r.stats.values())
    line = f"{sum(s['calls'] for s in r.stats.values())} calls, about {total:,} input tokens"
    if a.price_in:
        line += f"; input cost at ${a.price_in}/M: ${total / 1e6 * a.price_in:,.2f} (output not included)"
    print(line)


if __name__ == "__main__":
    main()
