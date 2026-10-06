#!/usr/bin/env python3
"""mode_methods.md: the formulas that read failure modes (which codes fired, or how many distinct codes), one row per
family, on Models·HoVer, Models·Terminal-Bench and Models·LiveCodeBench (50-task split).

    python3 sharing/scripts/mode_methods.py --out sharing/mode_methods.md

A family is a formula plus the variants that change only one setting of it: a weight, a constant, a cut-off, or
whether a count is the candidate's own or pooled over candidates. Each table shows the family member with the
highest mean tau over the three experiments and lists the next three members under the table. The two arms (no recovery,
with recovery) are tables of their own. The last section lists every cell of the first-and-last grid. Same inputs and
formula code as best_methods.py and first_last_study.py. Offline; no model call.
"""
from __future__ import annotations
import argparse, statistics as st, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import best_methods as bm  # noqa: E402
import first_last_study as fl  # noqa: E402

KEYS = ["models_hover", "models_tb", "models_lcb"]
WEIGHTS = ["none", "rarity, own", "rarity, pooled", "rarity, combined", "spread across candidates"]
SUMS = ["sum over endpoints", "sum over modes"]
COMBS = ["max", "sum over modes", "sum over endpoints"]
RULES = [r for r, _, _ in fl.RULES if r != "no filter"]
WNAME = {"none": "no weight", "rarity, own": "own rarity weight", "rarity, pooled": "pooled rarity weight",
         "rarity, combined": "combined rarity weight", "spread across candidates": "spread weight"}
SHOW = 3   # members listed under a table; the rest are in the appendix tables

# (arm, row label, members, the member expected to be best, how the shown member works)
FAMILIES = [
    ("none", "incidence after removing formatting codes", ["A: incidence, formatting removed (no recovery)"],
     "A: incidence, formatting removed (no recovery)",
     "delete formatting codes; share of tasks with any instance left"),
    ("none", "endpoint codes counted", [f"grid: no recovery · {w} · {c}" for w in WEIGHTS for c in SUMS] + ["setup 1"],
     "grid: no recovery · none · sum over endpoints",
     "per task: codes on the first instance + codes on the last; mean"),
    ("none", "mode filter on the endpoints", [f"B none: {r}" for r in RULES],
     "B none: per candidate: drop the top 1 mode",
     "ignore the candidate's most frequent code at each endpoint position; share of tasks whose first or last instance still has another code"),
    ("none", "worst mode", ["base none: worst mode"], "base none: worst mode",
     "for each code, the share of tasks on which it fired; score = the largest share"),
    ("none", "amplitude", ["base none: amplitude", "base none: step-amplitude", "base none: containment", "base none: damped PIE, β=0.5"],
     "base none: amplitude", "per task: number of distinct codes; mean"),
    ("none", "breadth", ["base none: breadth"], "base none: breadth", "number of distinct codes the candidate triggers on any task"),
    ("none", "patterns", ["base none: patterns"], "base none: patterns", "number of distinct code sets among the candidate's tasks"),
    ("rec", "unrecovered endpoint codes counted", [f"grid: unrecovered instances only · {w} · {c}" for w in WEIGHTS for c in SUMS],
     "grid: unrecovered instances only · none · sum over modes",
     "drop recovered instances; per task: distinct codes across the first and last remaining instance (a code on both counts once); mean"),
    ("rec", "mode filter on unrecovered endpoints", [f"B {i}: {r}" for i in ("after", "first") for r in RULES],
     "B first: per candidate: drop modes above mean + 1.5 SD",
     "drop recovered; at each endpoint position, count how often each code appears over the candidate's tasks; ignore codes above "
     "mean + 1.5 SD of those counts; share of tasks with a code left at either endpoint"),
    ("rec", "endpoints weighted by the recovery rate", [f"grid: recovery-weighted, {s} · {w} · {c}" for s in ("own", "pooled", "combined")
                                                        for w in WEIGHTS for c in COMBS],
     "grid: recovery-weighted, own · none · max",
     "endpoints of all instances; an unrecovered endpoint code weighs 1, a recovered one weighs how often the candidate leaves that "
     "code at that position unrecovered; per task: the largest weight; mean"),
    ("rec", "profile risk", ["base rec: profile risk (own consequence, max)"], "base rec: profile risk (own consequence, max)",
     "for each code, the share of the candidate's instances with it that went unrecovered; per task: the largest such share among "
     "the task's codes; mean"),
    ("rec", "unrecovered amplitude", [f"base rec: unrecovered {f}" for f in ("amplitude", "step-amplitude", "containment", "damped PIE, β=0.5")],
     "base rec: unrecovered amplitude", "drop recovered; per task: number of distinct codes; mean"),
    ("rec", "recovery-weighted amplitude", [f"base rec: recovery-weighted amplitude, γ={g}" for g in (1, 2, 3)],
     "base rec: recovery-weighted amplitude, γ=2",
     "for each (turn, code) unit, ρ = share of the tasks where it fired on which it was fully recovered; weight 1 − ρ²; "
     "score = Σ over units of weight × tasks fired ÷ T"),
    ("rec", "unrecovered worst mode", ["base rec: unrecovered worst mode"], "base rec: unrecovered worst mode",
     "drop recovered; worst mode on what is left"),
    ("rec", "unrecovered breadth", ["base rec: unrecovered breadth"], "base rec: unrecovered breadth", "drop recovered; breadth on what is left"),
    ("rec", "unrecovered patterns", ["base rec: unrecovered patterns"], "base rec: unrecovered patterns", "drop recovered; patterns on what is left"),
]
REFERENCES = {"none": [("incidence", "base none: incidence", "share of tasks with any instance"),
                       ("last-turn incidence", "base none: last-turn incidence", "share of tasks with an instance on the final turn")],
              "rec": [("unrecovered incidence", "base rec: unrecovered incidence", "share of tasks with any unrecovered instance")]}


