#!/usr/bin/env python3
"""Error analysis: which modes are mis-weighted, and which pairs did we
get wrong because of them?

Gold is used ONLY here, after Phi has scored, to measure each mode's real
outcome-link and to decompose ranking errors (hard rule 3: validation and
offline calibration, never inside the scoring path).

  1. per-mode outcome-link: gold pass rate when a mode is present vs absent
  2. charged-vs-earned: Phi's charge (prevalence, equal weights) against
     that measured influence -> over- and under-weighted modes
  3. pair inversions: for each candidate pair Phi orders wrongly, which
     mode's prevalence gap drove it
  4. ceiling: Phi with outcome-link weights (gold-calibrated regime only)
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "../2026-08-07-legacy-hover-phi-harness"))
import phi_harness as ph  # noqa: E402
from score_phi import build_phi_inputs, load_gold, TAXONOMY, RUN  # noqa: E402

DELTA, W0 = 0.5, 0.5


def per_task_gold():
    """{candidate: {task: 0/1}} at seed 0 — the executions Phi scored."""
    out = {}
    for cdir in sorted((RUN / "evaluation/gold_do_not_pass_to_judge").glob("candidate_*")):
        rep0 = {}
        for f in cdir.glob("*.json"):
            d = json.loads(f.read_text())
            if d["evaluation_repeat"] == 0:
                rep0[d["task"]["source_id"]] = d["gold_score"]
        out[cdir.name] = rep0
    return out


def main():
    tax = json.loads(TAXONOMY.read_text())
    names = {c["id"]: c["name"] for c in tax["codes"]}
    K = len(tax["codes"])
    cands, _ = build_phi_inputs()
    tg = per_task_gold()
    _, g300 = load_gold()

    # ---------- 1. per-mode outcome link (pooled over all candidates/tasks)
    stats = defaultdict(lambda: {"with": [], "without": []})
    for c, tasks in cands.items():
        for t, modes in tasks.items():
            gold = tg[c][t]
            present = set(modes)
            for m in names:
                stats[m]["with" if m in present else "without"].append(gold)
    print("=== 1. per-mode outcome link (seed-0 gold, pooled 600 tasks) ===")
    print(f"{'code':>6} {'tasks':>6} {'pass|present':>13} {'pass|absent':>12} "
          f"{'delta':>7}  name")
    link = {}
    rows = []
    for m in names:
        w, wo = stats[m]["with"], stats[m]["without"]
        if not w or not wo:
            continue
        pw, pwo = 100 * sum(w) / len(w), 100 * sum(wo) / len(wo)
        link[m] = pwo - pw          # positive = mode presence predicts failure
        rows.append((m, len(w), pw, pwo, pwo - pw))
    for m, n, pw, pwo, d in sorted(rows, key=lambda r: -r[4]):
        print(f"{m:>6} {n:>6} {pw:>12.1f}% {pwo:>11.1f}% {d:>+7.1f}  {names[m]}")

    # ---------- 2. charged vs earned
    print("\n=== 2. charged (Phi, equal weights) vs earned (outcome link) ===")
    prev = {m: sum(1 for t in cands.values() for mm in t.values() if m in mm)
            for m in names}
    tot_prev = sum(prev.values()) or 1
    tot_link = sum(max(0, link.get(m, 0)) * prev[m] for m in names) or 1
    print(f"{'code':>6} {'charge%':>8} {'earned%':>8} {'ratio':>7}  verdict")
    for m in sorted(names, key=lambda m: -prev[m]):
        if m not in link or prev[m] == 0:
            continue
        charge = 100 * prev[m] / tot_prev
        earned = 100 * max(0, link[m]) * prev[m] / tot_link
        ratio = charge / earned if earned > 0.01 else float("inf")
        verdict = ("OVER-charged" if ratio > 1.6 else
                   "under-charged" if ratio < 0.6 else "ok")
        e = f"{earned:>7.1f}%" if earned > 0.01 else "    ~0%"
        r = f"{ratio:>7.2f}" if ratio != float("inf") else "    inf"
        print(f"{m:>6} {charge:>7.1f}% {e} {r}  {verdict}")

    # ---------- 3. which pairs did Phi get wrong, and why
    print("\n=== 3. inverted candidate pairs (Phi v0.1 vs gold-300) ===")
    scores = {c: ph.phi_v01(t, len(t), DELTA, W0)[0] for c, t in cands.items()}
    modes_per = {c: {m: sum(1 for mm in t.values() if m in mm) / len(t)
                     for m in names} for c, t in cands.items()}
    names_s = sorted(cands)
    inversions = []
    for i in range(len(names_s)):
        for j in range(i + 1, len(names_s)):
            a, b = names_s[i], names_s[j]
            if (scores[a] - scores[b]) * (g300[a] - g300[b]) < 0:
                inversions.append((a, b))
    print(f"  {len(inversions)} inverted pairs of {len(names_s)*(len(names_s)-1)//2}")
    blame = defaultdict(float)
    for a, b in inversions:
        # Phi preferred whoever scored higher; gold disagreed.
        hi, lo = (a, b) if scores[a] > scores[b] else (b, a)
        for m in names:
            gap = modes_per[lo][m] - modes_per[hi][m]   # why Phi punished `lo`
            if gap > 0:
                blame[m] += gap * max(0.0, 1 - max(0, link.get(m, 0)) / 20)
    print("  modes most responsible (prevalence gap x weak outcome link):")
    for m, v in sorted(blame.items(), key=lambda kv: -kv[1])[:6]:
        print(f"    {m:>6} {v:>6.2f}  link {link.get(m,0):+5.1f}  {names[m]}")

    # ---------- 4. ceiling with outcome-link weights (gold-calibrated only)
    print("\n=== 4. ceiling: Phi with outcome-link weights (CALIBRATED, not gold-free) ===")
    wts = {m: max(0.0, link.get(m, 0)) for m in names}
    mx = max(wts.values()) or 1
    wts = {m: 0.05 + 0.95 * v / mx for m, v in wts.items()}

    def phi_weighted(tasks):
        import math
        aff, rec = ph.per_mode_rates(tasks)
        q = {m: wts.get(m, 0.5) * W0 * (DELTA ** (rec.get(m, 0) / a))
             for m, a in aff.items()}
        b = [1 - math.prod(1 - q[m] for m in mm) for mm in tasks.values()]
        return 100 * (1 - sum(b) / len(tasks))

    t_eq = ph.kendall_tau([scores[c] for c in names_s], [g300[c] for c in names_s])
    t_w = ph.kendall_tau([phi_weighted(cands[c]) for c in names_s],
                         [g300[c] for c in names_s])
    print(f"  equal weights   : {t_eq:+.3f}")
    print(f"  outcome weights : {t_w:+.3f}   (upper bound; weights fit on the target)")
    print("  baselines: outcome-only +0.439 | prevalence-only +0.561")


if __name__ == "__main__":
    main()
