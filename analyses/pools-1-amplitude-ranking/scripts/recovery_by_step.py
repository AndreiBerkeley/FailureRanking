#!/usr/bin/env python3
"""Recovery-discounted blame with (code, step) as the unit. DECLARED GOLD-USING.

    python3 analyses/pools-1-amplitude-ranking/scripts/recovery_by_step.py

Same formula as recovery_influence.py, but a mode is a (code, agent-turn) pair, so a code firing at
summarize1 and the same code firing at summarize2 are two modes with separate appear/recover counts.
Step attribution from votes_by_turn: 'both' = both readers placed the code on that turn; 'any' = at
least one did. Aggregations lower-is-better: mode_sum, task_max, task_nor. Validation against the
generalization gold; the gold-50 partial says whether the units add anything beyond the gold read.
"""
from __future__ import annotations
import json, gzip, glob, sys, random, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p, ranks  # noqa: E402

CONFIGS = [("hover", "map-5", "tax-10"), ("hover", "map-3", "tax-18"), ("ifbench", "map-1", "tax-1"), ("hotpotqa", "map-1", "tax-1")]
TAU = 3


def resid(r, z):
    rr, rz = ranks(r), ranks(z); k = len(r); mz = sum(rz) / k; mr = sum(rr) / k
    b = sum((a - mz) * (c - mr) for a, c in zip(rz, rr)) / sum((a - mz) ** 2 for a in rz)
    return [c - mr - b * (a - mz) for a, c in zip(rz, rr)]


def partial(x, y, z, N=20000):
    rx, ry = resid(x, z), resid(y, z); t0 = tau_b(rx, ry); rng = random.Random(2026); hits = 0; ry2 = list(ry)
    for _ in range(N): rng.shuffle(ry2); hits += abs(tau_b(rx, ry2)) >= abs(t0) - 1e-12
    return t0, (hits + 1) / (N + 1)


def units(recs, codes, min_votes):
    """per trace: the set of (code, step) units present."""
    out = []
    for r in recs:
        u = set()
        for tk, v in (r.get("votes_by_turn") or {}).items():
            step = tk.split(":", 1)[1]
            u |= {(m, step) for m, x in v.items() if x >= min_votes and m in codes}
        out.append((r["candidate_id"], r["task_id"], u))
    return out


def score(traces, per, cands, gamma):
    by = collections.defaultdict(list)
    for c, t, u in traces: by[c].append((t, u))
    out = {"mode_sum": {}, "task_max": {}, "task_nor": {}}
    for c in cands:
        R = by[c]; T = len(R); fail = {t: per["judging"][c][t] < 1.0 for t, _ in R}; base = sum(fail.values()) / T
        n = collections.Counter(); s = collections.Counter()
        for t, u in R:
            for m in u: n[m] += 1; s[m] += not fail[t]
        w = {m: (1 - (s[m] / n[m]) ** gamma) if n[m] >= TAU else base for m in n}
        out["mode_sum"][c] = sum(w[m] * n[m] for m in n) / T
        out["task_max"][c] = sum(max((w[m] for m in u), default=0.0) for _, u in R) / T
        nor = 0.0
        for _, u in R:
            p = 1.0
            for m in u: p *= 1 - w[m]
            nor += (1 - p) if u else 0.0
        out["task_nor"][c] = nor / T
    return out


def main():
    for b, mid, tid in CONFIGS:
        per, _ = load(b); Gg = means(per["generalization"])
        codes = {c["id"] for c in json.load(open(REPO / "data" / b / "taxonomies" / tid / "taxonomy.json"))["codes"]}
        recs = []
        for f in glob.glob(str(REPO / "data" / b / "mappings" / mid / "judge_records/*.jsonl.gz")):
            with gzip.open(f, "rt") as fh:
                for line in fh:
                    r = json.loads(line)
                    if r["status"] == "judged": recs.append(r)
        cands = sorted({r["candidate_id"] for r in recs}); tasks = sorted({r["task_id"] for r in recs})
        gg = [Gg[c] for c in cands]; g50 = [sum(per["judging"][c][t] for t in tasks) / len(tasks) for c in cands]
        for rule, mv in (("both readers same turn", 2), ("any reader", 1)):
            tr = units(recs, codes, mv); nunits = len({m for _, _, u in tr for m in u})
            print(f"\n== {b} {mid} ({tid}), (code, step) units, {rule}: {nunits} distinct units; ceiling {tau_b(g50, gg):+.2f} ==")
            print(f"   {'gamma':>5s} {'aggregation':11s} {'vs gold gen':>19s} {'| gold50 partialled out':>24s}")
            for gamma in (1, 2, 3):
                S = score(tr, per, cands, gamma)
                for agg in ("mode_sum", "task_max", "task_nor"):
                    s = [-S[agg][c] for c in cands]; pt, pp = partial(s, gg, g50)
                    print(f"   {gamma:5d} {agg:11s} {tau_b(s, gg):+7.2f} (p={perm_p(s, gg):.3f}) {pt:+12.2f} (p={pp:.2f})")


if __name__ == "__main__":
    main()