def label(m: str) -> str:
    """the name a dropped variant is listed under"""
    if m == "setup 1":
        return "Setup 1 (rarity weight over both endpoints pooled, codes counted once)"
    if m.startswith("grid: "):
        arm, w, c = m[6:].split(" · ")
        parts = [arm.split(", ")[1] + " recovery rate"] if arm.startswith("recovery-weighted") else []
        return ", ".join(parts + [WNAME[w], c])
    if m.startswith("B "):
        inp, rule = m[2:].split(": ", 1)
        return {"none": "", "after": "recovery checked on the endpoints, ", "first": "endpoints of unrecovered instances, "}[inp] + rule
    return m.split(": ", 1)[1]


def collect():
    R = {}
    tau, *_ = bm.collect()
    v0 = lambda r: r[0] if isinstance(r, tuple) else r
    for (arm, f), v in tau.items():
        R[{"bar": "bar", "no recovery": "base none", "recovery": "base rec"}[arm] + ": " + f] = [v0(v[k]) for k in KEYS]
    E = [fl.Exp(e) for e in fl.MAIN if e["key"] in KEYS]
    E.sort(key=lambda x: KEYS.index(x.key))
    for name, v in fl.part_a(E).items():
        if not name.startswith("_"):
            R[f"A: {name}"] = [v[k][0] for k in KEYS]
    B, _ = fl.part_b(E)
    for (k, inp, rule), v in B.items():
        R.setdefault(f"B {inp}: {rule}", [None] * 3)[KEYS.index(k)] = v[0]
    for x in E:
        for cell, v in fl.grid(x).items():
            R.setdefault("grid: " + " · ".join(cell), [None] * 3)[KEYS.index(x.key)] = v[0]
        R.setdefault("setup 1", [None] * 3)[KEYS.index(x.key)] = fl.setup1(x)[0]
    return E, R


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("sharing/mode_methods.md")); a = ap.parse_args()
    E, R = collect()
    mean = lambda m: st.mean(R[m])
    f3 = lambda x: f"{x:+.3f}"
    head = "| method | " + " | ".join(f"{fl.SHORT[x.key]} ({len(x.active)}×{x.T})" for x in E) + " | mean | how it works |"
    sep = "|---|" + "---:|" * (len(E) + 1) + "---|"
    bar = R["bar: gold on the judged tasks"]
    L = ["# Methods that read failure modes", "",
         "The formulas that use which codes fired, or how many distinct codes fired, not only whether a trace has a failure",
         "instance. Three experiments: Models·HoVer (judged set b), Models·Terminal-Bench 2.0 and Models·LiveCodeBench on its",
         "50-task split. GEPA·HoVer is left out of these tables; its numbers for every method are in `best_methods.md` and",
         "`first_last_study.md`. SWE-bench is not included: the endpoint formulas need its formatting codes chosen first.", "",
         "Each number is Kendall tau-b against the generalization set's pass rates, tied pairs dropped; every score is lower-is-better.",
         "The steps of every formula are in `formulas.md` (baselines, recovery-dependent formulas, and the section on the first and",
         "last failure instance).", "",
         "**One row per family.** A family is a formula plus the variants that change only one setting of it: a weight, a constant,",
         "a cut-off, or whether a count is the candidate's own or pooled over candidates. The row shows the member with the highest",
         "mean over the three experiments; the other members are listed under the table. The pick is made on the same three",
         "experiments it is reported on, so a shown row's mean is optimistic by roughly its gap to the next member. *Endpoint*",
         "formulas read only each trace's first and last failure instance, after deleting formatting codes.", ""]
    for arm, title in (("none", "Without recovery"), ("rec", "With recovery")):
        L += [f"## {title}", "", head, sep,
              "| *gold on the judged tasks (the bar)* | " + " | ".join(f"*{f3(x)}*" for x in bar) + f" | *{f3(st.mean(bar))}* | share of judged tasks the candidate passed |"]
        rows, dropped = [], []
        for arm_, name, members, expect, how in FAMILIES:
            if arm_ != arm:
                continue
            best = max(members, key=mean)
            if best != expect:
                sys.exit(f"{name}: best member is now {best!r}, not {expect!r}; rewrite its description")
            rows.append((mean(best), name, best, how))
            others = sorted((m for m in members if m != best), key=lambda m: -mean(m))
            if others:
                more = f"; {len(others) - SHOW} more in the appendix" if len(others) > SHOW else ""
                dropped.append(f"- **{name}** (shown: {label(best)}): " + "; ".join(f"{label(m)} {f3(mean(m))}" for m in others[:SHOW]) + more)
        for mu, name, best, how in sorted(rows, key=lambda r: -r[0]):
            L.append(f"| {name} | " + " | ".join(f3(x) for x in R[best]) + f" | {f3(mu)} | {how} |")
        for name, key, how in REFERENCES[arm]:
            L.append(f"| *{name} (instances only, reference)* | " + " | ".join(f"*{f3(x)}*" for x in R[key]) + f" | *{f3(mean(key))}* | {how} |")
        L += ["", "Next members of each family by mean tau over the three experiments:", "", *dropped, ""]
    L += ["## Appendix: every cell of the first-and-last grid", "",
          "Recovery weight × mode weight × combiner, as defined in `formulas.md`; 75 cells, sorted by mean within each recovery weight.", "",
          "| recovery weight | mode weight | combiner | " + " | ".join(fl.SHORT[x.key] for x in E) + " | mean |", "|---|---|---|" + "---:|" * (len(E) + 1)]
    cells = [m for m in R if m.startswith("grid: ")]
    order = ["no recovery", "recovery-weighted, own", "recovery-weighted, pooled", "recovery-weighted, combined", "unrecovered instances only"]
    for m in sorted(cells, key=lambda m: (order.index(m[6:].split(" · ")[0]), -mean(m))):
        arm, w, c = m[6:].split(" · ")
        L.append(f"| {arm} | {WNAME[w]} | {c} | " + " | ".join(f3(x) for x in R[m]) + f" | {f3(mean(m))} |")
    L += ["", "## Appendix: every mode filter", "",
          "Rules and inputs as defined in `formulas.md`; sorted by mean within each input.", "",
          "| input | rule | " + " | ".join(fl.SHORT[x.key] for x in E) + " | mean |", "|---|---|" + "---:|" * (len(E) + 1)]
    inputs = {"none": "endpoints of every instance (no recovery)", "after": "recovery checked on the endpoints", "first": "endpoints of unrecovered instances"}
    for inp in inputs:
        for r in sorted(RULES, key=lambda r: -mean(f"B {inp}: {r}")):
            L.append(f"| {inputs[inp]} | {r} | " + " | ".join(f3(x) for x in R[f"B {inp}: {r}"]) + f" | {f3(mean(f'B {inp}: {r}'))} |")
    L += ["", "Generated by `scripts/mode_methods.py` from the recorded judge and recovery runs; no model call."]
    a.out.write_text("\n".join(L) + "\n"); print(f"-> {a.out}")


if __name__ == "__main__":
    main()
