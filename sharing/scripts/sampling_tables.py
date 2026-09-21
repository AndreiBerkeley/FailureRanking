#!/usr/bin/env python3
"""results_ablation.md: how the formulas' agreement with the generalization set moves with the judged
tasks (how many, which) and with the generalization tasks (how many, which).

    python3 sharing/scripts/sampling_tables.py --out sharing/results_ablation.md

A. judged-side sweep: k tasks drawn uniformly from the judged set, 10 draws (seeds 1-10), the
   same draws for every formula; gold-k on the same draw is the bar. k = 10, 20, 30, 50 and the
   larger sets where judged (100 on Models·HoVer, 100 and 150 on LiveCodeBench).
B. generalization-side resampling: the full judged set fixed; m tasks drawn from the
   generalization set, 10 draws; gold-judged vs gen-m is the bar. m = 100, 300, full.
C. disjoint replication: the same formulas on non-overlapping judged sets of 50.

Formulas: gold, incidence, amplitude, damped PIE (β = 0.5), containment; on the recovery
side the same on unrecovered points plus recovery-weighted amplitude (γ = 3). Every kept point
counts (a point no code fit is its own pseudo-code). Definitions in formulas.md; the
formula code is shared with results_tables.py. Offline; no model call.
"""
from __future__ import annotations
import argparse, glob, json, math, random, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from results_tables import formulas, recovery_formulas, taub, gold_from, RECOVERED, UNC  # noqa: E402

DRAWS = 10
COLS = ["incidence", "amplitude", "damped PIE, β=0.5", "containment"]
RW = "recovery-weighted amplitude, γ=3"

EXPERIMENTS = [
    dict(title="GEPA candidates · HoVer", cands="12 GEPA-optimised prompt sets",
         all_points=[("runs/new_pipeline/hover/pointjudge-1-tax15", "runs/new_pipeline/hover/pool_judged50")],
         recovery=[("runs/new_pipeline/hover/recovery-2-tax15", "runs/new_pipeline/hover/pool_judged50")],
         gold_judged=("jsonl", "data/hover/outcomes/cap-2.jsonl"), gold_gen=("jsonl", "data/hover/outcomes/cap-3.jsonl"),
         gen_name="500 tasks", ks=[10, 20, 30, 50], ms=[100, 300], disjoint=None),
    dict(title="Models · HoVer", cands="9 models behind the same program",
         all_points=[("runs/new_pipeline/hover-models/pointjudge-1-sp15", "runs/new_pipeline/hover-models/pool_judging"),
                     ("runs/new_pipeline/hover-models/pointjudge-3", "runs/new_pipeline/hover-models/pool_judging")],
         recovery=[("runs/new_pipeline/hover-models/recovery-1", "runs/new_pipeline/hover-models/pool_judging")],
         gold_judged=("jsonl", "data/hover/outcomes/cap-7.jsonl"), gold_gen=("jsonl", "data/hover/outcomes/cap-8.jsonl"),
         gen_name="500 tasks", ks=[10, 20, 30, 50, 100], ms=[100, 300],
         disjoint=[("set a", "data/hover/splits/models-1-judged-50/split.json:judged"), ("set b", "data/hover/splits/models-1-judged-50-b/split.json:judged")],
         note="all points: judged sets a and b pooled (100 tasks, one taxonomy, one judge); recovery: set b only (50 tasks)"),
    dict(title="Models · LiveCodeBench", cands="9 models behind the same program",
         all_points=[("runs/new_pipeline/lcb-models/pointjudge-2", "runs/new_pipeline/lcb-models/pool_judging150")],
         recovery=[],
         gold_judged=("pool", "runs/new_pipeline/lcb-models/pool_judging150"), gold_gen=("pool", "runs/new_pipeline/lcb-models/pool_generalization"),
         gen_name="755 tasks", ks=[10, 20, 30, 50, 100, 150], ms=[100, 300],
         disjoint=[("set 1", "data/livecodebench/splits/judging-50-1/split.json:judging"), ("set 2", "data/livecodebench/splits/judging-100-1/split.json:judging:0"),
                   ("set 3", "data/livecodebench/splits/judging-100-1/split.json:judging:1")],
         note="no recovery pass exists on this benchmark; all-points side only"),
]


