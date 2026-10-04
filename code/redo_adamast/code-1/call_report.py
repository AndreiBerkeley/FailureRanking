#!/usr/bin/env python3
"""Per-stage report of a run's model calls: replies kept, failed attempts by kind, and how close replies came
to the output limit. Shows where a run hit trouble, also after the fact.

    python generation/call_report.py <run dir> [<run dir> ...] [--variant NAME]

Sources, per run dir:
  call_log.jsonl        one line per attempt (runs made since 2026-09-27): finish reason, token counts, billed
                        cost as the provider reports it with each reply, requests that got no reply, warnings
  calls/<name>.json     every reply kept; "meta" holds the same fields for replies made since 2026-09-27
  calls/<name>.failed_attemptN.txt   every unparseable reply; for older runs its kind is read from the text

Kinds of failed attempt:
  no reply      the call returned nothing (timeouts, errors, retries exhausted)
  cut off       the reply stopped at the output limit (finish reason length / MAX_TOKENS, or, for older
                runs, JSON that ends before it closes)
  not JSON      text with no JSON object in it
  malformed     a closed JSON object that still does not parse
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

CUT = {"length", "MAX_TOKENS"}
NEAR = 0.8  # a kept reply that used this share of the output limit is listed


def stage_of(name: str) -> str:
    parts = name.split("_")
    words = []
    for t in parts[1:]:  # drop round, annotator, part and trace ids; keep the segment and the step
        if re.fullmatch(r"(r|a|c|p|g|b)\d+|[0-9a-f]{16,}|FM-\d+|[A-Z]+\d*|[a-z]+-\d+", t):
            continue
        words.append(t if t.startswith("seg") else re.sub(r"\d+$", "", t))
    return "_".join([parts[0]] + words) if words else parts[0]


def kind_of_text(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return "no reply"
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    if "{" not in s:
        return "not JSON"
    return "malformed" if s.rstrip().endswith("}") else "cut off"


def variants_of(run: Path) -> list[str]:
    return [p.stem[len("config_"):] for p in run.glob("config_*.json")]


def keep(name: str, variant: str, others: list[str]) -> bool:
    if variant:
        return name.endswith("_" + variant)
    return not any(name.endswith("_" + v) for v in others)


def billed(run: Path, variant: str = "") -> dict:
    """Totals over a run's call log: billed USD as the provider reported it, and what is not in it."""
    log = Path(run) / (f"call_log_{variant}.jsonl" if variant else "call_log.jsonl")
    lines = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    return {"billed_usd": round(sum(x.get("cost") or 0 for x in lines), 6),
            "attempts": len(lines),
            "attempts_without_cost": sum(1 for x in lines if x.get("cost") is None and x.get("reply_chars")),
            "requests_without_reply": sum(x.get("lost_responses") or 0 for x in lines),
            "input_tokens": sum(x.get("prompt_tokens") or 0 for x in lines),
            "output_tokens": sum(x.get("output_tokens") or 0 for x in lines),
            "note": "requests without a reply may have been billed; that charge is not in billed_usd"}


