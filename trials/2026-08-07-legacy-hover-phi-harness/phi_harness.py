#!/usr/bin/env python3
"""Load legacy HoVer shakedown annotations into the Phi input representation
and score candidates with Phi v0 and Phi v0.1 side by side.

Trial: trials/2026-08-07-legacy-hover-phi-harness (see README.md).
Data: data/legacy-hover-shakedown/ — prototyping only, never claims-bearing
(data/SOURCES.md). This harness never reads gold: see _assert_no_gold_path.

Phi input representation per candidate:
    tasks: {task_id: {mode: [recovery_status, ...]}}
mode presence is deduplicated per task by construction; the per-(task, mode)
full-recovery flag is derived from the status list under an explicit policy.

Method sources (TIMELINE.md):
    v0    2026-08-07 13:57  Influence = (100/K) * Prevalence * delta^rr
    v0.1  2026-08-07 16:57  q_m = w0 * delta^rr(m); b_t = noisy-OR; Shapley
"""

import argparse
import json
import math
import sys
from pathlib import Path

# Loader policy (explicit; see README "Loader policy") ----------------------

RECOVERED_STATUSES = {"fully_recovered", "made_irrelevant"}
NA_STATUS = "not_applicable"
GOLD_MARKER = "gold_do_not_pass_to_judge"


def _assert_no_gold_path(path):
    if GOLD_MARKER in str(path):
        raise RuntimeError(f"gold quarantine violated: {path}")


def load_candidate(candidate_dir, include_secondary=False, na_policy="unrecovered"):
    """Return {task_id: {mode: [status, ...]}} for one candidate folder."""
    tasks = {}
    for f in sorted(Path(candidate_dir).glob("*.json")):
        _assert_no_gold_path(f)
        if f.name.startswith("_"):
            continue
        d = json.loads(f.read_text())
        task = d["task_id"]
        modes = tasks.setdefault(task, {})
        for fp in d.get("failure_points", []):
            status = fp.get("recovery_status", "unclear")
            if na_policy == "exclude" and status == NA_STATUS:
                continue
            if na_policy == "recovered" and status == NA_STATUS:
                status = "fully_recovered"
            for m in fp.get("taxonomy_mappings", []):
                if not include_secondary and m.get("primary_or_secondary") != "primary":
                    continue
                code = m.get("code")
                if code:
                    modes.setdefault(code, []).append(status)
    return tasks


def restrict_to_subset(tasks, subset_ids):
    """Keep only subset tasks that were actually annotated; report missing."""
    if subset_ids is None:
        return tasks, []
    present = {t: v for t, v in tasks.items() if t in subset_ids}
    missing = sorted(set(subset_ids) - set(tasks))
    return present, missing


def per_mode_rates(tasks):
    """(affected, recovered) task counts per mode; recovery = ALL statuses
    for the (task, mode) pair are in RECOVERED_STATUSES (strict v0 semantics)."""
    affected, recovered = {}, {}
    for _, modes in tasks.items():
        for mode, statuses in modes.items():
            affected[mode] = affected.get(mode, 0) + 1
            if all(s in RECOVERED_STATUSES for s in statuses):
                recovered[mode] = recovered.get(mode, 0) + 1
    return affected, recovered


# Scorers --------------------------------------------------------------------

def phi_v0(tasks, n_tasks, k_modes, delta):
    """TIMELINE 2026-08-07 13:57. Weight = 100/K equal split."""
    affected, recovered = per_mode_rates(tasks)
    influence = {}
    for mode, aff in affected.items():
        rr = recovered.get(mode, 0) / aff
        influence[mode] = (100.0 / k_modes) * (aff / n_tasks) * (delta ** rr)
    return 100.0 - sum(influence.values()), influence


def shapley_noisy_or(qs):
    """Exact Shapley values for v(T) = 1 - prod(1 - q_j), via the size-grouped
    identity phi_i = q_i * sum_k [k!(n-1-k)!/n!] * e_k(others' (1-q))."""
    n = len(qs)
    out = []
    for i, qi in enumerate(qs):
        others = [1.0 - q for j, q in enumerate(qs) if j != i]
        e = [1.0]  # elementary symmetric polynomials of `others`
        for x in others:
            e = [e[0]] + [e[k] + x * e[k - 1] for k in range(1, len(e))] + [x * e[-1]]
        acc = sum(
            (math.factorial(k) * math.factorial(n - 1 - k) / math.factorial(n)) * e[k]
            for k in range(n)
        )
        out.append(qi * acc)
    return out


def phi_v01(tasks, n_tasks, delta, w0):
    """TIMELINE 2026-08-07 16:57. Task-first noisy-OR + Shapley profile."""
    affected, recovered = per_mode_rates(tasks)
    q = {
        mode: w0 * (delta ** (recovered.get(mode, 0) / aff))
        for mode, aff in affected.items()
    }
    burdens, influence, max_cooccur = [], {}, 0
    for _, modes in tasks.items():
        present = sorted(modes)
        max_cooccur = max(max_cooccur, len(present))
        qs = [q[m] for m in present]
        b_t = 1.0 - math.prod(1.0 - x for x in qs)
        burdens.append(b_t)
        phis = shapley_noisy_or(qs)
        assert abs(sum(phis) - b_t) < 1e-9, "Shapley efficiency violated"
        for m, p in zip(present, phis):
            influence[m] = influence.get(m, 0.0) + 100.0 * p / n_tasks
    mean_burden = sum(burdens) / n_tasks if n_tasks else 0.0
    return 100.0 * (1.0 - mean_burden), influence, max_cooccur


