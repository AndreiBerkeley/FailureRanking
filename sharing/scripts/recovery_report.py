#!/usr/bin/env python3
"""One Markdown report per experiment on what the recovery reader did with the judge's failure instances.

    python3 sharing/scripts/recovery_report.py --recovery <recovery run> --taxonomy <taxonomy.json>
        --pool <judged pool dir> --title "..." --out sharing/<name>_recovery.md [--names <candidate set json>] [--note "..."]

Reads the recovery run's traces/*.json (each judged instance carries its verdict), counts verdicts
in total, per candidate and per failure mode, and reports instances and modes per trace before and
after the recovered instances are removed. No model call; no gold.
"""
from __future__ import annotations
import argparse, json, glob, collections
from pathlib import Path

RECOVERED = ("corrected", "contained")
ORDER = ["corrected", "contained", "unrecovered"]
COARSE = {"unrecovered": "unrecovered", "unassessable": "unrecovered", "corrected": "corrected", "contained": "contained", "made_irrelevant": "contained"}
def coarse(v): return COARSE.get(v, "unrecovered")   # runs before 2026-09-22 recorded five verdicts; three since
MEANING = {
    "corrected": "a later step replaced the wrong thing and the output does not carry it",
    "contained": "the output does not carry it and nothing corrected it: nothing downstream used it, or it was used and the output was fine regardless, or another path supplied what was needed",
    "unrecovered": "the effect is in the final output, or what the instance cost is missing from it, or the trace cannot show otherwise",
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
            v = coarse(p.get("recovery")); V[v] += 1; per_c[c][v] += 1
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
          f"Traces with a recovery verdict: **{n}** ({len(cands)} candidates × {len(tasks)} tasks{'' if n == len(cands)*len(tasks) else f'; {len(cands)*len(tasks)-n} traces could not be judged'}). One call per trace: the reader sees the whole trace and the judge's failure instances, and gives each instance one verdict."]
    L += [f"- {x}" for x in a.note]
    L += ["", "## Verdicts over every failure instance", "", "| verdict | instances | share | meaning |", "|---|---:|---:|---|"]
    for k in ORDER:
        if V[k]: L.append(f"| {k} | {V[k]} | {V[k]/total:.1%} | {MEANING[k]} |")
    L += [f"| **recovered (corrected + contained)** | **{rec}** | **{rec/total:.1%}** | removed for the unrecovered-only scores |",
          f"| **left standing (unrecovered)** | **{unrec}** | **{unrec/total:.1%}** | what the unrecovered-only scores read |", ""]
    fb = sum(per_c[c]["flag_before"] for c in cands); fa = sum(per_c[c]["flag_after"] for c in cands)
    L += ["## Per trace (one candidate on one task), before and after", "", "| | before recovery | after (unrecovered only) |", "|---|---:|---:|",
          f"| failure instances per trace, mean | {total/n:.2f} | {unrec/n:.2f} |",
          f"| distinct failure modes per trace, mean | {sum(per_c[c]['modes'] for c in cands)/n:.2f} | {sum(per_c[c]['umodes'] for c in cands)/n:.2f} |",
          f"| traces with at least one instance | {fb} of {n} ({fb/n:.0%}) | {fa} of {n} ({fa/n:.0%}) |", ""]
    L += ["## Per candidate", "", "| candidate | traces | instances before | per trace | corrected | contained | unrecovered | unrec. per trace | traces flagged before → after |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for c in sorted(cands, key=lambda c: per_c[c]["unrec"] / per_c[c]["traces"]):
        p = per_c[c]; t = p["traces"]
        L.append(f"| {name(c)} | {t} | {p['points']} | {p['points']/t:.1f} | {p['corrected']} | {p['contained']} | {p['unrec']} | {p['unrec']/t:.2f} | {p['flag_before']} → {p['flag_after']} |")
    L += ["", "## Per failure mode", "", "| mode | instances before | recovered | unrecovered | share recovered |", "|---|---:|---:|---:|---:|"]
    for m in sorted(per_m, key=lambda m: -sum(per_m[m].values())):
        pm = per_m[m]; tot = sum(pm.values()); r_ = sum(pm[k] for k in RECOVERED)
        L.append(f"| `{m}` {tax.get(m, '')} | {tot} | {r_} | {tot-r_} | {r_/tot:.0%} |")
    L += ["", "An instance with several modes is counted once under each; `(uncoded)` = the judge kept the instance but no code fit it.", ""]
    a.out.write_text("\n".join(L)); print(f"{a.out}: {n} traces, {total} instances, {rec} recovered, {unrec} standing")


if __name__ == "__main__":
    main()
