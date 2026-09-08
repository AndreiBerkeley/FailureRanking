#!/usr/bin/env python3
"""Rank agreement between the three pools of pools-1, per benchmark, from gold outcomes.

    python3 analyses/pools-1-rank-agreement/scripts/rank_agreement.py

For every benchmark, each candidate's mean gold score is computed on each pool
(taxonomy, judging, generalization) from repeat-0 traces only, so every task
counts once, and traces the provider blocked are left out. The three candidate
rankings are then compared pairwise: Kendall tau-b with a permutation p-value,
Spearman rho, whether the top candidate is the same, whether pool A's top
candidate is in pool B's top three, and how many of the top three are shared.
Gold is used for validation only; no trace content is read.
"""
from __future__ import annotations
import glob, itertools, json, random, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BENCH = ("hover", "ifbench", "hotpotqa")
POOLS = ("taxonomy", "judging", "generalization")
PAIRS = (("taxonomy", "judging"), ("judging", "generalization"), ("taxonomy", "generalization"))


def load(b):
    split = json.loads((REPO / "data" / b / "splits" / "pools-1" / "split.json").read_text())["portions"]
    portion = {t: p for p, ids in split.items() for t in ids}
    per = {p: {} for p in POOLS}; dropped = 0
    for f in sorted(glob.glob(str(REPO / "data" / b / "outcomes" / "cap-*.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            if int(r.get("repeat", 0)) != 0: continue
            if r.get("capture_failed"): dropped += 1; continue
            p = portion.get(r["task_id"])
            if p is None: continue
            per[p].setdefault(r["candidate_id"], {})[r["task_id"]] = float(r["score"])   # one score per (candidate, task)
    return per, dropped


def means(d):
    return {c: sum(s.values()) / len(s) for c, s in d.items()}


def tau_b(x, y):
    n = len(x); conc = disc = tx = ty = 0
    for i, j in itertools.combinations(range(n), 2):
        a, b = x[i] - x[j], y[i] - y[j]
        if a == 0 and b == 0: continue
        if a == 0: tx += 1
        elif b == 0: ty += 1
        elif (a > 0) == (b > 0): conc += 1
        else: disc += 1
    den = ((conc + disc + tx) * (conc + disc + ty)) ** 0.5
    return (conc - disc) / den if den else float("nan")


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]: j += 1
        for k in range(i, j + 1): r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y); n = len(x); mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else float("nan")


def perm_p(x, y, n=20000, seed=2026):
    rng = random.Random(seed); t0 = abs(tau_b(x, y)); y = list(y); hits = 0
    for _ in range(n):
        rng.shuffle(y); hits += abs(tau_b(x, y)) >= t0 - 1e-12
    return (hits + 1) / (n + 1)


def top(m, k):
    return [c for c, _ in sorted(m.items(), key=lambda kv: -kv[1])[:k]]


def main():
    out = {"repeat": 0, "excluded": "traces the provider blocked (capture_failed)", "benchmarks": {}}
    for b in BENCH:
        per, dropped = load(b); cands = sorted(set.intersection(*(set(per[p]) for p in POOLS)))
        assert len(cands) == 12, (b, len(cands))
        M = {p: means(per[p]) for p in POOLS}
        sizes = {p: sorted({len(s) for s in per[p].values()}) for p in POOLS}
        print(f"\n== {b}: tasks per candidate {', '.join(f'{p} {sizes[p]}' for p in POOLS)}; blocked traces excluded: {dropped}")
        print(f"   {'pair':30s} {'tau-b':>7s} {'p':>7s} {'rho':>7s}  top-1  A-top1-in-B-top3  top-3 shared")
        res = {"tasks_per_candidate": sizes, "blocked_excluded": dropped, "means": M, "pairs": {}}
        for a, c in PAIRS:
            x = [M[a][k] for k in cands]; y = [M[c][k] for k in cands]
            t, p, rho = tau_b(x, y), perm_p(x, y), spearman(x, y)
            ta, tc = top(M[a], 3), top(M[c], 3)
            top1 = ta[0] == tc[0]; in3 = ta[0] in tc; shared = len(set(ta) & set(tc))
            print(f"   {a + ' vs ' + c:30s} {t:+7.3f} {p:7.4f} {rho:+7.3f}  {'yes' if top1 else 'no ':>4s}  {'yes' if in3 else 'no ':>16s}  {shared}/3")
            res["pairs"][f"{a} vs {c}"] = {"kendall_tau_b": t, "permutation_p": p, "spearman_rho": rho, "top1_same": top1,
                                           "top1_of_first_in_top3_of_second": in3, "top3_shared": shared, "top3": {a: ta, c: tc}}
        out["benchmarks"][b] = res
    (REPO / "analyses" / "pools-1-rank-agreement" / "results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