# Validation -----------------------------------------------------------------

def self_test():
    """The worked example frozen in conversation on 2026-08-07: N=4, modes A
    (w=0.5) and B (w=0.5), delta=0.5; task1 A+B unrecovered, task2 A
    recovered, task3 A unrecovered, task4 clean. Expect Phi_v01 = 62.70,
    Influence A = 27.28, B = 10.02."""
    tasks = {
        "t1": {"A": ["unrecovered"], "B": ["unrecovered"]},
        "t2": {"A": ["fully_recovered"]},
        "t3": {"A": ["unrecovered"]},
        "t4": {},
    }
    phi, infl, _ = phi_v01(tasks, n_tasks=4, delta=0.5, w0=0.5)
    assert abs(phi - 62.697) < 0.01, phi
    assert abs(infl["A"] - 27.28) < 0.01, infl
    assert abs(infl["B"] - 10.02) < 0.01, infl
    assert abs((100.0 - sum(infl.values())) - phi) < 1e-9
    # two-mode closed form
    qa, qb = 0.3, 0.8
    pa, pb = shapley_noisy_or([qa, qb])
    assert abs(pa - qa * (1 - qb / 2)) < 1e-12
    assert abs(pb - qb * (1 - qa / 2)) < 1e-12
    # no co-occurrence => v0 and v0.1 rank identically (2 synthetic candidates)
    a = {"t%d" % i: ({"A": ["unrecovered"]} if i < 6 else {}) for i in range(10)}
    b = {"t%d" % i: ({"A": ["unrecovered"]} if i < 3 else {}) for i in range(10)}
    va = phi_v0(a, 10, 19, 0.5)[0] - phi_v0(b, 10, 19, 0.5)[0]
    vb = phi_v01(a, 10, 0.5, 0.5)[0] - phi_v01(b, 10, 0.5, 0.5)[0]
    assert (va < 0) == (vb < 0)
    print("self-test: OK")


def kendall_tau(x, y):
    """tau-a between two equal-length score lists (pairs over indices)."""
    n = len(x)
    conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = (x[i] - x[j]) * (y[i] - y[j])
            conc += s > 0
            disc += s < 0
    return (conc - disc) / (n * (n - 1) / 2) if n > 1 else 1.0


# Entry ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="annotation run dir (candidate_* inside)")
    ap.add_argument("--taxonomy", required=True, help="taxonomy JSON the run used (K)")
    ap.add_argument("--subset", default=None, help="evaluation_subset.json (task universe)")
    ap.add_argument("--delta", type=float, default=0.5)
    ap.add_argument("--w0", type=float, default=0.5)
    ap.add_argument("--include-secondary", action="store_true")
    ap.add_argument("--na-policy", choices=["unrecovered", "recovered", "exclude"],
                    default="unrecovered")
    ap.add_argument("--out", default=None, help="write results JSON here")
    args = ap.parse_args()

    _assert_no_gold_path(args.run)
    k_modes = len(json.loads(Path(args.taxonomy).read_text())["codes"])
    subset = None
    if args.subset:
        subset = set(json.loads(Path(args.subset).read_text())["task_ids"])

    rows = []
    for cdir in sorted(Path(args.run).glob("candidate_*")):
        tasks = load_candidate(cdir, args.include_secondary, args.na_policy)
        tasks, missing = restrict_to_subset(tasks, subset)
        n = len(tasks)
        if n == 0:
            continue
        v0_phi, _ = phi_v0(tasks, n, k_modes, args.delta)
        v01_phi, v01_infl, max_co = phi_v01(tasks, n, args.delta, args.w0)
        rows.append({
            "candidate": cdir.name, "n_tasks": n, "missing_from_subset": len(missing),
            "phi_v0": round(v0_phi, 2), "phi_v01": round(v01_phi, 2),
            "max_cooccurrence": max_co,
            "mean_modes_per_task": round(
                sum(len(m) for m in tasks.values()) / n, 2),
            "top_influence_v01": sorted(
                v01_infl.items(), key=lambda kv: -kv[1])[:3],
        })

    for r, rank in ((sorted(rows, key=lambda r: -r["phi_v0"]), "rank_v0"),
                    (sorted(rows, key=lambda r: -r["phi_v01"]), "rank_v01")):
        for i, row in enumerate(r, 1):
            row[rank] = i
    tau = kendall_tau([r["phi_v0"] for r in rows], [r["phi_v01"] for r in rows])

    hdr = ("candidate", "n_tasks", "phi_v0", "rank_v0", "phi_v01", "rank_v01",
           "mean_modes_per_task", "max_cooccurrence")
    print("  ".join(f"{h:>19}" for h in hdr))
    for r in rows:
        print("  ".join(f"{str(r[h]):>19}" for h in hdr))
    print(f"\nkendall tau-a (v0 vs v0.1): {tau:.3f}   "
          f"K={k_modes} delta={args.delta} w0={args.w0} "
          f"na={args.na_policy} secondary={args.include_secondary}")

    if args.out:
        Path(args.out).write_text(json.dumps(
            {"config": vars(args), "K": k_modes, "kendall_tau": tau,
             "candidates": rows}, indent=1, default=str))
        print(f"wrote {args.out}")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        main()
