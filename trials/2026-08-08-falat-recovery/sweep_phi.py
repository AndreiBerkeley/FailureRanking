#!/usr/bin/env python3
"""Why did Phi v0 beat Phi v0.1? Three offline probes over the rebuilt
annotations (no API calls, no gold inside any scoring path):

  1. delta x w0 sweep      — is v0.1's shortfall a hyperparameter artifact?
  2. recovery ablation     — does the recovery term help or hurt the ranking?
  3. prevalence-only floor — how much comes from mode counts alone?

Gold is loaded only to score the resulting rankings, after the fact.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "../2026-08-07-legacy-hover-phi-harness"))
from phi_harness import phi_v0, phi_v01, kendall_tau  # noqa: E402
from score_phi import build_phi_inputs, load_gold, TAXONOMY  # noqa: E402


def strip_recovery(tasks):
    """Same mode presence, every occurrence marked unrecovered."""
    return {t: {m: ["unrecovered"] for m in modes} for t, modes in tasks.items()}


def rank_tau(score_fn, cands, gold):
    names = sorted(cands)
    scores = [score_fn(cands[c]) for c in names]
    return kendall_tau(scores, [gold[c] for c in names])


def main():
    K = len(json.loads(TAXONOMY.read_text())["codes"])
    cands, _ = build_phi_inputs()
    _, g300 = load_gold()

    print("=== 1. delta x w0 sweep, Phi v0.1 vs gold-300 ===")
    print("  w0/delta" + "".join(f"{d:>8}" for d in (0.1, 0.3, 0.5, 0.7, 0.9)))
    best = (None, -2)
    for w0 in (0.1, 0.2, 0.3, 0.5, 0.7, 0.9):
        row = []
        for delta in (0.1, 0.3, 0.5, 0.7, 0.9):
            t = rank_tau(lambda tk, d=delta, w=w0: phi_v01(tk, len(tk), d, w)[0],
                         cands, g300)
            row.append(t)
            if t > best[1]:
                best = ((w0, delta), t)
        print(f"{w0:>9}" + "".join(f"{t:>+8.3f}" for t in row))
    print(f"  best v0.1 cell: w0={best[0][0]}, delta={best[0][1]} -> {best[1]:+.3f}")

    print("\n=== 2. delta sweep, Phi v0 vs gold-300 ===")
    for delta in (0.1, 0.3, 0.5, 0.7, 0.9):
        t = rank_tau(lambda tk, d=delta: phi_v0(tk, len(tk), K, d)[0], cands, g300)
        print(f"  delta={delta}: {t:+.3f}")

    print("\n=== 3. recovery ablation (recovery term removed) ===")
    stripped = {c: strip_recovery(t) for c, t in cands.items()}
    for name, fn in (("v0  ", lambda tk: phi_v0(tk, len(tk), K, 0.5)[0]),
                     ("v0.1", lambda tk: phi_v01(tk, len(tk), 0.5, 0.5)[0])):
        with_rec = rank_tau(fn, cands, g300)
        without = rank_tau(fn, stripped, g300)
        print(f"  {name}: with recovery {with_rec:+.3f} | "
              f"without {without:+.3f} | recovery contributes {with_rec-without:+.3f}")

    print("\n=== 4. prevalence-only floor (fewest modes wins) ===")
    t = rank_tau(lambda tk: -sum(len(m) for m in tk.values()) / len(tk), cands, g300)
    print(f"  -mean modes/task vs gold-300: {t:+.3f}")

    print("\n  outcome-only baseline: +0.439")


if __name__ == "__main__":
    main()
