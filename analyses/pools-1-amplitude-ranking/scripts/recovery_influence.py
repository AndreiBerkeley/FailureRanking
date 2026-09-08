#!/usr/bin/env python3
"""Recovery-discounted blame (the 2026-08-17 combination-influence idea), single modes. DECLARED GOLD-USING.

    python3 analyses/pools-1-amplitude-ranking/scripts/recovery_influence.py

For candidate c and mode m over the judged tasks:
  n_m = tasks on which m fired;  s_m = those the task nevertheless passed by gold ("recovered")
  w_m = 1 - (s_m / n_m)^gamma        the mode's blame; gamma=1 linear discount, gamma=2 convex (August default)
  modes with n_m < tau (support) fall back to the candidate's own task failure rate as blame
Aggregations, all lower-is-better, mean over the judged tasks:
  mode_sum   sum_m w_m * n_m / T          (mode-first, every occurrence priced by its mode's blame)
  task_max   per task, max w_m over the codes present; 0 if none      (August v1)
  task_nor   per task, 1 - prod(1 - w_m); 0 if none                    (August v2, noisy-OR)
The influences use the candidate's gold on the SAME judged tasks, so agreement with gold-50 is
circular and only the generalization column is a test. Nothing here is outcome-free.
"""
from __future__ import annotations
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p  # noqa: E402

CONFIGS = [("hover", "map-5", "tax-10"), ("hover", "map-3", "tax-18"), ("ifbench", "map-1", "tax-1"), ("hotpotqa", "map-1", "tax-1")]
TAU = 3


def score(rows, per, cands, gamma):
    by = collections.defaultdict(list)
    for r in rows: by[r["candidate_id"]].append(r)
    out = {"mode_sum": {}, "task_max": {}, "task_nor": {}, "linear_check": {}}
    for c in cands:
        R = by[c]; T = len(R); fail = {r["task_id"]: per["judging"][c][r["task_id"]] < 1.0 for r in R}
        base = sum(fail.values()) / T
        n = collections.Counter(); s = collections.Counter()
        for r in R:
            for m in (r["codes"] or {}): n[m] += 1; s[m] += not fail[r["task_id"]]
        w = {m: (1 - (s[m] / n[m]) ** gamma) if n[m] >= TAU else base for m in n}
        out["mode_sum"][c] = sum(w[m] * n[m] for m in n) / T
        out["task_max"][c] = sum(max((w[m] for m in (r["codes"] or {})), default=0.0) for r in R) / T
        nor = 0.0
        for r in R:
            p = 1.0
            for m in (r["codes"] or {}): p *= 1 - w[m]
            nor += 1 - p if (r["codes"] or {}) else 0.0
        out["task_nor"][c] = nor / T
    return out


def main():
    for b, mid, tid in CONFIGS:
        per, _ = load(b); Gg = means(per["generalization"])
        rows = [json.loads(l) for l in open(REPO / "data" / b / "mappings" / mid / "mapping.jsonl")]
        rows = [r for r in rows if r["status"] == "judged" and int(r.get("repeat", 0)) == 0]
        cands = sorted({r["candidate_id"] for r in rows}); tasks = sorted({r["task_id"] for r in rows})
        gg = [Gg[c] for c in cands]; x50 = [sum(per["judging"][c][t] for t in tasks) / len(tasks) for c in cands]
        print(f"\n== {b} {mid} ({tid}); ceiling gold50 vs gold gen {tau_b(x50, gg):+.2f} ==")
        print(f"   {'gamma':>5s} {'aggregation':11s} {'vs gold gen (the test)':>24s} {'vs gold50 (circular)':>22s}")
        for gamma in (1, 2, 3):
            S = score(rows, per, cands, gamma)
            for agg in ("mode_sum", "task_max", "task_nor"):
                s = [-S[agg][c] for c in cands]
                print(f"   {gamma:5d} {agg:11s} {tau_b(s, gg):+7.2f} (p={perm_p(s, gg):.3f}) {'':6s} {tau_b(s, x50):+7.2f} (p={perm_p(s, x50):.3f})")


if __name__ == "__main__":
    main()
