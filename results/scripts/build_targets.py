#!/usr/bin/env python3
"""Build the gold targets a ranking method is scored against. Offline.

Two targets, per FOUNDATION.md section 5:

  cross-run        long-run average on the SAME task set, estimated from the
                   repeats of the measurement split
  generalization   long-run average on a NEW task set, from the generalization
                   split

Neither is judged. They are gold outcomes, and they exist to be compared
against, never to feed formula development.

Each target carries three things beyond the ranking, because a ranking without
them invites the error FOUNDATION.md names -- gold scoring always returns a
complete order, even when the truth is that the candidates are indistinguishable.

  reliability    split-half over tasks, Spearman-Brown corrected to full length.
                 The ceiling on any correlation measured against this target,
                 and the factor observed correlations are attenuated by.
  signal/noise   between-candidate variance over the noise variance of one
                 candidate mean. Below ~1 the ordering is mostly noise.
  resolvable     per pair, the paired per-task difference and whether it clears
                 1.96 standard errors. Pairs that do not are not real orderings
                 and no method should be credited or penalised for them.
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import statistics as st
from itertools import combinations
from pathlib import Path

REPO = Path("/Users/andreicojocaru/Desktop/FailureRank")
TRIAL = REPO / "legacy/trials/2026-08-25-gepa-cross-benchmark-candidates"


def load(run: str, repeats=None):
    """candidate -> task -> [scores across repeats]"""
    m: dict = {}
    used_repeats = set()
    for p in sorted(glob.glob(str(TRIAL / "runs" / run / "records" / "*.json"))):
        d = json.loads(Path(p).read_text())
        rep = d.get("repeat")
        if repeats is not None and rep not in repeats:
            continue
        used_repeats.add(rep)
        c = d["candidate_idx"]
        m.setdefault(c, {})
        for r in d["records"]:
            m[c].setdefault(r["task_id"], []).append(float(r["score"]))
    return m, sorted(used_repeats)


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = sum((a - mx) ** 2 for a in x) ** 0.5
    dy = sum((b - my) ** 2 for b in y) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


def reliability(per_task, trials=400, seed=0):
    """Split-half over TASKS, Spearman-Brown corrected."""
    rng = random.Random(seed)
    cands = sorted(per_task)
    tasks = sorted(set().union(*[set(v) for v in per_task.values()]))
    rs = []
    for _ in range(trials):
        t = tasks[:]
        rng.shuffle(t)
        h = len(t) // 2
        A, B = t[:h], t[h:h * 2]
        xa = [st.mean(per_task[c][k] for k in A if k in per_task[c]) for c in cands]
        xb = [st.mean(per_task[c][k] for k in B if k in per_task[c]) for c in cands]
        r = pearson(xa, xb)
        if r == r:
            rs.append(r)
    rh = st.mean(rs)
    return 2 * rh / (1 + rh) if rh > -1 else float("nan")


def build(benchmark: str, run: str, label: str, repeats=None) -> dict:
    raw, used = load(run, repeats)
    if not raw:
        raise SystemExit(f"no records for {run}")
    # average repeats within a task first, so a task counts once
    per_task = {c: {k: st.mean(v) for k, v in d.items()} for c, d in raw.items()}
    cands = sorted(per_task)
    tasks = sorted(set().union(*[set(v) for v in per_task.values()]))
    means = {c: st.mean(per_task[c][k] for k in tasks if k in per_task[c])
             for c in cands}

    n = len(tasks)
    between = st.pvariance(list(means.values()))
    noise = st.mean(st.pvariance(list(per_task[c].values())) for c in cands) / n

    # resolvable pairs: paired per-task differences, so task difficulty cancels
    pairs = []
    for a, b in combinations(cands, 2):
        common = [k for k in tasks if k in per_task[a] and k in per_task[b]]
        d = [per_task[a][k] - per_task[b][k] for k in common]
        if len(d) < 2:
            continue
        md = st.mean(d)
        se = st.stdev(d) / len(d) ** 0.5
        pairs.append({"a": a, "b": b, "diff": round(md, 4), "se": round(se, 4),
                      "resolvable": bool(se > 0 and abs(md) > 1.96 * se)})
    nres = sum(1 for p in pairs if p["resolvable"])

    rel = reliability(per_task)
    return {
        "benchmark": benchmark,
        "target": label,
        "source_run": run,
        "repeats_used": used,
        "n_tasks": n,
        "n_candidates": len(cands),
        "ranking": [c for c in sorted(cands, key=lambda c: -means[c])],
        "mean_score": {str(c): round(means[c], 4) for c in cands},
        "reliability": round(rel, 4),
        "attenuation": round(max(rel, 0) ** 0.5, 4),
        "between_candidate_variance": round(between, 6),
        "noise_variance_of_one_mean": round(noise, 6),
        "signal_to_noise": round(between / noise, 3) if noise else None,
        "pairs_total": len(pairs),
        "pairs_resolvable": nres,
        "pairs_resolvable_fraction": round(nres / len(pairs), 3) if pairs else None,
        "pairs": pairs,
        "warning": (None if rel >= 0.5 and between / noise > 1 else
                    "This target cannot validate a ranking method. The candidate "
                    "ordering it reports is not reproducible on a resampled task "
                    "set, so agreement with it measures nothing."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmarks", nargs="+",
                    default=["livebenchmath", "hotpotqa"])
    ap.add_argument("--out", type=Path, default=REPO / "results" / "targets")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    for b in a.benchmarks:
        for label, run, reps in (
                ("cross_run", f"{b}_measurement_v2", None),
                ("generalization", f"{b}_generalization_v2", None)):
            t = build(b, run, label, reps)
            f = a.out / f"{b}.{label}.json"
            f.write_text(json.dumps(t, indent=2))
            flag = "" if not t["warning"] else "   *** UNUSABLE ***"
            print(f"{b:<14} {label:<15} n={t['n_tasks']:>4} "
                  f"reliability={t['reliability']:>7.3f} "
                  f"s/n={t['signal_to_noise']:>7.2f} "
                  f"resolvable={t['pairs_resolvable']}/{t['pairs_total']}{flag}")
    print(f"\n-> {a.out}")


if __name__ == "__main__":
    main()
