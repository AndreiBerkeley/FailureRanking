#!/usr/bin/env python3
"""Exact-pattern entries: a task's whole code set is one entry, sub-combinations do not count.

    python3 analyses/pools-1-amplitude-ranking/scripts/patterns.py

For a candidate, pattern p = the exact set of codes on a task; rate_p = tasks with exactly that set / 50.
  any          sum of rates of non-empty patterns  (= share of tasks with any failure)
  distinct     number of distinct non-empty patterns
  recurring    number of non-empty patterns seen on >= 2 tasks
  recur_mass   share of tasks whose pattern recurs on >= 2 tasks
  mean_size    mean size of the pattern over tasks (= amplitude, for reference)
Lower is better. Kendall tau-b (permutation p) against gold on the 50 judged tasks and on the generalization pool.
"""
from __future__ import annotations
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p  # noqa: E402

MAPS = {"hover": ("map-3", "tax-18"), "ifbench": ("map-1", "tax-1"), "hotpotqa": ("map-1", "tax-1")}


def main():
    for b, (mid, tid) in MAPS.items():
        per, _ = load(b); Gg = means(per["generalization"])
        rows = [json.loads(l) for l in open(REPO / "data" / b / "mappings" / mid / "mapping.jsonl")]
        rows = [r for r in rows if r["status"] == "judged" and int(r.get("repeat", 0)) == 0]
        cands = sorted({r["candidate_id"] for r in rows}); tasks = sorted({r["task_id"] for r in rows}); T = len(tasks)
        pat = {c: collections.Counter() for c in cands}
        for r in rows: pat[r["candidate_id"]][frozenset(r.get("codes") or {})] += 1
        S = {"any": {c: sum(n for p, n in pat[c].items() if p) / T for c in cands},
             "distinct": {c: sum(1 for p in pat[c] if p) for c in cands},
             "recurring": {c: sum(1 for p, n in pat[c].items() if p and n >= 2) for c in cands},
             "recur_mass": {c: sum(n for p, n in pat[c].items() if p and n >= 2) / T for c in cands},
             "mean_size": {c: sum(len(p) * n for p, n in pat[c].items()) / T for c in cands}}
        g50 = {c: sum(per["judging"][c][t] for t in tasks) / T for c in cands}
        x50 = [g50[c] for c in cands]; xg = [Gg[c] for c in cands]
        d = [S["distinct"][c] for c in cands]; rm = [S["recur_mass"][c] for c in cands]
        print(f"\n== {b} ({mid}, {tid}): distinct non-empty patterns per candidate {min(d)}–{max(d)} of 50 tasks; share of tasks whose pattern recurs {min(rm):.2f}–{max(rm):.2f}; gold50 vs gold gen {tau_b(x50, xg):+.2f}")
        print(f"   {'reading':11s} {'range':>13s}  {'gold50 vs judge50':>19s}  {'gold gen vs judge50':>20s}")
        for name, sc in S.items():
            s = [-sc[c] for c in cands]
            print(f"   {name:11s} {min(sc.values()):5.2f}–{max(sc.values()):5.2f}  {tau_b(s, x50):+.2f} (p={perm_p(s, x50):.3f})     {tau_b(s, xg):+.2f} (p={perm_p(s, xg):.3f})")
        # the most common patterns overall, to see what recurs
        allp = collections.Counter()
        for c in cands:
            for p, n in pat[c].items(): allp[p] += n
        tax = {x["id"]: x["name"] for x in json.load(open(REPO / "data" / b / "taxonomies" / tid / "taxonomy.json"))["codes"]}
        print("   most common patterns across all candidates:", [(" + ".join(tax[x][:18] for x in sorted(p)) or "(none)", n) for p, n in allp.most_common(4)])


if __name__ == "__main__":
    main()
