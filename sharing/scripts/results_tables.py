#!/usr/bin/env python3
"""results.md: per experiment, the formulas of formulas.md on the tasks that have recovery results.

    python3 sharing/scripts/results_tables.py --out sharing/results.md

Table 1: every point the judge kept (no recovery anywhere).  Table 2: the same formulas on the
unrecovered points only, plus the three recovery-dependent formulas.  Columns: tau-b vs the
judged tasks' own gold, top-1 vs it; tau-b vs the generalization set's gold, top-1 and top-3
overlap vs it; resolved pairs (ties dropped on either side).  All offline; no model call.

Points are read from the recovery run's records (the judge's points with a verdict each).
A point the judge kept but no code fit is reported both ways: "every kept point" gives it its
own pseudo-code `(uncoded)`; "coded points only" drops it. The profile formulas (breadth, worst
mode, patterns) read codes and so have one row.
"""
from __future__ import annotations
import argparse, glob, itertools, json, math
from collections import defaultdict
from pathlib import Path

RECOVERED = ("corrected", "contained", "made_irrelevant")
UNC = "(uncoded)"
SUPPORT_MIN = 3   # a unit seen on fewer tasks than this takes the candidate's overall recovery share (as in methods/scripts/recovery_weighted.py)

EXPERIMENTS = [
    dict(key="gepa_hover", title="GEPA candidates · HoVer", candidates="12 GEPA-optimised prompt sets",
         recovery="runs/new_pipeline/hover/recovery-2-tax15", pool="runs/new_pipeline/hover/pool_judged50",
         gold_judged=("jsonl", "data/hover/outcomes/cap-2.jsonl"), gold_gen=("jsonl", "data/hover/outcomes/cap-3.jsonl"),
         gen_name="eval-1 domain, 500 tasks", names=None, drop=(),
         judge="readers gpt-5.6-luna ×2, decider gpt-5.6-sol; success rule in view", rec="claude-sonnet-5; success rule in view",
         taxonomy="GEPA_Candidates_HoVer_taxonomy.json (15 codes, 2 hand-authored)"),
    dict(key="models_hover", title="Models · HoVer (judged set b)", candidates="9 models behind the same program",
         recovery="runs/new_pipeline/hover-models/recovery-1", pool="runs/new_pipeline/hover-models/pool_judging",
         gold_judged=("jsonl", "data/hover/outcomes/cap-7.jsonl"), gold_gen=("jsonl", "data/hover/outcomes/cap-8.jsonl"),
         gen_name="models-1 generalization, 500 tasks", names="data/hover/candidates/sets/models-1.json", drop=(),
         judge="readers gemini-3.6-flash ×2, decider claude-sonnet-5; before the success rule", rec="claude-sonnet-5; before the success rule",
         taxonomy="Models_HoVer_taxonomy.json (15 codes, 1 hand-authored)"),
    dict(key="models_tb", title="Models · Terminal-Bench 2.0", candidates="7 models behind the Terminus 2 agent",
         recovery="runs/new_pipeline/terminalbench/recovery-1", pool="runs/new_pipeline/terminalbench/pool_judged20_frontier7",
         gold_judged=("pool", "runs/new_pipeline/terminalbench/pool_judged20_frontier7"), gold_gen=("pool", "runs/new_pipeline/terminalbench/pool_eval69_frontier7"),
         gen_name="pools-1 eval, 69 tasks", names="data/terminalbench/candidates/sets/terminus2-1.json", drop=("vulnerable-secret",),
         judge="readers gpt-5.6-luna ×2, decider gpt-5.6-sol; success rule in view", rec="claude-sonnet-5; success rule in view",
         taxonomy="Models_TerminalBench_taxonomy.json (10 codes)"),
]


