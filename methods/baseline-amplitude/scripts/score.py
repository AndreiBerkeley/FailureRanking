#!/usr/bin/env python3
"""Base failure amplitude: score every candidate from a judge mapping, and validate against a target.

    python3 methods/baseline-amplitude/scripts/score.py --benchmark hover --mapping map-5
    python3 methods/baseline-amplitude/scripts/score.py --benchmark hover --mapping map-5 --out results/hover/map-5/baseline-amplitude

A(c) = (1/T) * sum over the candidate's judged tasks t of |codes(c,t)|, the mean number of DISTINCT
codes the judge assigned per task. Lower is better. codes(c,t) is a set, so a code cited twice in a
trace counts once; every code weighs the same. A judged task with no code contributes 0, and the
formula cannot tell a clean task from one the judge said nothing about.

Reads only the mapping (codes per trace, repeat 0, judged status). No gold, no taxonomy text, no
trace content: the score is outcome-free. Gold is read afterwards, for validation only.
"""
from __future__ import annotations
import argparse, json, random, statistics as st
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def tau_b(x, y):
    n = len(x); c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = x[i] - x[j], y[i] - y[j]
            if a == 0 and b == 0: continue
            if a == 0: tx += 1
            elif b == 0: ty += 1
            elif (a > 0) == (b > 0): c += 1
            else: d += 1
    den = ((c + d + tx) * (c + d + ty)) ** 0.5
    return (c - d) / den if den else float("nan")


def perm_p(x, y, n=20000, seed=0):
    rng = random.Random(seed); t0 = abs(tau_b(x, y)); y = list(y); hits = 0
    for _ in range(n):
        rng.shuffle(y); hits += abs(tau_b(x, y)) >= t0 - 1e-12
    return (hits + 1) / (n + 1)


def score(benchmark: str, mapping: str) -> dict:
    """candidate -> A(c), plus the per-task code counts the bootstrap needs."""
    rows = [json.loads(l) for l in open(REPO / "data" / benchmark / "mappings" / mapping / "mapping.jsonl")]
    rows = [r for r in rows if r["status"] == "judged" and int(r.get("repeat", 0)) == 0]
    per = {}
    for r in rows: per.setdefault(r["candidate_id"], {})[r["task_id"]] = len(r.get("codes") or {})
    return {"counts": per, "score": {c: st.mean(v.values()) for c, v in per.items()},
            "tasks": sorted({r["task_id"] for r in rows}), "traces": len(rows)}


def target_gold(benchmark: str, portion: str, tasks=None) -> dict:
    """candidate -> mean gold score over a portion of the split (repeat 0), for validation only."""
    ids = set(json.loads((REPO / "data" / benchmark / "splits" / "pools-1" / "split.json").read_text())["portions"][portion])
    if tasks is not None: ids &= set(tasks)
    per = {}
    for f in sorted((REPO / "data" / benchmark / "outcomes").glob("cap-*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r["task_id"] in ids and int(r.get("repeat", 0)) == 0 and not r.get("capture_failed"):
                per.setdefault(r["candidate_id"], {})[r["task_id"]] = float(r["score"])
    return {c: st.mean(v.values()) for c, v in per.items() if v}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True); ap.add_argument("--mapping", required=True)
    ap.add_argument("--target", default="generalization", help="split portion to validate against (default: generalization)")
    ap.add_argument("--bootstrap", type=int, default=2000); ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    S = score(a.benchmark, a.mapping); G = target_gold(a.benchmark, a.target)
    cands = sorted(set(S["score"]) & set(G))
    x = [-S["score"][c] for c in cands]; y = [G[c] for c in cands]     # negate: lower amplitude = better
    t, p = tau_b(x, y), perm_p(x, y)
    rng = random.Random(2026); boots = []
    for _ in range(a.bootstrap):                                        # resample the judged tasks
        smp = [rng.choice(S["tasks"]) for _ in S["tasks"]]
        xb = [-st.mean(S["counts"][c][k] for k in smp if k in S["counts"][c]) for c in cands]
        boots.append(tau_b(xb, y))
    boots.sort(); lo, hi = boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]
    print(f"{a.benchmark} {a.mapping}: {S['traces']} traces, {len(cands)} candidates, {len(S['tasks'])} tasks")
    print(f"  amplitude (codes per task, lower better): " + ", ".join(f"{c[-6:]} {S['score'][c]:.2f}" for c in sorted(cands, key=lambda c: S['score'][c])))
    print(f"  vs gold on '{a.target}': tau-b {t:+.2f} (permutation p={p:.3f}), 95% task-bootstrap [{lo:+.2f}, {hi:+.2f}]")
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "scores.json").write_text(json.dumps({"method": "baseline-amplitude", "benchmark": a.benchmark, "mapping": a.mapping,
            "formula": "A(c) = mean over judged tasks of |distinct codes|; lower is better", "reads": "mapping only; outcome-free",
            "scores": S["score"], "tasks": len(S["tasks"]), "traces": S["traces"],
            "validation": {"target": a.target, "kendall_tau_b": t, "permutation_p": p, "bootstrap95": [lo, hi]}}, indent=1))
        print(f"  -> {a.out}/scores.json")


if __name__ == "__main__":
    main()
