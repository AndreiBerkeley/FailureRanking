#!/usr/bin/env python3
"""Basic mode-first readings of a candidate's code profile, from a black-box judge (codes per trace only).

    python3 analyses/pools-1-amplitude-ranking/scripts/profile_basics.py

r_m(c) = share of the 50 judged tasks on which code m fired for c. Modes that never fired anywhere are dropped.
  sum         S = sum_m r_m            (= base amplitude)
  breadth     B = number of modes with r_m > 0
  worst       W = max_m r_m
  persistent  P = number of modes with r_m >= 0.2
All lower-is-better. Kendall tau-b (permutation p) against gold on the 50 judged tasks and on the generalization pool.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p  # noqa: E402

MAPS = {"hover": ("map-3", "tax-18"), "ifbench": ("map-1", "tax-1"), "hotpotqa": ("map-1", "tax-1")}


def main():
    print(f"{'benchmark':9s} {'reading':11s} {'range':>13s}  {'gold50 vs judge50':>19s}  {'gold gen vs judge50':>20s}  {'gold50 vs gold gen':>18s}")
    for b, (mid, tid) in MAPS.items():
        per, _ = load(b); Gg = means(per["generalization"])
        rows = [json.loads(l) for l in open(REPO / "data" / b / "mappings" / mid / "mapping.jsonl")]
        rows = [r for r in rows if r["status"] == "judged" and int(r.get("repeat", 0)) == 0]
        cands = sorted({r["candidate_id"] for r in rows}); tasks = sorted({r["task_id"] for r in rows}); T = len(tasks)
        occ = {c: {} for c in cands}
        for r in rows:
            for m in (r.get("codes") or {}): occ[r["candidate_id"]][m] = occ[r["candidate_id"]].get(m, 0) + 1
        M = sorted({m for c in cands for m in occ[c]})
        rate = {c: {m: occ[c].get(m, 0) / T for m in M} for c in cands}
        readings = {"sum": {c: sum(rate[c].values()) for c in cands},
                    "breadth": {c: sum(1 for m in M if rate[c][m] > 0) for c in cands},
                    "worst": {c: max(rate[c].values()) for c in cands},
                    "persistent": {c: sum(1 for m in M if rate[c][m] >= 0.2) for c in cands}}
        g50 = {c: sum(per["judging"][c][t] for t in tasks) / T for c in cands}
        x50 = [g50[c] for c in cands]; xg = [Gg[c] for c in cands]; base = f"{tau_b(x50, xg):+.2f} (p={perm_p(x50, xg):.3f})"
        for name, S in readings.items():
            s = [-S[c] for c in cands]
            print(f"{b:9s} {name:11s} {min(S.values()):5.2f}–{max(S.values()):5.2f}  {tau_b(s, x50):+.2f} (p={perm_p(s, x50):.3f})     {tau_b(s, xg):+.2f} (p={perm_p(s, xg):.3f})      {base}")
        print(f"{'':9s} modes that fired: {len(M)} of {len(json.load(open(REPO / 'data' / b / 'taxonomies' / tid / 'taxonomy.json'))['codes'])}")


if __name__ == "__main__":
    main()
