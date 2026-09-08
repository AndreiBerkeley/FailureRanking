#!/usr/bin/env python3
"""Why counting fails: per code, (1) task-level lift = P(task fails | code fired) - P(task fails | not fired) within each
candidate, averaged over candidates; (2) candidate-level tau between the code's firing rate and the generalization gold.
Then amplitude recomputed over the codes with positive lift only, as a diagnostic (uses gold; not a method).

    python3 analyses/pools-1-amplitude-ranking/scripts/why_amplitude_fails.py
"""
from __future__ import annotations
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p  # noqa: E402

MAPS = {"hover": ("map-3", "tax-18"), "hotpotqa": ("map-1", "tax-1"), "ifbench": ("map-1", "tax-1")}


def main():
    for b, (mid, tid) in MAPS.items():
        per, _ = load(b); Gg = means(per["generalization"])
        tax = {c["id"]: c["name"] for c in json.load(open(REPO / "data" / b / "taxonomies" / tid / "taxonomy.json"))["codes"]}
        rows = [json.loads(l) for l in open(REPO / "data" / b / "mappings" / mid / "mapping.jsonl")]
        rows = [r for r in rows if r["status"] == "judged" and int(r.get("repeat", 0)) == 0]
        cands = sorted({r["candidate_id"] for r in rows}); T = len({r["task_id"] for r in rows})
        fail = {c: {t: per["judging"][c][t] < 1.0 for t in per["judging"][c]} for c in cands}
        codes = sorted({m for r in rows for m in (r.get("codes") or {})})
        pres = {c: {m: set() for m in codes} for c in cands}
        for r in rows:
            for m in (r.get("codes") or {}): pres[r["candidate_id"]][m].add(r["task_id"])
        tasks_c = {c: {r["task_id"] for r in rows if r["candidate_id"] == c} for c in cands}
        gg = [Gg[c] for c in cands]
        print(f"\n== {b} ({mid}, {tid}); overall task failure rate on the judged 50: {sum(sum(fail[c][t] for t in tasks_c[c]) for c in cands) / (12 * T):.0%}")
        print(f"   {'code':52s} {'fires':>5s} {'on failing tasks':>16s} {'lift':>6s} {'rate vs gold':>12s}")
        lifts = {}
        for m in codes:
            n = sum(len(pres[c][m]) for c in cands); onfail = sum(sum(fail[c][t] for t in pres[c][m]) for c in cands)
            L = []
            for c in cands:
                P = pres[c][m]; A = tasks_c[c] - P
                if P and A: L.append(sum(fail[c][t] for t in P) / len(P) - sum(fail[c][t] for t in A) / len(A))
            lift = sum(L) / len(L) if L else float("nan"); lifts[m] = lift
            rate = [len(pres[c][m]) / T for c in cands]
            print(f"   {m + ' ' + tax[m][:44]:52s} {n:5d} {onfail / n if n else 0:16.0%} {lift:+6.2f} {tau_b([-x for x in rate], gg):+12.2f}")
        pos = [m for m in codes if lifts[m] > 0.05]
        A_all = {c: sum(len(pres[c][m]) for m in codes) / T for c in cands}; A_pos = {c: sum(len(pres[c][m]) for m in pos) / T for c in cands}
        print(f"   amplitude over all codes: tau vs gold gen {tau_b([-A_all[c] for c in cands], gg):+.2f};  over the {len(pos)} codes with task-level lift > 0.05: {tau_b([-A_pos[c] for c in cands], gg):+.2f} (p={perm_p([-A_pos[c] for c in cands], gg):.3f})  [diagnostic: uses gold to pick codes]")


if __name__ == "__main__":
    main()