def report(run: Path, variant: str = "") -> str:
    run = Path(run)
    others = [v for v in variants_of(run) if v != variant]
    alloc = run / (f"allocation_{variant}.json" if variant else "allocation.json")
    tids = sorted({t for v in json.loads(alloc.read_text()).values() for t in v}, key=len, reverse=True) \
        if alloc.exists() else []

    def base(n):  # the call name without the variant and without trace ids
        n = n[:-len(variant) - 1] if variant else n
        for t in tids:
            n = n.replace("_" + t, "")
        return n
    cfg = run / (f"config_{variant}.json" if variant else "config.json")
    max_output = int(json.loads(cfg.read_text()).get("max_output", 0)) if cfg.exists() else 0

    ok = defaultdict(int)
    largest = defaultdict(int)
    used = defaultdict(lambda: (0, 0))  # stage -> (max output tokens, max_output they were made under)
    near = []
    for p in sorted((run / "calls").glob("*.json")):
        if not keep(p.stem, variant, others):
            continue
        c = json.loads(p.read_text())
        st = stage_of(base(p.stem))
        ok[st] += 1
        largest[st] = max(largest[st], len(c.get("raw") or ""))
        m = c.get("meta") or {}
        if m.get("output_tokens"):
            if m["output_tokens"] > used[st][0]:
                used[st] = (m["output_tokens"], max_output)
            if max_output and m["output_tokens"] >= NEAR * max_output:
                near.append(f"{p.stem}: {m['output_tokens']:,} of {max_output:,} output tokens")

    failed = {}  # (name, attempt) -> (kind, chars, when)
    for p in sorted((run / "calls").glob("*.failed_attempt*.txt")):
        name, att = p.name.split(".failed_attempt")
        if keep(name, variant, others):
            text = p.read_text()
            failed[name, int(att[:-4])] = (kind_of_text(text), len(text), "")
    log = run / (f"call_log_{variant}.jsonl" if variant else "call_log.jsonl")
    cost = defaultdict(float)  # stage -> USD billed, as the provider reported it, over every logged attempt
    unpriced = 0               # logged attempts that got a reply but carry no billed cost (logged before cost was)
    lost = 0                   # requests sent that got no reply (timeout, dropped connection): any charge is unknown
    tokens = [0, 0]            # input, output (thinking included) over every logged attempt
    if log.exists():
        for line in map(json.loads, log.read_text().splitlines()):
            st_ = stage_of(base(line["call"]))
            tokens[0] += line.get("prompt_tokens") or 0
            tokens[1] += line.get("output_tokens") or 0
            lost += line.get("lost_responses") or 0
            if line.get("cost") is not None:
                cost[st_] += line["cost"]
            elif line.get("reply_chars"):
                unpriced += 1
            if not line["ok"]:  # the finish reason is authoritative; otherwise the kind read from the saved text
                key = (line["call"], line["attempt"])
                k = "cut off" if line.get("finish_reason") in CUT else \
                    "no reply" if not line["reply_chars"] else failed.get(key, ("malformed",))[0]
                failed[key] = (k, line["reply_chars"], line["time"])
            m_out, cap = line.get("output_tokens"), line.get("max_output") or max_output
            if line["ok"] and m_out and m_out >= used[st_][0]:
                used[st_] = (m_out, cap)
            if line["ok"] and m_out and cap and m_out >= NEAR * cap:
                x = f"{line['call']}: {m_out:,} of {cap:,} output tokens"
                if x not in near:
                    near.append(x)

    kinds = ["no reply", "cut off", "not JSON", "malformed"]
    fails = defaultdict(lambda: defaultdict(int))
    for (name, _), (k, _, _) in failed.items():
        fails[stage_of(base(name))][k] += 1
    stages = sorted(set(ok) | set(fails))
    shown = [k for k in kinds if any(fails[s][k] for s in stages)]
    head = f"{'stage':22s} {'kept':>5s} " + " ".join(f"{k:>11s}" for k in shown) + f" {'largest reply':>15s} {'max output used':>24s} {'cost':>10s}"
    rows = [f"calls of {run}" + (f" (variant {variant})" if variant else ""), head]
    for s in stages:
        u, cap = used[s]
        out = f"{u:,} / {cap:,} ({u / cap:.0%})" if u and cap else "not recorded"
        c = f"${cost[s]:,.2f}" if s in cost else "-"
        rows.append(f"{s:22s} {ok[s]:5d} " + " ".join(f"{fails[s][k]:11d}" for k in shown)
                    + f" {largest[s]:>9,d} chars {out:>24s} {c:>10s}")
    if cost:
        rows.append(f"billed: ${sum(cost.values()):,.4f} over every logged attempt, as the provider reported it per reply "
                    f"({tokens[0]:,} input and {tokens[1]:,} output tokens, thinking included)")
    if unpriced:
        rows.append(f"cost not recorded for {unpriced} logged attempts (made before cost was logged); not included")
    if lost:
        rows.append(f"{lost} requests got no reply (timeout or dropped connection); if the provider billed them, "
                    f"that is not included")
    if not log.exists():
        rows.append("cost: not recorded (no call log; runs before 2026-09-27)")
    if failed:
        rows.append("failed attempts:")
        for (name, att), (k, chars, when) in sorted(failed.items()):
            rows.append(f"  {name} attempt {att}: {k}, {chars:,} chars" + (f", {when}" if when else "")
                        + ("  (kept on a later attempt)" if (run / "calls" / f"{name}.json").exists() else ""))
    if near:
        rows.append(f"kept replies at {NEAR:.0%} or more of the output limit:")
        rows += [f"  {x}" for x in near]
    if not failed and not near:
        rows.append("no failed attempts; no kept reply near the output limit")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--variant", default="")
    a = ap.parse_args()
    print("\n\n".join(report(r, a.variant) for r in a.runs))


if __name__ == "__main__":
    main()