def load_runs(runs, with_verdicts):
    """candidate -> task -> [(turn, codes, recovered?)], and candidate -> task -> last turn"""
    pts = defaultdict(dict); last = defaultdict(dict)
    for run, pool in runs:
        inv = {v: k for k, v in json.load(open(f"{pool}/pool_manifest.json"))["candidate_index"].items()}
        for f in glob.glob(f"{run}/traces/*.json"):
            d = json.load(open(f))
            if d.get("status") != "judged": continue
            c = inv[d["candidate_index"]]; t = d["task_id"]
            pts[c][t] = [(q["turn"], list(q.get("codes") or [UNC]), (q.get("recovery") in RECOVERED) if with_verdicts else False) for q in d["points"]]
            last[c][t] = max(x["turn"] for x in d["turns"])
    active = sorted(pts); tasks = sorted(pts[active[0]])
    assert all(sorted(pts[c]) == tasks for c in active), "candidates judged on different tasks"
    return active, tasks, pts, last


def split_tasks(spec, all_tasks):
    path, portion, *half = spec.split(":"); ts = sorted(set(json.load(open(path))["portions"][portion]) & set(all_tasks))
    if half:
        rng = random.Random(0); rng.shuffle(ts); n = len(ts) // 2
        ts = ts[:n] if half[0] == "0" else ts[n:]
    return sorted(ts)


def scores_on(active, tasks, pts, last, GJ, unrec, with_rw):
    sub_pts = {c: {t: pts[c][t] for t in tasks} for c in active}
    M = formulas(active, tasks, sub_pts, last, unrec)
    out = {"gold": {c: -sum(GJ[c][t] for t in tasks) / len(tasks) for c in active}}
    for k in COLS: out[k] = M[k]
    if with_rw: out[RW] = recovery_formulas(active, tasks, sub_pts, GJ)[RW]
    return out


def fmt(vals):
    vals = [v for v in vals if not math.isnan(v)]
    if not vals: return "—"
    return f"{sum(vals)/len(vals):+.2f}" if len(vals) == 1 else f"{sum(vals)/len(vals):+.2f} ({min(vals):+.2f}…{max(vals):+.2f})"


def sweep_table(active, tasks, pts, last, GJ, gg, ks, unrec, with_rw):
    cols = ["gold"] + COLS + ([RW] if with_rw else [])
    L = ["| k | draws | " + " | ".join(cols) + " |", "|---:|---:|" + "---:|" * len(cols)]
    for k in ks:
        if k > len(tasks): continue
        draws = [sorted(tasks)] if k == len(tasks) else [sorted(random.Random(seed).sample(tasks, k)) for seed in range(1, DRAWS + 1)]
        taus = defaultdict(list); beats = defaultdict(int)
        for dr in draws:
            S = scores_on(active, dr, pts, last, GJ, unrec, with_rw)
            tg = {name: taub(S[name], gg, active)[0] for name in cols}
            for name in cols:
                taus[name].append(tg[name])
                if name != "gold" and not math.isnan(tg[name]) and tg[name] >= tg["gold"]: beats[name] += 1
        cells = [fmt(taus["gold"])] + [f"{fmt(taus[n])} · ≥bar {beats[n]}/{len(draws)}" if len(draws) > 1 else fmt(taus[n]) for n in cols[1:]]
        L.append(f"| {k} | {len(draws)} | " + " | ".join(cells) + " |")
    return L


def gen_table(active, tasks, pts, last, GJ, GG, ms, unrec, with_rw):
    cols = ["gold"] + COLS + ([RW] if with_rw else [])
    S = scores_on(active, tasks, pts, last, GJ, unrec, with_rw)
    gen_tasks = sorted(GG[active[0]])
    L = ["| m | draws | " + " | ".join(cols) + " |", "|---:|---:|" + "---:|" * len(cols)]
    for m in ms + [len(gen_tasks)]:
        if m > len(gen_tasks): continue
        draws = [gen_tasks] if m == len(gen_tasks) else [random.Random(seed).sample(gen_tasks, m) for seed in range(1, DRAWS + 1)]
        taus = defaultdict(list)
        for dr in draws:
            ggm = {c: sum(GG[c][t] for t in dr) / len(dr) for c in active}
            for name in cols: taus[name].append(taub(S[name], ggm, active)[0])
        L.append(f"| {m} | {len(draws)} | " + " | ".join(fmt(taus[n]) for n in cols) + " |")
    return L


