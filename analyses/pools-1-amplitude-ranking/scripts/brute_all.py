#!/usr/bin/env python3
"""Every counting ("brute") method, on every benchmark/taxonomy mapping we hold.

    python3 analyses/pools-1-amplitude-ranking/scripts/brute_all.py

All methods read only the codes the panel assigned per task (repeat 0, judged traces), never an
outcome. Each is lower-is-better and is compared with gold by Kendall tau-b (permutation p),
against gold on the same judged tasks and against gold on the generalization pool.

k_t = distinct codes on task t; r_m = share of the candidate's judged tasks carrying code m.
  amplitude    mean_t k_t                  = sum_m r_m
  any          mean_t 1[k_t >= 1]          = the full inclusion-exclusion series, and the
                                             sum of exact-pattern rates: all three coincide
  saturate     mean_t (1 - 2^-k_t)
  cap3         mean_t min(k_t,3)/3
  pie_pairs    mean_t (k_t - C(k_t,2))     inclusion-exclusion truncated after pairs
  combos_all   mean_t (2^k_t - 1)          every sub-combination counts
  combos_recur as above, combinations seen on >= 2 of the candidate's tasks only
  combos_wt    sum_S p_S^2                 each combination weighted by its own rate
  breadth      # codes with r_m > 0
  worst        max_m r_m
  persistent   # codes with r_m >= 0.2
  pat_distinct # distinct non-empty exact patterns
  pat_recur    # exact patterns seen on >= 2 tasks
  pat_mass     share of tasks whose exact pattern recurs
"""
from __future__ import annotations
import json, sys, math, itertools, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p  # noqa: E402

CONFIGS = [("hover", "map-3", "tax-18"), ("hover", "map-5", "tax-10"),
           ("ifbench", "map-1", "tax-1"), ("hotpotqa", "map-1", "tax-1")]
ORDER = ["amplitude", "any", "saturate", "cap3", "pie_pairs", "combos_all", "combos_recur",
         "combos_wt", "breadth", "worst", "persistent", "pat_distinct", "pat_recur", "pat_mass"]


def scores(rows, cands):
    """method -> {candidate: score}, all lower-is-better."""
    by = {c: [] for c in cands}                       # per candidate, list of code-sets per task
    for r in rows: by[r["candidate_id"]].append(frozenset(r["codes"] or {}))
    out = {m: {} for m in ORDER}
    for c, sets in by.items():
        T = len(sets); ks = [len(s) for s in sets]
        rate = collections.Counter()
        for s in sets:
            for m in s: rate[m] += 1
        rate = {m: v / T for m, v in rate.items()}
        combo = collections.Counter()
        for s in sets:
            for r_ in range(1, len(s) + 1):
                for x in itertools.combinations(sorted(s), r_): combo[x] += 1
        pat = collections.Counter(sets)
        out["amplitude"][c] = sum(ks) / T
        out["any"][c] = sum(1 for k in ks if k) / T
        out["saturate"][c] = sum(1 - 2.0 ** -k for k in ks) / T
        out["cap3"][c] = sum(min(k, 3) / 3 for k in ks) / T
        out["pie_pairs"][c] = sum(k - math.comb(k, 2) for k in ks) / T
        out["combos_all"][c] = sum(2 ** k - 1 for k in ks) / T
        out["combos_recur"][c] = sum(n for n in combo.values() if n >= 2) / T
        out["combos_wt"][c] = sum((n / T) ** 2 for n in combo.values())
        out["breadth"][c] = len(rate)
        out["worst"][c] = max(rate.values()) if rate else 0.0
        out["persistent"][c] = sum(1 for v in rate.values() if v >= 0.2)
        out["pat_distinct"][c] = sum(1 for p in pat if p)
        out["pat_recur"][c] = sum(1 for p, n in pat.items() if p and n >= 2)
        out["pat_mass"][c] = sum(n for p, n in pat.items() if p and n >= 2) / T
    return out


def main():
    res, meta = {}, {}
    for b, mid, tid in CONFIGS:
        per, _ = load(b); Gg = means(per["generalization"])
        rows = [json.loads(l) for l in open(REPO / "data" / b / "mappings" / mid / "mapping.jsonl")]
        rows = [r for r in rows if r["status"] == "judged" and int(r.get("repeat", 0)) == 0]
        cands = sorted({r["candidate_id"] for r in rows}); tasks = sorted({r["task_id"] for r in rows})
        g50 = {c: sum(per["judging"][c][t] for t in tasks) / len(tasks) for c in cands}
        x50 = [g50[c] for c in cands]; gg = [Gg[c] for c in cands]
        S = scores(rows, cands)
        key = f"{b}/{tid}"
        meta[key] = {"mapping": mid, "traces": len(rows), "tasks": len(tasks), "candidates": len(cands),
                     "codes": len(json.load(open(REPO / "data" / b / "taxonomies" / tid / "taxonomy.json"))["codes"]),
                     "ceiling_tau": tau_b(x50, gg), "ceiling_p": perm_p(x50, gg)}
        res[key] = {}
        for m in ORDER:
            s = [-S[m][c] for c in cands]
            res[key][m] = {"gold50": tau_b(s, x50), "gold50_p": perm_p(s, x50),
                           "gen": tau_b(s, gg), "gen_p": perm_p(s, gg)}
    keys = list(res)
    print("mapping, size and the ceiling gold on the judged tasks reaches against the generalization pool\n")
    print(f"  {'benchmark / taxonomy':22s} {'mapping':8s} {'codes':>5s} {'traces':>6s} {'tasks':>5s}  {'ceiling':>15s}")
    for k in keys:
        m = meta[k]; print(f"  {k:22s} {m['mapping']:8s} {m['codes']:5d} {m['traces']:6d} {m['tasks']:5d}  {m['ceiling_tau']:+.2f} (p={m['ceiling_p']:.3f})")
    for target, lab in (("gen", "gold on the GENERALIZATION pool"), ("gold50", "gold on the SAME judged tasks")):
        print(f"\n\nKendall tau-b against {lab}\n")
        print(f"  {'method':13s} " + "  ".join(f"{k:>21s}" for k in keys))
        for m in ORDER:
            print(f"  {m:13s} " + "  ".join(f"{res[k][m][target]:+7.2f} (p={res[k][m][target + '_p']:.3f})" for k in keys))
    (REPO / "analyses/pools-1-amplitude-ranking/brute_all.json").write_text(json.dumps({"meta": meta, "results": res}, indent=1))


if __name__ == "__main__":
    main()
