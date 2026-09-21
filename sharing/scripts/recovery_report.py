#!/usr/bin/env python3
"""One Markdown report per experiment on what the recovery reader did with the judge's points.

    python3 sharing/scripts/recovery_report.py --recovery <recovery run> --taxonomy <taxonomy.json>
        --pool <judged pool dir> --title "..." --out sharing/<name>_recovery.md [--names <candidate set json>] [--note "..."]

Reads the recovery run's traces/*.json (each judged point carries its verdict), counts verdicts
in total, per candidate and per failure mode, and reports points and modes per trace before and
after the recovered points are removed. No model call; no gold.
"""
from __future__ import annotations
import argparse, json, glob, collections
from pathlib import Path

RECOVERED = ("corrected", "contained", "made_irrelevant")
ORDER = ["corrected", "contained", "made_irrelevant", "unrecovered", "unassessable"]
MEANING = {
    "corrected": "a later step fixed the wrong thing itself (the missing item was obtained, the wrong value replaced)",
    "contained": "the wrong thing stayed wrong but never reached what the output is scored on",
    "made_irrelevant": "a later step made the point moot (a different route obtained what was needed)",
    "unrecovered": "the point's effect is still in the final output",
    "unassessable": "the trace does not show enough to decide",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recovery", required=True); ap.add_argument("--taxonomy", required=True); ap.add_argument("--pool", required=True)
    ap.add_argument("--title", required=True); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--names", default=None, help="candidate set json with solver_models, to label candidates by model")
    ap.add_argument("--note", action="append", default=[], help="a line for the header (repeatable)")
    a = ap.parse_args()
    rs = json.load(open(f"{a.recovery}/summary.json"))
    tax = {c["id"]: c["name"] for c in json.load(open(a.taxonomy))["codes"]}
    inv = {v: k for k, v in json.load(open(f"{a.pool}/pool_manifest.json"))["candidate_index"].items()}
    label = {}
    if a.names:
        cs = json.load(open(a.names)); sm = cs.get("solver_models") or {}
        label = {c: (sm[c] if isinstance(sm, dict) else sm[i]) for i, c in enumerate(cs["candidate_ids"])} if sm else {}
    recs = [json.load(open(f)) for f in sorted(glob.glob(f"{a.recovery}/traces/*.json"))]
    judged = [r for r in recs if r.get("status") == "judged"]
    tasks = sorted({r["task_id"] for r in judged}); cands = sorted({inv[r["candidate_index"]] for r in judged})

    V = collections.Counter(); per_c = collections.defaultdict(collections.Counter); per_m = collections.defaultdict(collections.Counter)
    tr = collections.defaultdict(dict)   # candidate -> trace -> (points, unrec, modes, unrec modes)
    for r in judged:
        c = inv[r["candidate_index"]]; pts = r.get("points") or []
        modes = {m for p in pts for m in (p.get("codes") or ["(uncoded)"])}
        umodes = set(); u = 0
        for p in pts:
            v = p.get("recovery") or "unassessable"; V[v] += 1; per_c[c][v] += 1
            for m in (p.get("codes") or ["(uncoded)"]): per_m[m][v] += 1
            if v not in RECOVERED:
                u += 1; umodes |= set(p.get("codes") or ["(uncoded)"])
        per_c[c]["traces"] += 1; per_c[c]["points"] += len(pts); per_c[c]["unrec"] += u
        per_c[c]["flag_before"] += bool(pts); per_c[c]["flag_after"] += bool(u)
        per_c[c]["modes"] += len(modes); per_c[c]["umodes"] += len(umodes)
    total = sum(V.values()); rec = sum(V[k] for k in RECOVERED); unrec = total - rec
    n = len(judged)
    def name(c): return f"{label[c]} (`{c}`)" if c in label else f"`{c}`"

    L = [f"# {a.title} — recovery pass", ""]
    L += [f"Recovery reader: `{rs.get('model')}` (thinking {rs.get('thinking')}), success rule in view: **{'yes' if rs.get('success_rule_in_view') else 'no'}**.",
          f"Judge mapping read: `{rs.get('mapping')}`; taxonomy `{a.taxonomy}` ({len(tax)} codes).",
          f"Traces with a recovery verdict: **{n}** ({len(cands)} candidates × {len(tasks)} tasks{'' if n == len(cands)*len(tasks) else f'; {len(cands)*len(tasks)-n} traces could not be judged'}). One call per trace: the reader sees the whole trace and the judge's points, and gives each point one verdict."]
    L += [f"- {x}" for x in a.note]
    L += ["", "## Verdicts over every point", "", "| verdict | points | share | meaning |", "|---|---:|---:|---|"]
    for k in ORDER:
        if V[k]: L.append(f"| {k} | {V[k]} | {V[k]/total:.1%} | {MEANING[k]} |")
    L += [f"| **recovered (corrected + contained + made_irrelevant)** | **{rec}** | **{rec/total:.1%}** | removed for the unrecovered-only scores |",
          f"| **left standing (unrecovered + unassessable)** | **{unrec}** | **{unrec/total:.1%}** | what the unrecovered-only scores read |", ""]
    fb = sum(per_c[c]["flag_before"] for c in cands); fa = sum(per_c[c]["flag_after"] for c in cands)
    L += ["## Per trace (one candidate on one task), before and after", "", "| | before recovery | after (unrecovered only) |", "|---|---:|---:|",
          f"| points per trace, mean | {total/n:.2f} | {unrec/n:.2f} |",
          f"| distinct failure modes per trace, mean | {sum(per_c[c]['modes'] for c in cands)/n:.2f} | {sum(per_c[c]['umodes'] for c in cands)/n:.2f} |",
          f"| traces with at least one point | {fb} of {n} ({fb/n:.0%}) | {fa} of {n} ({fa/n:.0%}) |", ""]
    L += ["## Per candidate", "", "| candidate | traces | points before | per trace | corrected | contained | made irrelevant | unrecovered | unrec. per trace | traces flagged before → after |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for c in sorted(cands, key=lambda c: per_c[c]["unrec"] / per_c[c]["traces"]):
        p = per_c[c]; t = p["traces"]
        L.append(f"| {name(c)} | {t} | {p['points']} | {p['points']/t:.1f} | {p['corrected']} | {p['contained']} | {p['made_irrelevant']} | {p['unrec']} | {p['unrec']/t:.2f} | {p['flag_before']} → {p['flag_after']} |")
    L += ["", "## Per failure mode", "", "| mode | points before | recovered | unrecovered | share recovered |", "|---|---:|---:|---:|---:|"]
    for m in sorted(per_m, key=lambda m: -sum(per_m[m].values())):
        pm = per_m[m]; tot = sum(pm.values()); r_ = sum(pm[k] for k in RECOVERED)
        L.append(f"| `{m}` {tax.get(m, '')} | {tot} | {r_} | {tot-r_} | {r_/tot:.0%} |")
    L += ["", "A point with several modes is counted once under each; `(uncoded)` = the judge kept the point but no code fit it.", ""]
    a.out.write_text("\n".join(L)); print(f"{a.out}: {n} traces, {total} points, {rec} recovered, {unrec} standing")


if __name__ == "__main__":
    main()