def gold_from(spec, active):
    kind, src = spec; d = defaultdict(dict)
    if kind == "jsonl":
        for line in open(src):
            r = json.loads(line)
            if r["candidate_id"] in active: d[r["candidate_id"]][r["task_id"]] = r["score"]
    else:
        sc = json.load(open(f"{src}/outcomes.json"))["scores"]
        for p in glob.glob(f"{src}/*.json"):
            if p.endswith(("outcomes.json", "pool_manifest.json")): continue
            t = json.load(open(p)); m = t["metadata"]
            if m["candidate_id"] in active: d[m["candidate_id"]][m["task_id"]] = sc[t["trace_id"]]
    return d


def load(exp):
    inv = {v: k for k, v in json.load(open(f"{exp['pool']}/pool_manifest.json"))["candidate_index"].items()}
    label = {}
    if exp["names"]:
        cs = json.load(open(exp["names"])); sm = cs.get("solver_models") or {}
        label = {c: (sm[c] if isinstance(sm, dict) else sm[i]) for i, c in enumerate(cs["candidate_ids"])} if sm else {}
    recs = []
    for f in glob.glob(f"{exp['recovery']}/traces/*.json"):
        d = json.load(open(f))
        if d.get("status") != "judged" or d["task_id"] in exp["drop"]: continue
        recs.append(d)
    active = sorted({inv[r["candidate_index"]] for r in recs})
    # per candidate per task: points as (turn, codes, recovered?) ; last turn
    pts = defaultdict(dict); last = defaultdict(dict)
    for r in recs:
        c = inv[r["candidate_index"]]; t = r["task_id"]
        pts[c][t] = [(q["turn"], list(q.get("codes") or [UNC]), (q.get("recovery") in RECOVERED)) for q in r["points"]]
        last[c][t] = max(x["turn"] for x in r["turns"])
    tasks = sorted(pts[active[0]])
    assert all(sorted(pts[c]) == tasks for c in active), "candidates judged on different tasks"
    GJ = gold_from(exp["gold_judged"], active); GG = gold_from(exp["gold_gen"], active)
    assert all(t in GJ[c] for c in active for t in tasks), "a judged task has no gold row"
    return active, tasks, pts, last, GJ, GG, label


def formulas(active, tasks, pts, last, unrec_only):
    """name -> {candidate: score}, lower is better."""
    T = len(tasks)
    def sel(c, t): return [p for p in pts[c][t] if not (unrec_only and p[2])]
    codes = {c: {t: {m for p in sel(c, t) for m in p[1]} for t in tasks} for c in active}
    fir = {c: {t: {(p[0], m) for p in sel(c, t) for m in p[1]} for t in tasks} for c in active}
    coded = {c: {t: {m for m in codes[c][t] if m != UNC} for t in tasks} for c in active}
    def rate(c, m): return sum(1 for t in tasks if m in coded[c][t]) / T
    allm = sorted({m for c in active for t in tasks for m in coded[c][t]})
    def con(c):
        tot = 0
        for t in tasks:
            turns = {s for s, _ in fir[c][t]}
            for s, m in fir[c][t]:
                if s == last[c][t] or any(s2 > s for s2 in turns): tot += 1
        return tot / T
    M = {}
    M["incidence"] = {c: sum(1 for t in tasks if codes[c][t]) / T for c in active}
    M["last-turn incidence"] = {c: sum(1 for t in tasks if any(s == last[c][t] for s, _ in fir[c][t])) / T for c in active}
    M["amplitude"] = {c: sum(len(codes[c][t]) for t in tasks) / T for c in active}
    M["step-amplitude"] = {c: sum(len(fir[c][t]) for t in tasks) / T for c in active}
    # damped inclusion-exclusion over the task's codes: a subset of size j weighted beta^(j-1); closed form
    # (1 - (1-beta)^k) / beta for k codes. beta -> 0 is amplitude, beta = 1 is incidence.
    BETA = 0.5
    M["damped PIE, β=0.5"] = {c: sum((1 - (1 - BETA) ** len(codes[c][t])) / BETA for t in tasks) / T for c in active}
    M["containment"] = {c: con(c) for c in active}
    M["breadth"] = {c: sum(1 for m in allm if rate(c, m) > 0) for c in active}
    M["worst mode"] = {c: max((rate(c, m) for m in allm), default=0) for c in active}
    M["patterns"] = {c: len({frozenset(coded[c][t]) for t in tasks if coded[c][t]}) for c in active}
    return M


