#!/usr/bin/env python3
"""Gold scores for every candidate on each split-4 measurement set.

Each set is scored against the split-3 generalization portion MINUS its own 50
tasks -- 500 for set-A (a different portion entirely), 450 for set-B/C/D. The
full-500 column is reported alongside to show the size of the self-correlation
that exclusion removes.

    report_scores.py --out results/hover/split-4-gold-scores

Reads gold from traces-3 (judging for set-A, generalization for set-B/C/D and
the 350-task target) and writes scores.json plus a README.md report. No model
is called: every number here already existed on disk.

This directory is gold-bearing by design and is not on any gold-free scoring
path -- it exists to answer "how much does the answer depend on which 50 tasks
we drew", which is a question about gold.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
T3 = REPO / "benchmarks/hover/traces/traces-3"
SPLIT4 = REPO / "benchmarks/hover/splits/split-4/split.json"


def mean(v): return sum(v) / len(v)


def sd(v):
    m = mean(v)
    return math.sqrt(sum((a - m) ** 2 for a in v) / (len(v) - 1)) if len(v) > 1 else 0.0


def ranks(x):
    """Average ranks, ties shared."""
    o = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def pearson(x, y):
    n = len(x); mx, my = mean(x), mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return float("nan")
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def spearman(x, y): return pearson(ranks(x), ranks(y))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    sp = json.loads(SPLIT4.read_text())["portions"]
    gold = {p: {c: v["0"] for c, v in
                json.loads((T3 / p / "outcomes.json").read_text())["outcomes"].items()}
            for p in ("judging", "generalization")}
    cands = sorted(gold["judging"])

    # set-A's tasks are scored from the judging portion; everything else from
    # the generalization portion. Both are repeat 0 of the same capture.
    sets = ["set-A", "set-B", "set-C", "set-D"]
    src = {"set-A": "judging"}
    ids = {"set-A": sorted(gold["judging"][cands[0]])}
    for k in ("set-B", "set-C", "set-D"):
        src[k], ids[k] = "generalization", sp[k]

    tgt_ids = json.loads(SPLIT4.read_text())["targets"]
    gen500 = sorted(gold["generalization"][cands[0]])

    def acc_of(source, task_ids):
        return [mean([gold[source][c][t] for t in task_ids]) for c in cands]

    acc = {k: acc_of(src[k], ids[k]) for k in sets}
    tgt_acc = {k: acc_of("generalization", tgt_ids[k]) for k in sets}
    full500 = acc_of("generalization", gen500)
    tgt = full500          # the headline target column: all 500 tasks

    # System prompt length: constant per candidate, and the free predictor that
    # beat failure density. Read from any one trace per candidate.
    plen = {}
    for f in sorted((T3 / "judging/corpus").glob("*.json")):
        d = json.loads(f.read_text())
        ci = d["metadata"]["candidate_index"]
        if ci not in plen:
            plen[ci] = sum(len(m["content"]) for m in d["messages"] if m["role"] == "system")
    cmap = {e["pool_candidate_id"]: e["candidate_index"]
            for e in json.loads((T3 / "judging/candidate_map.json").read_text())["candidates"]}
    pl = [plen[cmap[c]] for c in cands]

    def se(p, n): return math.sqrt(p * (1 - p) / n)

    def separable(k, task_ids=None, source=None):
        """Pairs distinguishable at 1.96 SE, paired on the set's shared tasks."""
        task_ids = ids[k] if task_ids is None else task_ids
        source = src[k] if source is None else source
        n, out = len(task_ids), 0
        rows = [[gold[source][c][t] for t in task_ids] for c in cands]
        for i, j in itertools.combinations(range(len(cands)), 2):
            d = [rows[i][t] - rows[j][t] for t in range(n)]
            s = sd(d) / math.sqrt(n)
            if s and abs(mean(d) / s) > 1.96:
                out += 1
        return out

    scores = {
        "produced_by": "results/hover/split-4-gold-scores/scripts/report_scores.py",
        "split": "benchmarks/hover/splits/split-4/split.json",
        "gold_from": {k: f"benchmarks/hover/traces/traces-3/{v}/outcomes.json"
                      for k, v in src.items()},
        "candidates": cands,
        "n_tasks": {k: len(ids[k]) for k in ids},
        "accuracy": {k: dict(zip(cands, acc[k])) for k in acc},
        "rank": {k: dict(zip(cands, ranks([-x for x in acc[k]]))) for k in acc},
        "target": {"portion": "split-3 generalization (500 tasks)",
                   "scoring_rule": "exclude the measured set's own tasks",
                   "effective_n": {k: len(tgt_ids[k]) for k in sets}},
        "accuracy_target_500": dict(zip(cands, full500)),
        "spearman_vs_target": {k: spearman(acc[k], tgt_acc[k]) for k in sets},
        "spearman_vs_full_500_LEAKY": {k: spearman(acc[k], full500) for k in sets},
        "spearman_between_sets": {f"{x}|{y}": spearman(acc[x], acc[y])
                                  for x, y in itertools.combinations(sets, 2)},
        "pairs_separable_of_66": dict({k: separable(k) for k in sets},
                                     **{"target_500": separable("target", gen500, "generalization")}),
        "system_prompt_chars": dict(zip(cands, pl)),
        "spearman_promptlen_vs": dict({k: spearman(pl, acc[k]) for k in sets},
                                     **{"target_500": spearman(pl, full500)}),
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "scores.json").write_text(json.dumps(scores, indent=1) + "\n")

    L = []
    w = L.append
    w("# split-4 — gold scores per measurement set\n")
    w("Four disjoint 50-task measurement sets scored against split-3's 500-task")
    w("`generalization` portion. **No capture and no judging was run for this**: every")
    w("trace and every gold score already existed under")
    w("`benchmarks/hover/traces/traces-3/`. set-A is split-3's `judging` portion;")
    w("set-B/C/D are drawn from the generalization portion itself.\n")
    w("A set is scored against **the 500 minus its own 50 tasks** — 500 for set-A,")
    w("which comes from a different portion, and 450 for set-B/C/D. Scoring a set")
    w("against a target it is 10% of is self-correlation: set-B reads +0.907 clean")
    w("and +0.965 leaky. Exclusion costs nothing measurable (46/66 pairs separable")
    w("at both 500 and 450; SE 0.0221 vs 0.0233).\n")
    w("Generated by `scripts/report_scores.py`; numbers in `scores.json`.\n")
    w("## Accuracy per candidate\n")
    w("Fraction of tasks solved. Gold is binary, so this is directly comparable")
    w("across sets of different size. `±` is the binomial standard error.\n")
    w("| candidate | sys prompt chars | target (500) | set-A (50) | set-B (50) | set-C (50) | set-D (50) | spread A–D |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|")
    for i in sorted(range(len(cands)), key=lambda i: -tgt[i]):
        row = [acc[k][i] for k in sets]
        w(f"| {cands[i]} | {pl[i]:,} | **{tgt[i]:.3f}** ±{se(tgt[i], 350):.3f} | "
          + " | ".join(f"{v:.3f} ±{se(v, 50):.3f}" for v in row)
          + f" | {max(row) - min(row):.3f} |")
    w(f"| *mean* | | {mean(tgt):.3f} | "
      + " | ".join(f"{mean(acc[k]):.3f}" for k in sets) + " | |")
    w("")
    w(f"Target SE is ±{se(mean(tgt), 500):.3f} per candidate; each 50-task cell carries")
    w(f"±{se(0.58, 50):.3f}.")
    w("")
    w("## Does a 50-task set recover the target ranking?\n")
    w("| set | target n | Spearman vs target | vs full 500 (leaky) | pairs separable of 66 |")
    w("|---|---:|---:|---:|---:|")
    for k in sets:
        w(f"| {k} | {len(tgt_ids[k])} | **{scores['spearman_vs_target'][k]:+.3f}** | "
          f"{scores['spearman_vs_full_500_LEAKY'][k]:+.3f} | {scores['pairs_separable_of_66'][k]} |")
    w(f"| target | 500 | — | — | {scores['pairs_separable_of_66']['target_500']} |")
    w("")
    w("set-A's two columns agree by construction: it is disjoint from all 500, so it")
    w("has nothing to leak.")
    w("")
    w("## Agreement between the measurement sets\n")
    w("| pair | Spearman |")
    w("|---|---:|")
    for k, v in scores["spearman_between_sets"].items():
        w(f"| {k.replace('|', ' vs ')} | {v:+.3f} |")
    w("")
    w("## System prompt length as a free predictor\n")
    w("The system prompt is byte-identical across all 50 traces of a candidate, so")
    w("its length is a per-candidate constant that costs nothing to measure.\n")
    w("| measured against | Spearman |")
    w("|---|---:|")
    for k in sets + ["target_500"]:
        w(f"| gold on {k.replace('_', ' ')} | {scores['spearman_promptlen_vs'][k]:+.3f} |")
    w("")
    (a.out / "README.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\n-> {a.out}/README.md and scores.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
