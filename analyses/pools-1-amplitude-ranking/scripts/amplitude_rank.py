#!/usr/bin/env python3
"""Base failure amplitude from the judged sample, ranked against gold on the judging and generalization pools.

    python3 analyses/pools-1-amplitude-ranking/scripts/amplitude_rank.py

Amplitude A(c) = mean over the candidate's judged traces of the number of DISTINCT codes the
panel assigned (lower is better); a judged trace with no code contributes 0. Read from the
mapping rows (repeat 0, judged status only). Gold rankings are candidate means of repeat-0
scores over (a) the judged tasks, (b) the whole judging pool, (c) the generalization pool.
Kendall tau-b with a permutation p over 12 candidates. Gold is used only as the target here.
"""
from __future__ import annotations
import json, sys, itertools, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pools-1-rank-agreement" / "scripts"))
from rank_agreement import REPO, load, means, tau_b, perm_p, spearman  # noqa: E402

MAPS = {"hover": [("map-3", "tax-18"), ("map-1", "tax-7")], "ifbench": [("map-1", "tax-1")], "hotpotqa": [("map-1", "tax-1")]}


def amplitude(b, mid):
    rows = [json.loads(l) for l in open(REPO / "data" / b / "mappings" / mid / "mapping.jsonl")]
    per = {}
    for r in rows:
        if r["status"] != "judged" or int(r.get("repeat", 0)) != 0: continue
        per.setdefault(r["candidate_id"], []).append(len(r.get("codes") or {}))
    tasks = {r["task_id"] for r in rows}
    return {c: sum(v) / len(v) for c, v in per.items()}, tasks, sum(1 for r in rows if r["status"] == "judged" and not r.get("codes"))


def main():
    out = {}
    for b, maps in MAPS.items():
        per, _ = load(b); G = {p: means(per[p]) for p in ("judging", "generalization")}
        for mid, tid in maps:
            A, tasks, silent = amplitude(b, mid); cands = sorted(A)
            assert len(cands) == 12
            gj50 = {c: sum(per["judging"][c][t] for t in tasks if t in per["judging"][c]) / sum(1 for t in tasks if t in per["judging"][c]) for c in cands}
            score = [-A[c] for c in cands]   # lower amplitude = better, so negate for a "higher is better" comparison
            res = {}
            for name, g in (("gold on the 50 judged tasks", gj50), ("gold on the whole judging pool", G["judging"]), ("gold on the generalization pool", G["generalization"])):
                y = [g[c] for c in cands]; res[name] = (tau_b(score, y), perm_p(score, y), spearman(score, y))
            gj = [G["judging"][c] for c in cands]; g50 = [gj50[c] for c in cands]; gg = [G["generalization"][c] for c in cands]
            res["gold judging pool vs gold generalization"] = (tau_b(gj, gg), perm_p(gj, gg), spearman(gj, gg))
            res["gold 50 judged tasks vs gold generalization"] = (tau_b(g50, gg), perm_p(g50, gg), spearman(g50, gg))
            print(f"\n== {b} {mid} ({tid}): amplitude over {len(tasks)} judged tasks x 12 candidates; judged traces with no code: {silent}")
            print(f"   amplitude by candidate (lower is better): " + ", ".join(f"{c[-6:]} {A[c]:.2f}" for c in sorted(cands, key=A.get)))
            print(f"   {'comparison':48s} {'tau-b':>7s} {'p':>7s} {'rho':>7s}")
            for k, (t, p, r) in res.items(): print(f"   {k:48s} {t:+7.3f} {p:7.4f} {r:+7.3f}")
            out[f"{b}/{mid}"] = {"taxonomy": tid, "amplitude": A, "judged_tasks": len(tasks), "silent_traces": silent, "kendall": {k: {"tau_b": t, "p": p, "spearman": r} for k, (t, p, r) in res.items()}}
    (REPO / "analyses" / "pools-1-amplitude-ranking" / "results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
