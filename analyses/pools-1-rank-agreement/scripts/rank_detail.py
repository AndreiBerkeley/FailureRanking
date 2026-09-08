#!/usr/bin/env python3
"""Companion to rank_agreement.py: how much of the disagreement is noise, and how much is the optimizer.

  - resolvability per pool: spread of candidate means against the standard error of each mean
    (a pair of candidates is 'resolvable' when |mean difference| exceeds twice the combined SE)
  - bootstrap CI of Kendall tau-b per pair: tasks are resampled within each pool, 1,000 times
  - the taxonomy pool split into optimizer-seen tasks (gepa-1 train + validation) and never-seen tasks,
    each compared with the judging and generalization pools
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rank_agreement import REPO, BENCH, POOLS, PAIRS, load, means, tau_b, top

R = random.Random(2026)


def se(scores):
    n = len(scores); m = sum(scores) / n
    return (sum((s - m) ** 2 for s in scores) / (n - 1) / n) ** 0.5 if n > 1 else float("nan")


def boot_tau(A, B, cands, n=1000):
    ta = sorted({t for c in cands for t in A[c]}); tb = sorted({t for c in cands for t in B[c]}); out = []
    for _ in range(n):
        sa = [R.choice(ta) for _ in ta]; sb = [R.choice(tb) for _ in tb]
        x = [sum(A[c].get(t, 0.0) for t in sa) / len(sa) for c in cands]
        y = [sum(B[c].get(t, 0.0) for t in sb) / len(sb) for c in cands]
        out.append(tau_b(x, y))
    out.sort(); return out[int(0.025 * n)], out[int(0.975 * n)]


def restrict(d, keep):
    return {c: {t: s for t, s in v.items() if t in keep} for c, v in d.items()}


def main():
    for b in BENCH:
        per, _ = load(b); cands = sorted(set.intersection(*(set(per[p]) for p in POOLS)))
        g = json.loads((REPO / "data" / b / "splits" / "gepa-1" / "split.json").read_text())["portions"]
        seen = set(g.get("train", [])) | set(g.get("validation", []))
        print(f"\n== {b}")
        print(f"   {'pool':15s} {'tasks':>5s} {'mean range':>13s} {'median SE':>10s} {'resolvable pairs':>17s}")
        for p in POOLS:
            M = means(per[p]); ses = {c: se(list(per[p][c].values())) for c in cands}
            vals = sorted(M[c] for c in cands); med = sorted(ses.values())[6]
            res = sum(1 for i in range(12) for j in range(i + 1, 12)
                      if abs(M[cands[i]] - M[cands[j]]) > 2 * (ses[cands[i]] ** 2 + ses[cands[j]] ** 2) ** 0.5)
            print(f"   {p:15s} {len(next(iter(per[p].values()))):5d} {vals[0]:.3f} – {vals[-1]:.3f} {med:10.3f} {res:11d} / 66")
        print(f"   {'pair':30s} {'tau-b':>7s}  {'95% bootstrap CI':>17s}")
        for a, c in PAIRS:
            x = [means(per[a])[k] for k in cands]; y = [means(per[c])[k] for k in cands]
            lo, hi = boot_tau(per[a], per[c], cands)
            print(f"   {a + ' vs ' + c:30s} {tau_b(x, y):+7.3f}  [{lo:+.2f}, {hi:+.2f}]")
        tax = per["taxonomy"]; tasks = {t for c in cands for t in tax[c]}
        parts = {"taxonomy, optimizer-seen": tasks & seen, "taxonomy, never-seen": tasks - seen}
        for name, keep in parts.items():
            if not keep: print(f"   {name}: 0 tasks"); continue
            sub = restrict(tax, keep); xs = [means(sub)[k] for k in cands]
            row = "  ".join(f"vs {p} {tau_b(xs, [means(per[p])[k] for k in cands]):+.3f}" for p in ("judging", "generalization"))
            print(f"   {name} ({len(keep)} tasks): {row}; top-1 = {top(means(sub), 1)[0][-6:]}")
        print(f"   top-1 per pool: " + ", ".join(f"{p} {top(means(per[p]), 1)[0][-6:]}" for p in POOLS))


if __name__ == "__main__":
    main()
