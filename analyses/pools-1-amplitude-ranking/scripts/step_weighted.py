#!/usr/bin/env python3
"""Step-weighted amplitude on HoVer: weight a firing by which step it happened at. Outcome-free.

    python3 analyses/pools-1-amplitude-ranking/scripts/step_weighted.py

A_w(c) = (1/T) * sum over judged tasks of sum over (code, step) firings of w[step], lower better.
Weights are fixed before looking at any target. Gold is read only to validate, against the
500-task generalization pool (disjoint from every judging task by construction).

Attribution: 'placed' = both readers put the code on that turn; 'any' = at least one did.
"""
from __future__ import annotations
import json, gzip, glob, sys, random, collections, statistics as st
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p  # noqa: E402

AG = ["summarize1", "create_query_hop2", "summarize2", "create_query_hop3"]
Q, S = {"create_query_hop2", "create_query_hop3"}, {"summarize1", "summarize2"}


def firings(mapping, codes, min_votes):
    """(candidate, task, [steps]) per trace."""
    out = []
    for f in sorted(glob.glob(str(REPO / "data" / "hover" / "mappings" / mapping / "judge_records/*.jsonl.gz"))):
        with gzip.open(f, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                if r["status"] != "judged": continue
                ev = []
                for tk, v in (r.get("votes_by_turn") or {}).items():
                    step = tk.split(":", 1)[1]
                    ev += [step for m, x in v.items() if x >= min_votes and m in codes]
                out.append((r["candidate_id"], r["trace_id"], ev))
    return out


def score(ev, w):
    n = collections.Counter(); s = collections.Counter()
    for c, _, steps in ev: n[c] += 1; s[c] += sum(w.get(x, 0.0) for x in steps)
    return {c: s[c] / n[c] for c in n}


def report(name, ev, w, cands, gg, boot_units):
    S = score(ev, w); x = [-S[c] for c in cands]
    rng = random.Random(2026); bs = []
    for _ in range(1000):
        smp = [rng.choice(boot_units) for _ in boot_units]
        by = collections.defaultdict(list)
        for c, t, steps in ev: by[t] = (c, steps)
        acc = collections.Counter(); cnt = collections.Counter()
        for t in smp:
            c, steps = by[t]; cnt[c] += 1; acc[c] += sum(w.get(x, 0.0) for x in steps)
        bs.append(tau_b([-acc[c] / cnt[c] if cnt[c] else 0 for c in cands], gg))
    bs.sort()
    kept = sum(sum(1 for x in steps if w.get(x, 0.0) > 0) for _, _, steps in ev)
    print(f"   {name:34s} tau {tau_b(x, gg):+.2f} (p={perm_p(x, gg):.3f})  95% CI [{bs[25]:+.2f}, {bs[974]:+.2f}]  firings used {kept}")


def main():
    per, _ = load("hover"); Gg = means(per["generalization"])
    for mapping, tid in (("map-5", "tax-10"), ("map-3", "tax-18")):
        codes = {c["id"] for c in json.load(open(REPO / "data/hover/taxonomies" / tid / "taxonomy.json"))["codes"]}
        for rule, mv in (("placed (both readers on the turn)", 2), ("any reader", 1)):
            ev = firings(mapping, codes, mv)
            cands = sorted({c for c, _, _ in ev}); gg = [Gg[c] for c in cands]
            traces = [t for _, t, _ in ev]
            print(f"\n== hover {mapping} ({tid}), {rule} ==")
            for name, w in (("all four steps equal (baseline)", {a: 1.0 for a in AG}),
                            ("queries only", {a: (1.0 if a in Q else 0.0) for a in AG}),
                            ("summarizers only", {a: (1.0 if a in S else 0.0) for a in AG}),
                            ("queries 1.5x, summarizers 1x", {a: (1.5 if a in Q else 1.0) for a in AG}),
                            ("hop3 only (the terminal act)", {a: (1.0 if a == "create_query_hop3" else 0.0) for a in AG})):
                report(name, ev, w, cands, gg, traces)
            print(f"   {'query multiplier sweep:':34s} " + "  ".join(
                f"{k}x {tau_b([-v for v in score(ev, {a: (k if a in Q else 1.0) for a in AG}).values()], gg):+.2f}"
                for k in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0)))


if __name__ == "__main__":
    main()
