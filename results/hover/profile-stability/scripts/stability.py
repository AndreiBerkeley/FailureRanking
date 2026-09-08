#!/usr/bin/env python3
"""Does a candidate's failure distribution stay the same on new tasks?

    stability.py --n-run results/hover/judge-tax2-judging \
                 --m-run results/hover/judge-tax2-generalization \
                 --taxonomy runs/taxgen-v4/hover/taxonomy_v2.json \
                 --out results/hover/profile-stability/tax-7

"Stays the same" is meaningless without a noise floor. A code that fires 0.08
times per trace produces ~4 hits across a candidate's 50 traces, and that count
moves a long way between task samples for reasons that have nothing to do with
the candidate. So every number here is reported against what *sampling alone*
would produce: the M-side profile is repeatedly subsampled down to N's size,
and the resulting spread is the band a real difference has to clear.

Four questions, in increasing sharpness:

  0. reliability before transfer is even asked: split N in half and check
                 whether a code reproduces itself across task samples drawn
                 from the SAME pool. A code that cannot do that has no
                 stability to transfer, and its N-vs-M agreement is luck
                 either way.
  1. per-code    does each code fire at the same rate on N and on M?
  2. per-profile is a candidate's whole 7- or 18-vector the same on N and M,
                 relative to how much a 50-task draw moves it anyway?
  3. identity    given a candidate's profile on N, is the nearest M profile its
                 own? This is the strongest form of "the profile is a property
                 of the candidate, not of the task sample". Chance is 1/12.
  4. carriers    is that identity distributed across the taxonomy, or does one
                 frequent code do all the work? A signature resting on a single
                 code is a thinner claim than one resting on the shape.

Section 4 scores single codes with an unnormalised metric. A one-element share
vector is always [1.0], so l1_share is identically zero across every pair and
the comparison would be vacuous.

Every candidate is profiled on **its own** judged tasks rather than on tasks
judged for all twelve. The corpus is ordered by content hash, so a partial run
holds a random subset of (candidate, task) pairs and the all-twelve
intersection is empty until nearly every trace is done -- requiring it would
throw away a complete partial run. Differing task samples add sampling noise to
cross-candidate comparisons, and that is exactly the noise the floor models, so
the floor subsamples each candidate independently to match.

Reads only judge outputs and never gold. Works on a partial M run (it says so).
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path


def mean(v): return sum(v) / len(v) if v else 0.0


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


def load(run: Path):
    """-> {candidate: {task: {code: count}}}, only judged traces."""
    out: dict[int, dict[str, dict[str, int]]] = defaultdict(dict)
    bad = 0
    for f in sorted((run / "traces").glob("*.json")):
        d = json.loads(f.read_text())
        if d.get("status") != "judged":
            bad += 1
            continue
        out[d["candidate_index"]][d["task_id"]] = d.get("codes") or {}
    return dict(out), bad


def profile(byc, cand, tasks, codes):
    """Per-trace firing rate for each code, over the given tasks."""
    t = [byc[cand][x] for x in tasks if x in byc[cand]]
    n = len(t) or 1
    return [sum(d.get(c, 0) for d in t) / n for c in codes]


def l1_abs(a, b):
    """Absolute rate difference. Unlike l1_share this stays meaningful for a
    single code, where shares carry no information at all."""
    return sum(abs(x - y) for x, y in zip(a, b))


def l1_share(a, b):
    """L1 between two profiles as *shares*, so it measures shape, not volume."""
    sa, sb = sum(a) or 1.0, sum(b) or 1.0
    return sum(abs(x / sa - y / sb) for x, y in zip(a, b))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-run", type=Path, required=True)
    ap.add_argument("--m-run", type=Path, required=True)
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--draws", type=int, default=1000, help="subsamples of M for the noise floor")
    ap.add_argument("--half-splits", type=int, default=400,
                    help="random half-splits of N for the reliability section")
    ap.add_argument("--seed", type=int, default=5)
    a = ap.parse_args()

    tax = json.loads(a.taxonomy.read_text())
    codes = [c["id"] for c in tax["codes"]]
    names = {c["id"]: c["name"] for c in tax["codes"]}

    N, nbad = load(a.n_run)
    M, mbad = load(a.m_run)
    cands = sorted(set(N) & set(M))
    if not cands:
        raise SystemExit("no candidate has judged traces in both runs yet")
    # Per-candidate task sets: see the module docstring.
    ntask = {c: sorted(N[c]) for c in cands}
    mtask = {c: sorted(M[c]) for c in cands}
    ntasks = sorted(set().union(*ntask.values()))
    mtasks = sorted(set().union(*mtask.values()))
    nmin, nmax = min(len(v) for v in ntask.values()), max(len(v) for v in ntask.values())
    mmin, mmax = min(len(v) for v in mtask.values()), max(len(v) for v in mtask.values())
    # No fixed expectation for |M|: the output directory may hold traces from
    # more than one run over the same corpus. Report what is there.
    partial = False
    rng = random.Random(a.seed)

    pN = {c: profile(N, c, ntask[c], codes) for c in cands}
    pM = {c: profile(M, c, mtask[c], codes) for c in cands}

    # ---- noise floor: subsample M to N's size, many times -----------------
    # Each candidate's M sample is cut to the size of its own N sample.
    ksz = {c: min(len(ntask[c]), len(mtask[c])) for c in cands}
    k = min(ksz.values())
    # A subsample of size k drawn from a pool of size k is the pool: zero
    # variance, and a floor of 0 that every real gap "fails". Say so rather
    # than print a meaningless band.
    degenerate = any(ksz[c] > 0.9 * len(mtask[c]) for c in cands)
    floor_l1, floor_rate = [], defaultdict(list)
    for _ in range(a.draws):
        for c in cands:
            q = list(mtask[c]); rng.shuffle(q)
            lo, hi = q[:ksz[c]], q[ksz[c]:]        # disjoint halves, never overlapping
            if not hi:
                continue
            p, pr = profile(M, c, lo, codes), profile(M, c, hi, codes)
            floor_l1.append(l1_share(p, pr))
            for i, cd in enumerate(codes):
                floor_rate[cd].append(abs(p[i] - pr[i]))

    # ---- 0. can a code reproduce itself within N at all? ------------------
    half = defaultdict(list); half_ident = []
    for _ in range(a.half_splits):
        pa, pb = {}, {}
        for c in cands:
            q = list(ntask[c]); rng.shuffle(q); h = len(q) // 2
            pa[c] = profile(N, c, q[:h], codes)
            pb[c] = profile(N, c, q[h:], codes)
        for i, cd in enumerate(codes):
            r = spearman([pa[c][i] for c in cands], [pb[c][i] for c in cands])
            if r == r:
                half[cd].append(r)
        half_ident.append(mean([min(((l1_share(pa[c], pb[o]), o) for o in cands))[1] == c
                                for c in cands]))
    reliability = {cd: (pct(half[cd], 50) if half[cd] else None) for cd in codes}

    # ---- 1. per-code ------------------------------------------------------
    percode = {}
    for i, cd in enumerate(codes):
        xn = [pN[c][i] for c in cands]; xm = [pM[c][i] for c in cands]
        percode[cd] = {
            "name": names[cd],
            "rate_N": mean(xn), "rate_M": mean(xm),
            "spearman_across_candidates": spearman(xn, xm),
            "mean_abs_diff": mean([abs(p - q) for p, q in zip(xn, xm)]),
            "sampling_floor_p95": pct(floor_rate[cd], 95),
            "half_split_reliability_on_N": reliability[cd],
        }

    # ---- 2. per-profile ---------------------------------------------------
    perprof = {c: {"l1_share_N_vs_M": l1_share(pN[c], pM[c])} for c in cands}
    band = (pct(floor_l1, 50), pct(floor_l1, 95))
    inside = sum(perprof[c]["l1_share_N_vs_M"] <= band[1] for c in cands)

    # ---- 3. identity ------------------------------------------------------
    hits, ident = 0, {}
    for c in cands:
        d = sorted(((l1_share(pN[c], pM[o]), o) for o in cands))
        ident[c] = {"nearest": d[0][1], "own_distance": l1_share(pN[c], pM[c]),
                    "nearest_distance": d[0][0],
                    "own_rank_of_12": [o for _, o in d].index(c) + 1}
        hits += d[0][1] == c
    # the same test using only sampling noise: does a 50-task subsample of M
    # identify its own candidate? that is the ceiling this test can reach.
    ceil_hits, ceil_n = 0, 0
    for _ in range(min(a.draws, 200)):
        for c in cands:
            p = profile(M, c, rng.sample(mtask[c], ksz[c]), codes)
            ceil_hits += min(((l1_share(p, pM[o]), o) for o in cands))[1] == c
            ceil_n += 1

    # ---- 4. what carries the identity? -----------------------------------
    def ident_rate(sub, dist):
        idx = [codes.index(c) for c in sub]
        hit = 0
        for c in cands:
            pa = [pN[c][i] for i in idx]
            best = min(((dist(pa, [pM[o][i] for i in idx]), o) for o in cands))[1]
            hit += best == c
        return hit / len(cands)

    top = max(codes, key=lambda c: percode[c]["rate_N"])
    rest = [c for c in codes if c != top]
    carriers = {
        "most_frequent_code": top,
        "full_profile_abs": ident_rate(codes, l1_abs),
        "top_code_alone_abs": ident_rate([top], l1_abs),
        "without_top_code_abs": ident_rate(rest, l1_abs) if rest else None,
        "without_top_code_share": ident_rate(rest, l1_share) if rest else None,
        "drop_one": {c: ident_rate([x for x in codes if x != c], l1_share)
                     for c in codes},
    }

    res = {
        "n_run": str(a.n_run), "m_run": str(a.m_run), "taxonomy": str(a.taxonomy),
        "codes": len(codes), "candidates": len(cands),
        "tasks": {"N_union": len(ntasks), "M_union": len(mtasks),
                  "per_candidate_N": {"min": nmin, "max": nmax},
                  "per_candidate_M": {"min": mmin, "max": mmax}},
        "unjudged_traces": {"N": nbad, "M": mbad},
        "partial_M": partial,
        "half_split_on_N": {"draws": a.half_splits,
                            "subset_size": len(ntasks) // 2,
                            "identity_mean": mean(half_ident),
                            "reliability": reliability},
        "per_code": percode,
        "per_profile": perprof,
        "sampling_floor_l1": {"median": band[0], "p95": band[1],
                              "draws": a.draws, "subsample_size": k,
                              "degenerate": degenerate},
        "profiles_inside_floor": f"{inside}/{len(cands)}",
        "identity": ident,
        "identity_top1": hits / len(cands),
        "identity_top1_ceiling_from_sampling_alone": ceil_hits / ceil_n,
        "identity_chance": 1 / len(cands),
        "carriers": carriers,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "stability.json").write_text(json.dumps(res, indent=1) + "\n")

    L = []; w = L.append
    w(f"# Failure-profile stability — {len(codes)} codes\n")
    w(f"M covers **{len(mtasks)} distinct tasks**, {mmin}–{mmax} per candidate. If that "
      f"exceeds the task set you filtered to, the output directory also holds traces "
      f"from an earlier run over the same corpus; they are the same instrument on the "
      f"same pool and are included deliberately.\n")
    if degenerate:
        worst = min(cands, key=lambda c: len(mtask[c]) - ksz[c])
        w(f"> **The noise floor is degenerate and every floor comparison below is")
        w(f"> meaningless.** The floor cuts each candidate's M sample to the size of its")
        w(f"> N sample, but at least one candidate has too little M to cut: cand_{worst:02d}")
        w(f"> has {len(mtask[worst])} M tasks and a subsample size of {ksz[worst]}, so its")
        w(f"> 'subsample' is essentially the whole set and contributes zero spread.")
        w(f"> Only the identity test in section 3 is readable until every candidate has")
        w(f"> several times more M tasks than N tasks.\n")
    w(f"{len(cands)} candidates. N: {nmin}–{nmax} tasks per candidate. "
      f"M: {mmin}–{mmax} tasks per candidate. Judge outputs only; no gold was read.\n")
    w("Each candidate is profiled on its own judged tasks, not on tasks judged for all")
    w("twelve — the corpus is hash-ordered, so a partial run has an empty all-twelve")
    w("intersection. The floor subsamples each candidate independently to match.\n")
    w(f"The noise floor comes from {a.draws:,} disjoint splits of each candidate's M "
      f"tasks into {k} versus the rest: that is how far a profile moves between two "
      f"non-overlapping task samples of the same candidate.\n")
    w("## 0. Which codes can be stable at all?\n")
    w(f"{a.half_splits} random half-splits of each candidate's N tasks "
      f"(~{nmin // 2} vs ~{nmin - nmin // 2}), both halves from the same pool. This is not")
    w("transfer — it is the ceiling transfer could reach. A code that fails here has")
    w("no stability to lose.\n")
    w("| code | name | rate/trace on N | half-split ρ |")
    w("|---|---|---:|---:|")
    for cd in sorted(codes, key=lambda c: -percode[c]["rate_N"]):
        r = reliability[cd]
        w(f"| {cd} | {percode[cd]['name'][:34]} | {percode[cd]['rate_N']:.3f} | "
          + (f"{r:+.3f} |" if r is not None else "never fires |"))
    w(f"\nWhole-profile identity within N: {mean(half_ident):.1%} "
      f"(chance {1/len(cands):.1%}).\n")
    w("## 1. Per-code rates, N vs M\n")
    w("| code | name | rate on N | rate on M | ρ across candidates | mean abs diff |"
      " sampling floor (p95) | reliability on N |")
    w("|---|---|---:|---:|---:|---:|---:|---:|")
    for cd in codes:
        p = percode[cd]
        flag = "" if p["mean_abs_diff"] <= p["sampling_floor_p95"] else " ⚠"
        r = p["half_split_reliability_on_N"]
        w(f"| {cd} | {p['name'][:34]} | {p['rate_N']:.3f} | {p['rate_M']:.3f} | "
          f"{p['spearman_across_candidates']:+.3f} | {p['mean_abs_diff']:.3f}{flag} | "
          f"{p['sampling_floor_p95']:.3f} | "
          + (f"{r:+.3f} |" if r is not None else "— |"))
    w("\n⚠ marks a code whose N-vs-M gap exceeds what sampling alone explains.\n")
    w("## 2. Whole-profile shape\n")
    w(f"L1 distance between share vectors. Sampling floor: median "
      f"{band[0]:.3f}, 95th percentile {band[1]:.3f}.\n")
    w(f"**{inside} of {len(cands)} candidates** sit inside the sampling floor.\n")
    w("| candidate | L1(N, M) | inside floor |")
    w("|---|---:|---|")
    for c in cands:
        v = perprof[c]["l1_share_N_vs_M"]
        w(f"| cand_{c:02d} | {v:.3f} | {'yes' if v <= band[1] else 'no'} |")
    w("\n## 3. Identity: is a candidate's nearest M profile its own?\n")
    w(f"| | rate |")
    w(f"|---|---:|")
    w(f"| N profile finds its own candidate | **{hits}/{len(cands)} = {hits/len(cands):.1%}** |")
    w(f"| ceiling: a {k}-task subsample of M finds its own | "
      f"{res['identity_top1_ceiling_from_sampling_alone']:.1%} |")
    w(f"| chance | {1/len(cands):.1%} |")
    w("")
    w("| candidate | nearest M profile | own distance | rank of own |")
    w("|---|---|---:|---:|")
    for c in cands:
        i = ident[c]
        w(f"| cand_{c:02d} | cand_{i['nearest']:02d}"
          f"{' ✓' if i['nearest'] == c else ''} | {i['own_distance']:.3f} | "
          f"{i['own_rank_of_12']} |")
    w("\n## 4. What carries the identity?\n")
    w("A signature resting on one frequent code is a thinner claim than one resting")
    w("on the shape. Single codes are scored by absolute rate difference: a one-code")
    w("*share* vector is always [1.0], which would make that row vacuous.\n")
    w("| profile | identity |")
    w("|---|---:|")
    w(f"| all {len(codes)} codes, absolute rates | {carriers['full_profile_abs']:.1%} |")
    w(f"| all {len(codes)} codes, shares only | {hits/len(cands):.1%} |")
    w(f"| {top} alone (most frequent, {percode[top]['rate_N']:.2f}/trace) | "
      f"{carriers['top_code_alone_abs']:.1%} |")
    if rest:
        w(f"| without {top}, absolute | {carriers['without_top_code_abs']:.1%} |")
        w(f"| without {top}, shares | {carriers['without_top_code_share']:.1%} |")
    w(f"| chance | {1/len(cands):.1%} |")
    w("\nDrop-one-code, shares:\n")
    w("| code dropped | identity |")
    w("|---|---:|")
    for c, v in sorted(carriers["drop_one"].items(), key=lambda kv: kv[1])[:6]:
        w(f"| {c} ({names[c][:30]}) | {v:.1%} |")
    (a.out / "README.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\n-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
