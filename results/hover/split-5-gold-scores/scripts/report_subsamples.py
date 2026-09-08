#!/usr/bin/env python3
"""Gold scores for every candidate on every split-5 subsample, plus the variance
curve those subsamples are drawn to reveal.

    report_subsamples.py --out results/hover/split-5-gold-scores

Two things are reported. The 30 recorded subsamples give concrete, addressable
score tables. A Monte Carlo over many more draws at each size gives the shape:
how far a subsample's answer typically sits from the truth, as a function of n.

No model is called. This directory is gold-bearing by design and sits on no
gold-free scoring path.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
T3 = REPO / "benchmarks/hover/traces/traces-3"
SUBS = REPO / "benchmarks/hover/splits/split-5/subsamples.json"
MC_DRAWS = 2000


def mean(v): return sum(v) / len(v)


def sd(v):
    m = mean(v)
    return math.sqrt(sum((a - m) ** 2 for a in v) / (len(v) - 1)) if len(v) > 1 else 0.0


def pct(v, q):
    s = sorted(v); k = (len(s) - 1) * q / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] if lo == hi else s[lo] * (hi - k) + s[hi] * (k - lo)


def ranks(x):
    o = sorted(range(len(x)), key=lambda i: x[i]); r = [0.0] * len(x); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def pearson(x, y):
    mx, my = mean(x), mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x)); sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return float("nan") if sx == 0 or sy == 0 else \
        sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def spearman(x, y): return pearson(ranks(x), ranks(y))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mc-draws", type=int, default=MC_DRAWS)
    a = ap.parse_args()

    meta = json.loads(SUBS.read_text())
    subs = meta["subsamples"]
    gold = {c: v["0"] for c, v in
            json.loads((T3 / "generalization/outcomes.json").read_text())["outcomes"].items()}
    cands = sorted(gold)
    pool = sorted(gold[cands[0]])
    # candidate x task matrix, task order fixed by `pool`
    pos = {t: i for i, t in enumerate(pool)}
    G = [[gold[c][t] for t in pool] for c in cands]
    truth = [mean(r) for r in G]

    def acc(ix): return [mean([G[i][t] for t in ix]) for i in range(len(cands))]

    def separable(ix):
        n, out = len(ix), 0
        for i, j in itertools.combinations(range(len(cands)), 2):
            d = [G[i][t] - G[j][t] for t in ix]
            s = sd(d) / math.sqrt(n)
            if s and abs(mean(d) / s) > 1.96:
                out += 1
        return out

    # ---- the 30 recorded subsamples -------------------------------------
    rec = {}
    for name, s in sorted(subs.items()):
        ix = [pos[t] for t in s["tasks"]]
        tx = [pos[t] for t in s["target"]]
        av, at = acc(ix), acc(tx)
        rec[name] = {"n": s["n"], "accuracy": dict(zip(cands, av)),
                     "spearman_vs_target": spearman(av, at),
                     "target_n": len(tx), "pairs_separable_of_66": separable(ix),
                     "top1": cands[max(range(len(cands)), key=lambda i: av[i])]}

    # ---- Monte Carlo: the shape ----------------------------------------
    rng = random.Random(101)
    sizes = meta["sizes"]
    curve = {}
    for n in sizes:
        rhos, seps, errs, tops, percand = [], [], [], [], {i: [] for i in range(len(cands))}
        for _ in range(a.mc_draws):
            ix = rng.sample(range(len(pool)), n)
            rest = list(set(range(len(pool))) - set(ix))
            av = acc(ix)
            rhos.append(spearman(av, acc(rest)))
            errs.append(mean([abs(av[i] - truth[i]) for i in range(len(cands))]))
            tops.append(cands[max(range(len(cands)), key=lambda i: av[i])])
            for i in range(len(cands)):
                percand[i].append(av[i])
            if len(seps) < 200:
                seps.append(separable(ix))
        true_top = cands[max(range(len(cands)), key=lambda i: truth[i])]
        curve[n] = {
            "draws": a.mc_draws,
            "spearman_vs_held_out": {"median": pct(rhos, 50), "mean": mean(rhos),
                                     "sd": sd(rhos), "p05": pct(rhos, 5),
                                     "p95": pct(rhos, 95), "min": min(rhos)},
            "mean_abs_accuracy_error": mean(errs),
            "per_candidate_accuracy_sd": mean([sd(percand[i]) for i in range(len(cands))]),
            "pairs_separable_of_66": {"mean": mean(seps), "n_evaluated": len(seps)},
            "picks_true_best": sum(t == true_top for t in tops) / len(tops),
            "distinct_candidates_ever_ranked_first": len(set(tops)),
        }

    out = {"produced_by": "results/hover/split-5-gold-scores/scripts/report_subsamples.py",
           "subsamples": "benchmarks/hover/splits/split-5/subsamples.json",
           "gold_from": "benchmarks/hover/traces/traces-3/generalization/outcomes.json",
           "candidates": cands, "truth_500": dict(zip(cands, truth)),
           "recorded": rec, "monte_carlo": curve}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "scores.json").write_text(json.dumps(out, indent=1) + "\n")

    L = []; w = L.append
    w("# split-5 — gold scores across random subsamples of 50–100 tasks\n")
    w("Thirty recorded subsamples drawn from split-3's 500 unseen tasks, five at")
    w("each of six sizes, each scored against the 500 minus its own tasks. **No")
    w("capture and no judging was run**: every trace and gold score already existed.")
    w("Subsamples overlap each other by construction — 500 tasks cannot supply many")
    w("disjoint sets this large — so they are independent draws, not a partition.\n")
    w("Generated by `scripts/report_subsamples.py`; numbers in `scores.json`.\n")

    w("## The truth to be recovered\n")
    w("Accuracy on all 500 tasks, ±0.022 per candidate.\n")
    w("| candidate | accuracy on 500 |")
    w("|---|---:|")
    for i in sorted(range(len(cands)), key=lambda i: -truth[i]):
        w(f"| {cands[i]} | {truth[i]:.3f} |")
    w("")

    w("## How much does the draw matter? (Monte Carlo, "
      f"{a.mc_draws:,} draws per size)\n")
    w("| n | ρ vs held-out: median | 5th pct | worst seen | per-candidate acc sd |"
      " mean abs error | pairs separable /66 | picks the true best |")
    w("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for n in sizes:
        c = curve[n]; s = c["spearman_vs_held_out"]
        w(f"| {n} | {s['median']:+.3f} | {s['p05']:+.3f} | {s['min']:+.3f} | "
          f"{c['per_candidate_accuracy_sd']:.3f} | {c['mean_abs_accuracy_error']:.3f} | "
          f"{c['pairs_separable_of_66']['mean']:.1f} | {c['picks_true_best']:.1%} |")
    w("")
    w("`picks the true best` is how often the subsample's top-ranked candidate is")
    w("the one that is actually best on all 500.")
    w("")

    w("## The thirty recorded subsamples\n")
    w("| subsample | n | ρ vs its target | pairs separable /66 | ranks first |")
    w("|---|---:|---:|---:|---|")
    for name, r in rec.items():
        w(f"| {name} | {r['n']} | {r['spearman_vs_target']:+.3f} | "
          f"{r['pairs_separable_of_66']} | {r['top1']} |")
    w("")

    w("## Per-candidate accuracy on every subsample\n")
    for n in sizes:
        names = [k for k in rec if rec[k]["n"] == n]
        w(f"### n = {n}\n")
        w("| candidate | truth (500) | " + " | ".join(names) + " | range |")
        w("|---|---:|" + "---:|" * (len(names) + 1))
        for i in sorted(range(len(cands)), key=lambda i: -truth[i]):
            row = [rec[k]["accuracy"][cands[i]] for k in names]
            w(f"| {cands[i]} | {truth[i]:.3f} | "
              + " | ".join(f"{v:.3f}" for v in row)
              + f" | {max(row) - min(row):.3f} |")
        w("")
    (a.out / "README.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:60]))
    print(f"\n-> {a.out}/README.md and scores.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
