#!/usr/bin/env python3
"""Failure-profile stability: does a candidate's failure distribution on the
sample portion match its distribution on the domain portion?

    stability.py --n-map data/hover/mappings/map-1 --m-map data/hover/mappings/map-2 \
                 --taxonomy data/hover/taxonomies/tax-7/taxonomy.json \
                 --labels data/hover/candidates/sets/pool-3.json --out results/tax-7

Reads two mappings of the same taxonomy (N = the sample, M = the domain) and
writes stability.json and a README. Judge outputs only: no gold is read.

Adapted from results/hover/profile-stability/scripts/stability.py to read the
data/ layout; the statistics are unchanged. Pure standard library.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path


def mean(v): return sum(v) / len(v) if v else float("nan")


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
    return float("nan") if sx == 0 or sy == 0 else sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def spearman(x, y): return pearson(ranks(x), ranks(y))


def load(mapping_dir: Path):
    """-> {candidate_id: {task_id: {code: count}}}, judged traces only."""
    out = defaultdict(dict); bad = 0
    for line in open(mapping_dir / "mapping.jsonl"):
        d = json.loads(line)
        if d["status"] != "judged":
            bad += 1; continue
        out[d["candidate_id"]][d["task_id"]] = d["codes"] or {}
    return dict(out), bad


def profile(byc, cand, tasks, codes):
    t = [byc[cand][x] for x in tasks if x in byc[cand]]
    n = len(t) or 1
    return [sum(d.get(c, 0) for d in t) / n for c in codes]


def l1_abs(a, b): return sum(abs(x - y) for x, y in zip(a, b))


def l1_share(a, b):
    sa, sb = sum(a) or 1.0, sum(b) or 1.0
    return sum(abs(x / sa - y / sb) for x, y in zip(a, b))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-map", type=Path, required=True)
    ap.add_argument("--m-map", type=Path, required=True)
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--labels", type=Path, required=True, help="candidate set file with an aliases map")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--half-splits", type=int, default=400)
    ap.add_argument("--seed", type=int, default=5)
    a = ap.parse_args()

    tax = json.loads(a.taxonomy.read_text())
    codes = [c["id"] for c in tax["codes"]]
    names = {c["id"]: c["name"] for c in tax["codes"]}
    aliases = json.loads(a.labels.read_text()).get("aliases", {})
    lab = lambda c: aliases.get(c, c)
    n_id = json.loads((a.n_map / "manifest.json").read_text())["mapping_id"]
    m_id = json.loads((a.m_map / "manifest.json").read_text())["mapping_id"]

    N, nbad = load(a.n_map)
    M, mbad = load(a.m_map)
    cands = sorted(set(N) & set(M))
    if not cands:
        raise SystemExit("no candidate has judged traces in both mappings")
    ntask = {c: sorted(N[c]) for c in cands}
    mtask = {c: sorted(M[c]) for c in cands}
    ntasks = sorted(set().union(*ntask.values()))
    mtasks = sorted(set().union(*mtask.values()))
    nmin, nmax = min(len(v) for v in ntask.values()), max(len(v) for v in ntask.values())
    mmin, mmax = min(len(v) for v in mtask.values()), max(len(v) for v in mtask.values())
    rng = random.Random(a.seed)

    pN = {c: profile(N, c, ntask[c], codes) for c in cands}
    pM = {c: profile(M, c, mtask[c], codes) for c in cands}

    ksz = {c: min(len(ntask[c]), len(mtask[c])) for c in cands}
    k = min(ksz.values())
    degenerate = any(ksz[c] > 0.9 * len(mtask[c]) for c in cands)
    floor_l1, floor_rate = [], defaultdict(list)
    for _ in range(a.draws):
        for c in cands:
            q = list(mtask[c]); rng.shuffle(q)
            lo, hi = q[:ksz[c]], q[ksz[c]:]
            if not hi:
                continue
            p, pr = profile(M, c, lo, codes), profile(M, c, hi, codes)
            floor_l1.append(l1_share(p, pr))
            for i, cd in enumerate(codes):
                floor_rate[cd].append(abs(p[i] - pr[i]))

    half = defaultdict(list); half_ident = []
    for _ in range(a.half_splits):
        pa, pb = {}, {}
        for c in cands:
            q = list(ntask[c]); rng.shuffle(q); h = len(q) // 2
            pa[c] = profile(N, c, q[:h], codes); pb[c] = profile(N, c, q[h:], codes)
        for i, cd in enumerate(codes):
            r = spearman([pa[c][i] for c in cands], [pb[c][i] for c in cands])
            if r == r:
                half[cd].append(r)
        half_ident.append(mean([min(((l1_share(pa[c], pb[o]), o) for o in cands))[1] == c for c in cands]))
    reliability = {cd: (pct(half[cd], 50) if half[cd] else None) for cd in codes}

    percode = {}
    for i, cd in enumerate(codes):
        xn = [pN[c][i] for c in cands]; xm = [pM[c][i] for c in cands]
        percode[cd] = {"name": names[cd], "rate_N": mean(xn), "rate_M": mean(xm),
                       "spearman_across_candidates": spearman(xn, xm),
                       "mean_abs_diff": mean([abs(p - q) for p, q in zip(xn, xm)]),
                       "sampling_floor_p95": pct(floor_rate[cd], 95),
                       "half_split_reliability_on_N": reliability[cd]}

    perprof = {c: {"l1_share_N_vs_M": l1_share(pN[c], pM[c])} for c in cands}
    band = (pct(floor_l1, 50), pct(floor_l1, 95))
    inside = sum(perprof[c]["l1_share_N_vs_M"] <= band[1] for c in cands)

    hits, ident = 0, {}
    for c in cands:
        d = sorted(((l1_share(pN[c], pM[o]), o) for o in cands))
        ident[c] = {"nearest": d[0][1], "own_distance": l1_share(pN[c], pM[c]),
                    "nearest_distance": d[0][0], "own_rank": [o for _, o in d].index(c) + 1}
        hits += d[0][1] == c
    ceil_hits, ceil_n = 0, 0
    for _ in range(min(a.draws, 200)):
        for c in cands:
            p = profile(M, c, rng.sample(mtask[c], ksz[c]), codes)
            ceil_hits += min(((l1_share(p, pM[o]), o) for o in cands))[1] == c
            ceil_n += 1

    def ident_rate(sub, dist):
        idx = [codes.index(c) for c in sub]; hit = 0
        for c in cands:
            pa = [pN[c][i] for i in idx]
            best = min(((dist(pa, [pM[o][i] for i in idx]), o) for o in cands))[1]
            hit += best == c
        return hit / len(cands)

    top = max(codes, key=lambda c: percode[c]["rate_N"])
    rest = [c for c in codes if c != top]
    carriers = {"most_frequent_code": top,
                "full_profile_abs": ident_rate(codes, l1_abs),
                "top_code_alone_abs": ident_rate([top], l1_abs),
                "without_top_code_abs": ident_rate(rest, l1_abs) if rest else None,
                "without_top_code_share": ident_rate(rest, l1_share) if rest else None,
                "drop_one": {c: ident_rate([x for x in codes if x != c], l1_share) for c in codes}}

    res = {"n_map": n_id, "m_map": m_id, "taxonomy": str(a.taxonomy),
           "codes": len(codes), "candidates": len(cands), "candidate_labels": {c: lab(c) for c in cands},
           "tasks": {"N_union": len(ntasks), "M_union": len(mtasks),
                     "per_candidate_N": {"min": nmin, "max": nmax}, "per_candidate_M": {"min": mmin, "max": mmax}},
           "unjudged_traces": {"N": nbad, "M": mbad},
           "half_split_on_N": {"draws": a.half_splits, "subset_size": len(ntasks) // 2,
                               "identity_mean": mean(half_ident), "reliability": reliability},
           "per_code": percode, "per_profile": perprof,
           "sampling_floor_l1": {"median": band[0], "p95": band[1], "draws": a.draws,
                                 "subsample_size": k, "degenerate": degenerate},
           "profiles_inside_floor": f"{inside}/{len(cands)}",
           "identity": ident, "identity_top1": hits / len(cands),
           "identity_top1_ceiling_from_sampling_alone": ceil_hits / ceil_n,
           "identity_chance": 1 / len(cands), "carriers": carriers, "seed": a.seed}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "stability.json").write_text(json.dumps(res, indent=1) + "\n")

    L = []; w = L.append
    w(f"# Failure-profile stability — {len(codes)} codes ({n_id} against {m_id})\n")
    w(f"{len(cands)} candidates. N = `{n_id}`: {nmin}–{nmax} judged tasks per candidate, {len(ntasks)} distinct. "
      f"M = `{m_id}`: {mmin}–{mmax} judged tasks per candidate, {len(mtasks)} distinct. "
      f"Judge outputs only; no gold was read.\n")
    if degenerate:
        w("> **The noise floor is degenerate**: at least one candidate has too little M to subsample. "
          "Only the identity test in section 3 is readable.\n")
    w("Each candidate is profiled on its own judged tasks. The noise floor comes from "
      f"{a.draws:,} disjoint splits of each candidate's M tasks into {k} versus the rest: how far a "
      "profile moves between two non-overlapping task samples of the same candidate.\n")
    w("## 0. Which codes can be stable at all?\n")
    w(f"{a.half_splits} random half-splits of each candidate's N tasks (~{nmin // 2} vs ~{nmin - nmin // 2}), "
      "both halves from the same pool. This is not transfer; it is the ceiling transfer could reach.\n")
    w("| code | name | rate/trace on N | half-split ρ |"); w("|---|---|---:|---:|")
    for cd in sorted(codes, key=lambda c: -percode[c]["rate_N"]):
        r = reliability[cd]
        w(f"| {cd} | {percode[cd]['name'][:34]} | {percode[cd]['rate_N']:.3f} | " + (f"{r:+.3f} |" if r is not None else "never fires |"))
    w(f"\nWhole-profile identity within N: {mean(half_ident):.1%} (chance {1/len(cands):.1%}).\n")
    w("## 1. Per-code rates, N vs M\n")
    w("| code | name | rate on N | rate on M | ρ across candidates | mean abs diff | sampling floor (p95) | reliability on N |")
    w("|---|---|---:|---:|---:|---:|---:|---:|")
    for cd in codes:
        p = percode[cd]; flag = "" if p["mean_abs_diff"] <= p["sampling_floor_p95"] else " ⚠"
        r = p["half_split_reliability_on_N"]
        w(f"| {cd} | {p['name'][:34]} | {p['rate_N']:.3f} | {p['rate_M']:.3f} | {p['spearman_across_candidates']:+.3f} | "
          f"{p['mean_abs_diff']:.3f}{flag} | {p['sampling_floor_p95']:.3f} | " + (f"{r:+.3f} |" if r is not None else "— |"))
    w("\n⚠ marks a code whose N-vs-M gap exceeds what sampling alone explains.\n")
    w("## 2. Whole-profile shape\n")
    w(f"L1 distance between share vectors. Sampling floor: median {band[0]:.3f}, 95th percentile {band[1]:.3f}.\n")
    w(f"**{inside} of {len(cands)} candidates** sit inside the sampling floor.\n")
    w("| candidate | L1(N, M) | inside floor |"); w("|---|---:|---|")
    for c in cands:
        v = perprof[c]["l1_share_N_vs_M"]; w(f"| {lab(c)} | {v:.3f} | {'yes' if v <= band[1] else 'no'} |")
    w("\n## 3. Identity: is a candidate's nearest M profile its own?\n")
    w("| | rate |"); w("|---|---:|")
    w(f"| N profile finds its own candidate | **{hits}/{len(cands)} = {hits/len(cands):.1%}** |")
    w(f"| ceiling: a {k}-task subsample of M finds its own | {res['identity_top1_ceiling_from_sampling_alone']:.1%} |")
    w(f"| chance | {1/len(cands):.1%} |"); w("")
    w("| candidate | nearest M profile | own distance | rank of own |"); w("|---|---|---:|---:|")
    for c in cands:
        i = ident[c]
        w(f"| {lab(c)} | {lab(i['nearest'])}{' ✓' if i['nearest'] == c else ''} | {i['own_distance']:.3f} | {i['own_rank']} |")
    w("\n## 4. What carries the identity?\n")
    w("| profile | identity |"); w("|---|---:|")
    w(f"| all {len(codes)} codes, absolute rates | {carriers['full_profile_abs']:.1%} |")
    w(f"| all {len(codes)} codes, shares only | {hits/len(cands):.1%} |")
    w(f"| {top} alone (most frequent, {percode[top]['rate_N']:.2f}/trace) | {carriers['top_code_alone_abs']:.1%} |")
    if rest:
        w(f"| without {top}, absolute | {carriers['without_top_code_abs']:.1%} |")
        w(f"| without {top}, shares | {carriers['without_top_code_share']:.1%} |")
    w(f"| chance | {1/len(cands):.1%} |")
    w("\nDrop-one-code, shares:\n"); w("| code dropped | identity |"); w("|---|---:|")
    for c, v in sorted(carriers["drop_one"].items(), key=lambda kv: kv[1])[:6]:
        w(f"| {c} ({names[c][:30]}) | {v:.1%} |")
    (a.out / "README.md").write_text("\n".join(L) + "\n")
    print(f"{n_id} vs {m_id}: identity {hits}/{len(cands)}, inside floor {inside}/{len(cands)}, "
          f"median per-code ρ {pct([percode[c]['spearman_across_candidates'] for c in codes if percode[c]['spearman_across_candidates']==percode[c]['spearman_across_candidates']], 50):+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
