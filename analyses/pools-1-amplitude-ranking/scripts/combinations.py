#!/usr/bin/env python3
"""Combination entries: every set of codes that co-occurs on a task counts as an entry; score = sum of entry rates.

    python3 analyses/pools-1-amplitude-ranking/scripts/combinations.py

  all         every non-empty combination present on a task counts once there  -> mean over tasks of 2^k_t - 1
  recurring   only combinations present on at least two of the candidate's tasks
  weighted    each combination weighted by its own rate (the August 'persistent combinations')
Lower is better. Kendall tau-b (permutation p) against gold on the 50 judged tasks and on the generalization pool.
"""
from __future__ import annotations
import json, sys, itertools, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p  # noqa: E402

MAPS = {"hover": ("map-3", "tax-18"), "ifbench": ("map-1", "tax-1"), "hotpotqa": ("map-1", "tax-1")}


def combos(codes):
    codes = sorted(codes)
    for r in range(1, len(codes) + 1):
        for s in itertools.combinations(codes, r): yield s


def main():
    print(f"{'benchmark':9s} {'entries':10s} {'range':>15s}  {'gold50 vs judge50':>19s}  {'gold gen vs judge50':>20s}  {'gold50 vs gold gen':>18s}   max codes on a task")
    for b, (mid, tid) in MAPS.items():
        per, _ = load(b); Gg = means(per["generalization"])
        rows = [json.loads(l) for l in open(REPO / "data" / b / "mappings" / mid / "mapping.jsonl")]
        rows = [r for r in rows if r["status"] == "judged" and int(r.get("repeat", 0)) == 0]
        cands = sorted({r["candidate_id"] for r in rows}); tasks = sorted({r["task_id"] for r in rows}); T = len(tasks)
        cnt = {c: collections.Counter() for c in cands}; kmax = 0
        for r in rows:
            codes = list(r.get("codes") or {}); kmax = max(kmax, len(codes))
            for s in combos(codes): cnt[r["candidate_id"]][s] += 1
        S = {"all": {c: sum(cnt[c].values()) / T for c in cands},
             "recurring": {c: sum(n for n in cnt[c].values() if n >= 2) / T for c in cands},
             "weighted": {c: sum((n / T) ** 2 for n in cnt[c].values()) for c in cands}}
        g50 = {c: sum(per["judging"][c][t] for t in tasks) / T for c in cands}
        x50 = [g50[c] for c in cands]; xg = [Gg[c] for c in cands]; base = f"{tau_b(x50, xg):+.2f} (p={perm_p(x50, xg):.3f})"
        for name, sc in S.items():
            s = [-sc[c] for c in cands]
            print(f"{b:9s} {name:10s} {min(sc.values()):6.2f}–{max(sc.values()):6.2f}  {tau_b(s, x50):+.2f} (p={perm_p(s, x50):.3f})     {tau_b(s, xg):+.2f} (p={perm_p(s, xg):.3f})      {base}   {kmax}")


if __name__ == "__main__":
    main()