def disjoint_table(active, pts, last, GJ, gg, sets, unrec, with_rw):
    cols = ["gold"] + COLS + ([RW] if with_rw else [])
    L = ["| judged set | tasks | " + " | ".join(cols) + " |", "|---|---:|" + "---:|" * len(cols)]
    for name, ts in sets:
        S = scores_on(active, ts, pts, last, GJ, unrec, with_rw)
        L.append(f"| {name} | {len(ts)} | " + " | ".join(f"{taub(S[n], gg, active)[0]:+.2f}" for n in cols) + " |")
    return L


def render(exp):
    A_active, A_tasks, A_pts, A_last = load_runs(exp["all_points"], False)
    GJ = gold_from(exp["gold_judged"], A_active); GG = gold_from(exp["gold_gen"], A_active)
    gg = {c: sum(GG[c].values()) / len(GG[c]) for c in A_active}
    L = [f"## {exp['title']}", "", f"- candidates: {exp['cands']} ({len(A_active)}); generalization set: {exp['gen_name']}"]
    if exp.get("note"): L.append(f"- {exp['note']}")
    L += ["", f"### A. Judged-side sweep — all points (judged set: {len(A_tasks)} tasks)", "",
          "Each cell: mean tau vs gen gold over the draws (min…max) · how many draws land at or above the gold bar of the same draw.", ""]
    L += sweep_table(A_active, A_tasks, A_pts, A_last, GJ, gg, exp["ks"], False, False)
    if exp["recovery"]:
        R_active, R_tasks, R_pts, R_last = load_runs(exp["recovery"], True)
        L += ["", f"### A. Judged-side sweep — unrecovered points (judged set with recovery: {len(R_tasks)} tasks)", ""]
        L += sweep_table(R_active, R_tasks, R_pts, R_last, GJ, gg, exp["ks"], True, True)
    L += ["", f"### B. Generalization-side resampling — full judged set, all points", "",
          "Each cell: mean tau of the full-judged-set scores vs the gold of m generalization tasks (min…max).", ""]
    L += gen_table(A_active, A_tasks, A_pts, A_last, GJ, GG, exp["ms"], False, False)
    if exp["recovery"]:
        L += ["", f"### B. Generalization-side resampling — full judged set, unrecovered points", ""]
        L += gen_table(R_active, R_tasks, R_pts, R_last, GJ, GG, exp["ms"], True, True)
    if exp["disjoint"]:
        sets = [(n, split_tasks(spec, A_tasks)) for n, spec in exp["disjoint"]]
        L += ["", "### C. Disjoint judged sets — all points", "", "tau vs gen gold, one row per set; no overlap between the sets.", ""]
        L += disjoint_table(A_active, A_pts, A_last, GJ, gg, sets, False, False)
        if exp["recovery"]:
            rsets = [(n, [t for t in ts if t in R_tasks]) for n, ts in sets]; rsets = [(n, ts) for n, ts in rsets if len(ts) == len(R_tasks)]
            if rsets:
                L += ["", "### C. Disjoint judged sets — unrecovered points (the sets with recovery)", ""]
                L += disjoint_table(R_active, R_pts, R_last, GJ, gg, rsets, True, True)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("sharing/results_ablation.md")); a = ap.parse_args()
    parts = ["# Sampling: how the results move with the tasks", "",
             "Two independent axes. **A** changes the tasks the formula reads (how many, which); **B** changes the tasks the target is built from;",
             "**C** replaces the judged set with a disjoint one of the same size. Every draw is uniform without replacement, 10 draws (seeds 1–10),",
             "the same draws for every formula in a table, so formulas are compared on identical task sets. tau-b with ties dropped; the gold column",
             "is the bar computed on the same draw. Formulas as in `formulas.md`, every kept point counted. Generated by `scripts/sampling_tables.py`.", ""]
    for exp in EXPERIMENTS: parts += [render(exp), ""]
    a.out.write_text("\n".join(parts)); print(f"-> {a.out}")


if __name__ == "__main__":
    main()