def recovery_formulas(active, tasks, pts, GJ):
    T = len(tasks); M = {}
    # recovery-weighted amplitude: unit (turn, code); a unit on a task is recovered only if every firing of it was
    app_all, rec_all = {}, {}
    for c in active:
        app, rec = defaultdict(int), defaultdict(int)
        for t in tasks:
            u = {}
            for turn, cs, r in pts[c][t]:
                for m in cs: u[(turn, m)] = u.get((turn, m), True) and r
            for k, r in u.items(): app[k] += 1; rec[k] += r
        app_all[c], rec_all[c] = app, rec
    for g in (1, 2, 3):
        s = {}
        for c in active:
            app, rec = app_all[c], rec_all[c]; overall = sum(rec.values()) / max(sum(app.values()), 1); tot = 0.0
            for k, n in app.items():
                r = rec[k] / n if n >= SUPPORT_MIN else overall
                tot += (1 - r ** g) * n
            s[c] = tot / T
        M[f"recovery-weighted amplitude, γ={g}"] = s
    # profile risk: the candidate's own per-mode non-recovery share, max over the task's modes
    s = {}
    for c in active:
        app, unr = defaultdict(int), defaultdict(int)
        for t in tasks:
            for _, cs, r in pts[c][t]:
                for m in cs: app[m] += 1; unr[m] += (not r)
        q = {m: unr[m] / app[m] for m in app}
        s[c] = sum(max((q[m] for _, cs, _ in pts[c][t] for m in cs), default=0.0) for t in tasks) / T
    M["profile risk (own consequence, max)"] = s
    # gold-discounted incidence, literal: flagged (unrecovered) task counts 1 if failed, w if passed
    for w in (0.5,):
        M[f"gold-discounted incidence, w={w}"] = {c: sum((1.0 if GJ[c][t] == 0 else w) for t in tasks if any(not r for _, _, r in pts[c][t])) / T for c in active}
    return M


def taub(s, g, active):
    """s lower is better, g higher is better; ties dropped on either side. Returns (tau, resolved pairs)."""
    C = D = 0
    for a, b in itertools.combinations(active, 2):
        if s[a] == s[b] or g[a] == g[b]: continue
        C += (s[a] - s[b]) * (g[a] - g[b]) < 0; D += (s[a] - s[b]) * (g[a] - g[b]) > 0
    return ((C - D) / (C + D) if C + D else float("nan")), C + D


def topk(s, g, active, k):
    """how many of the formula's best k are in gold's best k (lower s is better, higher g is better)"""
    return len(set(sorted(active, key=lambda c: s[c])[:k]) & set(sorted(active, key=lambda c: -g[c])[:k]))


def row(name, s, gj, gg, active, bold=False):
    tj, nj = taub(s, gj, active); tg, ng = taub(s, gg, active)
    t1j = "yes" if topk(s, gj, active, 1) else "no"; t1g = "yes" if topk(s, gg, active, 1) else "no"
    n = f"**{name}**" if bold else name
    f = lambda x: "—" if math.isnan(x) else f"{x:+.3f}"
    return f"| {n} | {f(tj)} | {t1j} | {f(tg)} | {t1g} | {topk(s, gg, active, 3)}/3 | {ng} |"


HEAD = ("| formula | tau vs judged gold | top-1 judged | tau vs gen gold | top-1 gen | top-3 gen | resolved pairs |",
        "|---|---:|---|---:|---|---:|---:|")
ORDER = ["incidence", "last-turn incidence", "amplitude", "step-amplitude", "damped PIE, β=0.5", "containment", "breadth", "worst mode", "patterns"]


