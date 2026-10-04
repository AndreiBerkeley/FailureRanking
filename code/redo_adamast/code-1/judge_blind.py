#!/usr/bin/env python3
"""Two-pass test of a taxonomy: find failures without it, then check each one and give it a mode.

    python judge_blind.py --run <taxonomy run dir> --traces <dir of trace files> --out <dir> \
        --model <provider/model> [--taxonomy <file>] [--workers W] [--limit N] [--dry-run]

Per trace, two calls:
  1. find     the failure definition, "what correct work looks like" (the run's field analysis) and the trace;
              no taxonomy. The same prompt generation uses for observation (02_observation.md): every failure
              instance, with the quoted span and a line on what went wrong.
  2. verify   the failure definition and mode rules, the taxonomy (no instances), the trace and the candidates of
              call 1: for each, is it a failure, and if so its mode, or NONE with what kind of failure it is
              (judge_verify.md).
A trace too long for one call is split into parts as in run.py; each part gets both calls.
Traces go through one continuous pool of W workers. Every reply is cached, so a rerun continues where it stopped.

Writes:
  <out>/traces/<trace file name>   the candidates, each with its verdict and mode; and, apart ("missed_by_find"),
                                   failures call 2 saw that no candidate describes, each with its mode
  <out>/summary.json               found, confirmed, rejected; coverage = share of confirmed failures with a mode;
                                   NONE list; failures per mode; modes never used; billed cost
  <out>/call_report.txt, call_log.jsonl   calls and billed cost (see call_report.py)
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
from collections import Counter
from pathlib import Path

import run as gen

VERIFY = (gen.PROMPTS / "judge_verify.md").read_text().strip()


def verify_prompt(tax_text: str, part_text: str, failures: list) -> str:
    body = VERIFY.replace("{taxonomy}", tax_text).replace("{traces}", part_text).replace("{failures}", gen.dump(failures))
    return gen.SEP.join([gen.CONCEPTS, gen.RULES, body])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True, help="the taxonomy run dir (for 01_field_analysis.json)")
    ap.add_argument("--taxonomy", type=Path, default=None, help="default: <run>/final_taxonomy.json")
    ap.add_argument("--traces", type=Path, required=True, help="dir with one JSON file per trace")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--workers", type=int, default=6, help="W: traces in flight at once")
    ap.add_argument("--limit", type=int, default=None, help="first N traces")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--context-tokens", type=int, default=1_000_000)
    ap.add_argument("--reserve-chars", type=int, default=200_000)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-output", type=int, default=32768)
    a = ap.parse_args()
    if not a.dry_run and not a.model:
        raise SystemExit("--model is required unless --dry-run")
    a.prompt_chars = (a.context_tokens - a.max_output) * 3
    budget = a.prompt_chars - a.reserve_chars

    tax_file = a.taxonomy or a.run / "final_taxonomy.json"
    tax = json.loads(tax_file.read_text())
    tax = list(tax["taxonomy"] if isinstance(tax, dict) else tax)
    tax_text, ids = gen.dump(gen.slim(tax)), {m["id"] for m in tax}
    fa_text = gen.dump(json.loads((a.run / "01_field_analysis.json").read_text()))
    files = sorted(a.traces.glob("*.json"))[: a.limit]
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "traces").mkdir(exist_ok=True)
    gen.log(f"two-pass test of {tax_file} ({len(tax)} modes) on {len(files)} traces from {a.traces}, "
            f"{a.workers} workers; model {a.model}; {'DRY RUN' if a.dry_run else 'LIVE'}")
    r = gen.Runner(a)

    def one(f):
        """Both calls for one trace (every part); returns its record, or None on a dry run."""
        t = json.loads(f.read_text())
        text = gen.render(t)
        cands, missed, errors = [], [], []
        for u in gen.split_trace(t, budget):
            try:
                res = r.ask(f"find_{gen.ukey(u)}", "find",
                            gen.build("02_observation", field_analysis=fa_text, traces=gen.block([u])))
            except SystemExit as e:
                errors.append(str(e))
                continue
            found = [x for tr in (res or {}).get("traces", []) for x in tr.get("instances", [])]
            if a.dry_run:  # stand-in candidates, to size the verify call
                found = [{"step": "x", "quote": "x" * 120, "missing": None, "what_went_wrong": "x" * 150,
                          "should_have": "x" * 100}] * 10
            part = [{"failure_id": f"F{len(cands) + i + 1}",
                     **{k: x.get(k) for k in ("step", "quote", "missing", "what_went_wrong", "should_have")}}
                    for i, x in enumerate(found)]
            if not part:
                continue
            try:
                ver = r.ask(f"verify_{gen.ukey(u)}", "verify", verify_prompt(tax_text, gen.block([u]), part))
            except SystemExit as e:
                errors.append(str(e))
                ver = None
            by_id = {v.get("failure_id"): v for v in (ver or {}).get("verdicts", []) if isinstance(v, dict)}
            for c in part:
                v = by_id.get(c["failure_id"])
                mode = gen.norm_mode(v.get("mode")) if v and v.get("is_failure") else None
                c.update(part_no=u["part"],
                         quote_valid=c["quote"] is None or gen.canon(c["quote"]) in gen.canon(text),
                         verdict=None if v is None else ("failure" if v.get("is_failure") else "not a failure"),
                         why=v.get("why") if v else None, mode=mode,
                         mode_known=mode is None or mode == "NONE" or mode in ids,
                         none_fits=v.get("none_fits") if mode == "NONE" else None)
            cands += part
            for x in (ver or {}).get("missed") or []:  # failures call 2 saw that no candidate describes: kept apart
                if not isinstance(x, dict):
                    continue
                mode = gen.norm_mode(x.get("mode"))
                missed.append({"missed_id": f"M{len(missed) + 1}", "part_no": u["part"],
                               **{k: x.get(k) for k in ("quote", "missing", "what_went_wrong")},
                               "quote_valid": x.get("quote") is None or gen.canon(x.get("quote")) in gen.canon(text),
                               "mode": mode, "mode_known": mode == "NONE" or mode in ids,
                               "none_fits": x.get("none_fits") if mode == "NONE" else None})
        if a.dry_run:
            return None
        rec = {"trace_id": t["trace_id"], "task_id": t.get("task_id"),
               "status": "failed" if errors else "judged", "error": "; ".join(errors) or None, "candidates": cands,
               "missed_by_find": missed}
        (a.out / "traces" / f.name).write_text(gen.dump(rec))
        return rec

    recs, done = [], 0
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for fut in cf.as_completed([ex.submit(one, f) for f in files]):
            rec = fut.result()
            done += 1
            if rec:
                recs.append(rec)
                if done % 25 == 0 or done == len(files):
                    gen.log(f"{done}/{len(files)} traces tested; {sum(x['status'] == 'failed' for x in recs)} failed")

    if not a.dry_run:
        cands = [c for x in recs for c in x["candidates"]]
        confirmed = [c for c in cands if c["verdict"] == "failure"]
        fitted = [c for c in confirmed if c["mode"] not in (None, "NONE") and c["mode_known"]]
        none = [c for c in confirmed if c["mode"] == "NONE"]
        per_mode = Counter(c["mode"] for c in fitted)
        from call_report import billed, report as call_report
        summary = {
            "taxonomy": str(tax_file), "field_analysis": str(a.run / "01_field_analysis.json"),
            "traces_dir": str(a.traces), "model": a.model, "workers": a.workers,
            "test": "two calls per trace: find failures without the taxonomy (02_observation.md), then verify each and "
                    "give it a mode or NONE (judge_verify.md)",
            "traces": len(recs), "failed": [x["trace_id"] for x in recs if x["status"] == "failed"],
            "found": len(cands), "confirmed": len(confirmed),
            "not_a_failure": sum(c["verdict"] == "not a failure" for c in cands),
            "no_verdict": sum(c["verdict"] is None for c in cands),
            "coverage": round(len(fitted) / len(confirmed), 4) if confirmed else None,
            "none": len(none),
            "unknown_mode_ids": sum(c["verdict"] == "failure" and not c["mode_known"] for c in cands),
            "quotes_not_verbatim": sum(not c["quote_valid"] for c in cands),
            "failures_per_mode": dict(per_mode.most_common()),
            "modes_never_used": sorted(ids - set(per_mode)),
            "possible_modes": {m["id"]: per_mode.get(m["id"], 0) for m in tax if m.get("gap") == "possible"},
            "missed_by_find": {  # found by call 2 only; not in found / confirmed / coverage above
                "count": sum(len(x["missed_by_find"]) for x in recs),
                "with_mode": sum(m["mode"] != "NONE" and m["mode_known"] for x in recs for m in x["missed_by_find"]),
                "none": sum(m["mode"] == "NONE" for x in recs for m in x["missed_by_find"]),
                "failures_per_mode": dict(Counter(m["mode"] for x in recs for m in x["missed_by_find"]
                                                  if m["mode"] != "NONE" and m["mode_known"]).most_common()),
                "none_list": [{"trace_id": x["trace_id"], "missed_id": m["missed_id"], "what_went_wrong": m["what_went_wrong"],
                               "none_fits": m["none_fits"]} for x in recs for m in x["missed_by_find"] if m["mode"] == "NONE"]},
            "none_list": [{"trace_id": x["trace_id"], "failure_id": c["failure_id"], "what_went_wrong": c["what_went_wrong"],
                           "none_fits": c["none_fits"]} for x in recs for c in x["candidates"] if c["verdict"] == "failure" and c["mode"] == "NONE"],
        }
        summary["cost"] = billed(a.out)
        (a.out / "summary.json").write_text(gen.dump(summary))
        (a.out / "call_report.txt").write_text(call_report(a.out) + "\n")
        gen.log(f"{len(recs)} traces; {len(cands)} found, {len(confirmed)} confirmed, {summary['not_a_failure']} not "
                f"failures; coverage {summary['coverage']}; {len(none)} NONE; billed ${summary['cost']['billed_usd']:.2f}")

    total = sum(s["input_tokens_est"] for s in r.stats.values())
    print(f"{sum(s['calls'] for s in r.stats.values())} calls, about {total:,} input tokens"
          + (" (verify calls sized with 10 stand-in candidates per trace)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
