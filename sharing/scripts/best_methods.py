#!/usr/bin/env python3
"""best_methods.md: which formula ranks the candidates best, without recovery and with it, across every
experiment; and, for the formulas that read as a solve rate, how far the number is from the solve rate itself.

    python3 sharing/scripts/best_methods.py --out sharing/best_methods.md

The rule for "best", fixed before reading the table: per arm (every failure instance / unrecovered instances
plus the recovery-dependent formulas), the formula with the highest mean tau-b against the generalization
set over all experiments. Formulas that read the judged tasks' gold are not candidates. Every kept instance
counts (an instance no code fit is its own pseudo-code), as in compared_scoring.md. Same experiments, inputs
and formula code as results_tables.py. Offline; no model call.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from results_tables import MAIN, SUPPLEMENTARY, load, formulas, recovery_formulas, taub  # noqa: E402

SHORT = {"gepa_hover": "GEPA·HoVer", "models_hover": "Models·HoVer", "models_tb": "Models·TB", "models_lcb": "Models·LCB (50)",
         "models_lcb150": "Models·LCB, 150 (supp.)",
         "models_swe": "Models·SWE", "models_tau2": "Models·τ²", "models_bfcl": "Models·BFCL"}
# readings on the scale of a solve rate: 1 − score is the share of judged tasks the trace says were solved
SOLVE_RATE = [("no recovery", "incidence", "1 − incidence"),
              ("no recovery", "last-turn incidence", "1 − last-turn incidence"),
              ("recovery", "unrecovered incidence", "1 − unrecovered incidence"),
              ("recovery", "unrecovered last-turn incidence", "1 − unrecovered last-turn incidence"),
              ("recovery", "profile risk (own consequence, max)", "1 − profile risk")]


def collect():
    tau, dist_g, dist_j, info = {}, {}, {}, []
    for exp in MAIN + SUPPLEMENTARY:
        active, tasks, pts, last, GJ, GG, _ = load(exp)
        k = exp["key"]; n = len(active)
        gj = {c: sum(GJ[c][t] for t in tasks) / len(tasks) for c in active}
        gg = {c: sum(GG[c].values()) / len(GG[c]) for c in active}
        info.append((k, exp["title"], n, len(tasks), exp["gen_name"], exp.get("fallback", 0), bool(exp.get("supplementary"))))
        tau.setdefault(("bar", "gold on the judged tasks"), {})[k] = taub({c: -gj[c] for c in active}, gg, active)
        arms = {"no recovery": formulas(active, tasks, pts, last, False),
                "recovery": {**{f"unrecovered {f}": v for f, v in formulas(active, tasks, pts, last, True).items()},
                             **recovery_formulas(active, tasks, pts, GJ)}}
        for arm, M in arms.items():
            for f, s in M.items():
                if f.startswith("gold-discounted"):
                    continue
                tau.setdefault((arm, f), {})[k] = taub(s, gg, active)
        dist_g.setdefault("gold on the judged tasks (reference)", {})[k] = 100 * sum(abs(gj[c] - gg[c]) for c in active) / n
        for arm, f, name in SOLVE_RATE:
            s = arms[arm][f]
            dist_g.setdefault(name, {})[k] = 100 * sum(abs(1 - s[c] - gg[c]) for c in active) / n
            dist_j.setdefault(name, {})[k] = 100 * sum(abs(1 - s[c] - gj[c]) for c in active) / n
    return tau, dist_g, dist_j, info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("sharing/best_methods.md")); a = ap.parse_args()
    tau, dist_g, dist_j, info = collect()
    keys = [i[0] for i in info if not i[6]]; supp = [i[0] for i in info if i[6]]
    mean = lambda d: sum(d[k][0] if isinstance(d[k], tuple) else d[k] for k in keys) / len(keys)
    head = "| | " + " | ".join(SHORT[k] for k in keys) + " | **mean** |" + "".join(f" {SHORT[k]} |" for k in supp)
    sep = "|---|" + "---:|" * (len(keys) + 1 + len(supp))
    sv = lambda d: "".join(f" {d[k][0]:+.3f} |" if isinstance(d[k], tuple) else f" {d[k]:.1f} |" for k in supp)
    L = ["# Best methods, without recovery and with it", "",
         "Which formula orders the candidates most like their pass rates on the generalization set, and, for the formulas whose",
         "score is on the scale of a solve rate, how far the number itself is from the solve rate. Formulas, the measure and the",
         "solve-rate reading are defined in `formulas.md`; per-experiment detail is in `results.md` and `compared_scoring.md`.", "",
         "**How \"best\" is chosen** (fixed before the table was read): in each arm, the formula with the highest *mean* tau-b against",
         "the generalization set over the main experiments below. Formulas that read the judged tasks' gold are not candidates. Every",
         "kept failure instance counts (an instance no code fit is its own pseudo-code). The selection is still made on the same",
         "experiments it is reported on, so the best row's mean is optimistic by the size of the gaps between rows.", "",
         "| experiment | candidates | judged tasks | generalization set |", "|---|---:|---:|---|"]
    for k, title, n, T, gen, fb, sup in info:
        L.append(f"| {title} | {n} | {T} | {gen}" + (f"; {fb} trace(s) without a recovery verdict count every instance unrecovered" if fb else "")
                 + ("; shown after the mean, in no mean and no choice" if sup else "") + " |")
    for arm, title in (("no recovery", "Without recovery: every failure instance the judge kept"),
                       ("recovery", "With recovery: unrecovered instances, plus the recovery-dependent formulas")):
        rows = sorted([(f, d) for (a_, f), d in tau.items() if a_ == arm], key=lambda fd: -mean(fd[1]))
        best = rows[0][0]
        L += ["", f"## {title}", "", "tau-b against the generalization set's pass rates (ties dropped); lower score is better for every formula.", "",
              head, sep]
        bar = tau[("bar", "gold on the judged tasks")]
        L.append("| *gold on the judged tasks (the bar)* | " + " | ".join(f"*{bar[k][0]:+.3f}*" for k in keys) + f" | *{mean(bar):+.3f}* |" + sv(bar))
        for f, d in rows:
            nm = f"**{f}** (best)" if f == best else f
            L.append(f"| {nm} | " + " | ".join(f"{d[k][0]:+.3f}" for k in keys) + f" | {mean(d):+.3f} |" + sv(d))
    L += ["", "## Read as a solve rate: absolute distance from the actual solve rate", "",
          "For each formula on the scale of a share of tasks, 1 − score is the share of judged tasks the traces say were solved. The",
          "entry is the mean over candidates of |that share − the candidate's actual solve rate|, in percentage points. Formulas that",
          "count (amplitude and the rest) are not on this scale and have no entry.", "",
          "**Against the generalization set's solve rate** (the reference row is the judged tasks' own solve rate against it: the part",
          "of the gap that is the task draw)", "", head, sep]
    for name, d in dist_g.items():
        nm = f"*{name}*" if name.startswith("gold") else name
        L.append(f"| {nm} | " + " | ".join(f"{d[k]:.1f}" for k in keys) + f" | {sum(d[k] for k in keys)/len(keys):.1f} |" + sv(d))
    L += ["", "**Against the judged tasks' own solve rate** (same tasks the traces are from)", "", head, sep]
    for name, d in dist_j.items():
        L.append(f"| {name} | " + " | ".join(f"{d[k]:.1f}" for k in keys) + f" | {sum(d[k] for k in keys)/len(keys):.1f} |" + sv(d))
    L += ["", "Generated by `scripts/best_methods.py` from the recorded judge and recovery runs; no model call."]
    a.out.write_text("\n".join(L) + "\n"); print(f"-> {a.out}")


if __name__ == "__main__":
    main()