PROFILE = {"breadth", "worst mode", "patterns"}


def rows_both(names, M_all, M_coded, gj, gg, active):
    out = []
    for k in names:
        if k in PROFILE: out.append(row(k, M_all[k], gj, gg, active)); continue
        out.append(row(f"{k} · every kept point", M_all[k], gj, gg, active))
        out.append(row(f"{k} · coded points only", M_coded[k], gj, gg, active))
    return out


def render(exp):
    active, tasks, pts, last, GJ, GG, label = load(exp)
    pts_coded = {c: {t: [p for p in pts[c][t] if p[1] != [UNC]] for t in tasks} for c in active}
    n_unc = sum(1 for c in active for t in tasks for p in pts[c][t] if p[1] == [UNC])
    gj = {c: sum(GJ[c][t] for t in tasks) / len(tasks) for c in active}
    gg = {c: sum(GG[c].values()) / len(GG[c]) for c in active}
    npts = sum(len(pts[c][t]) for c in active for t in tasks); nunrec = sum(1 for c in active for t in tasks for p in pts[c][t] if not p[2])
    pairs = len(active) * (len(active) - 1) // 2
    L = [f"## {exp['title']}", "",
         f"- candidates: {exp['candidates']} ({len(active)}); judged tasks: **{len(tasks)}**" + (f" (dropped: {', '.join(exp['drop'])})" if exp["drop"] else "") + f"; traces: {len(active) * len(tasks)}",
         f"- taxonomy: `{exp['taxonomy']}`; judge: {exp['judge']}; recovery: {exp['rec']}",
         f"- points: {npts} kept by the judge ({n_unc} of them fit no code), {nunrec} left unrecovered",
         f"- generalization set: {exp['gen_name']}, disjoint from the judged tasks; {pairs} candidate pairs in all",
         "", f"### Table 1 — every point the judge kept", "", *HEAD]
    gold_neg = {c: -gj[c] for c in active}
    L.append(row("gold on the judged tasks (reference)", gold_neg, gj, gg, active, bold=True))
    L += rows_both(ORDER, formulas(active, tasks, pts, last, False), formulas(active, tasks, pts_coded, last, False), gj, gg, active)
    L += ["", f"### Table 2 — unrecovered points only, and the recovery-dependent formulas", "", *HEAD]
    L.append(row("gold on the judged tasks (reference)", gold_neg, gj, gg, active, bold=True))
    M = formulas(active, tasks, pts, last, True)
    L += rows_both(ORDER, M, formulas(active, tasks, pts_coded, last, True), gj, gg, active)
    R, Rc = recovery_formulas(active, tasks, pts, GJ), recovery_formulas(active, tasks, pts_coded, GJ)
    L += rows_both(list(R), R, Rc, gj, gg, active)
    L += ["", "Whether these two scores also read as solve rates (not only as an order) is in `compared_scoring.md`."]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("sharing/results.md")); a = ap.parse_args()
    parts = ["# Results", "",
             "One section per experiment, on the judged tasks that have recovery results. Table 1 reads every point the judge kept;",
             "Table 2 reads only the points the recovery reader left standing, then adds the three recovery-dependent formulas.",
             "Formulas and the measure are defined in `formulas.md`. tau-b drops tied pairs; *resolved pairs* says how many of the",
             "candidate pairs the tau rests on. top-3 = how many of the formula's best three are among the generalization set's best three.",
             "Lower is better for every formula except gold. A point the judge kept but no code fit is reported both ways: *every kept point*",
             "counts it as a failure of its own; *coded points only* drops it. Generated by `scripts/results_tables.py` from the recorded judge and recovery runs.", ""]
    for exp in EXPERIMENTS: parts += [render(exp), ""]
    a.out.write_text("\n".join(parts)); print(f"-> {a.out}")


if __name__ == "__main__":
    main()
