#!/usr/bin/env python3
"""Task-first bounded amplitude on the judged samples: per-task blame in [0,1], mean over tasks.

    python3 analyses/pools-1-amplitude-ranking/scripts/bounded_amplitude.py

Variants of blame(t) from k_t = distinct codes the panel assigned on task t (outcome-free):
  any        1 if k_t >= 1 else 0                (fraction of tasks with a failure)
  saturate   1 - 2^(-k_t)                        (1 code = 0.5, 2 = 0.75, 3 = 0.875, ...)
  cap3       min(k_t, 3) / 3                     (linear up to three mechanisms, then full)
Compared by Kendall tau-b with gold on the 50 judged tasks and gold on the generalization pool.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p  # noqa: E402

MAPS = {"hover": ("map-3", "tax-18"), "ifbench": ("map-1", "tax-1"), "hotpotqa": ("map-1", "tax-1")}
BLAME = {"any": lambda k: 1.0 if k else 0.0, "saturate": lambda k: 1 - 2.0 ** (-k), "cap3": lambda k: min(k, 3) / 3}


def main():
    print(f"{'benchmark':9s} {'variant':9s} {'score range':>13s}  {'gold50 vs judge50':>19s}  {'gold gen vs judge50':>20s}  {'gold50 vs gold gen':>18s}")
    for b, (mid, tid) in MAPS.items():
        per, _ = load(b); Gg = means(per["generalization"])
        rows = [json.loads(l) for l in open(REPO / "data" / b / "mappings" / mid / "mapping.jsonl")]
        rows = [r for r in rows if r["status"] == "judged" and int(r.get("repeat", 0)) == 0]
        cands = sorted({r["candidate_id"] for r in rows}); tasks = {r["task_id"] for r in rows}
        g50 = {c: sum(per["judging"][c][t] for t in tasks) / len(tasks) for c in cands}
        x50 = [g50[c] for c in cands]; xg = [Gg[c] for c in cands]; base = f"{tau_b(x50, xg):+.2f} (p={perm_p(x50, xg):.3f})"
        for name, f in BLAME.items():
            blame = {c: [] for c in cands}
            for r in rows: blame[r["candidate_id"]].append(f(len(r.get("codes") or {})))
            S = {c: sum(v) / len(v) for c, v in blame.items()}; s = [-S[c] for c in cands]   # lower blame = better
            rng = f"{min(S.values()):.2f}–{max(S.values()):.2f}"
            print(f"{b:9s} {name:9s} {rng:>13s}  {tau_b(s, x50):+.2f} (p={perm_p(s, x50):.3f})     {tau_b(s, xg):+.2f} (p={perm_p(s, xg):.3f})      {base}")


if __name__ == "__main__":
    main()
