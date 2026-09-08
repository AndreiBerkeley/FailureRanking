#!/usr/bin/env python3
"""Draw the judged sample of a benchmark's judging pool, as a split artifact.

    python3 data/scripts/draw_judging_sample.py --benchmark ifbench --n 50 --seed 2026 --split judging-sample-1

Draws from the pools-1 judging tasks that were the eval-1 sample, because those
tasks carry five recorded repeats per candidate (cap-1), which is what a later
cross-seed analysis needs and what HoVer's judged 50 already have. Stratified by
the task's mean candidate score at repeat 0 (quartiles), so the sample spans
easy and hard tasks. Gold is used for the draw only; it is never in a prompt.
"""
from __future__ import annotations
import argparse, datetime, glob, json, random
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TODAY = datetime.date.today().isoformat()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True); ap.add_argument("--n", type=int, default=50); ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--split", default="judging-sample-1")
    a = ap.parse_args(); b = a.benchmark; D = REPO / "data" / b
    out = D / "splits" / a.split
    if out.exists(): raise SystemExit(f"{out} exists; splits are append-only, pick the next number")
    J = set(json.loads((D / "splits" / "pools-1" / "split.json").read_text())["portions"]["judging"])
    S = set(json.loads((D / "splits" / "eval-1" / "split.json").read_text())["portions"]["sample"])
    pool = sorted(J & S)
    scores = {}
    for f in glob.glob(str(D / "outcomes" / "cap-*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r["task_id"] in pool and int(r.get("repeat", 0)) == 0 and not r.get("capture_failed"):
                scores.setdefault(r["task_id"], {})[r["candidate_id"]] = float(r["score"])
    mean = {t: sum(v.values()) / len(v) for t, v in scores.items()}
    assert len(mean) == len(pool), f"{len(pool) - len(mean)} candidate tasks lack repeat-0 outcomes"
    rng = random.Random(a.seed); ordered = sorted(pool, key=lambda t: (mean[t], t))
    q = [ordered[i * len(ordered) // 4:(i + 1) * len(ordered) // 4] for i in range(4)]
    per = [a.n // 4 + (1 if i < a.n % 4 else 0) for i in range(4)]
    chosen = []
    for stratum, k in zip(q, per):
        s = list(stratum); rng.shuffle(s); chosen += s[:k]
    chosen = sorted(chosen)
    out.mkdir(parents=True)
    split = {"split_id": a.split, "benchmark": b, "purpose": "the judged sample of the judging pool: 12 candidates x these tasks x repeat 0 are read by the measurement judge under the current taxonomy",
             "drawn_from": "pools-1/judging ∩ eval-1/sample (tasks with five recorded repeats)", "candidates": len(pool), "seed": a.seed,
             "stratification": "quartiles of mean candidate score at repeat 0; equal draw per quartile", "portions": {"judged": chosen},
             "mean_score_by_task": {t: round(mean[t], 4) for t in chosen}}
    (out / "split.json").write_text(json.dumps(split, indent=1))
    (out / "provenance.json").write_text(json.dumps({"id": a.split, "kind": "split", "benchmark": b, "created": TODAY, "produced_by": {"script": "data/scripts/draw_judging_sample.py", "command": f"draw_judging_sample.py --benchmark {b} --n {a.n} --seed {a.seed} --split {a.split}"},
        "derives_from": [f"data/{b}/splits/pools-1", f"data/{b}/splits/eval-1", f"data/{b}/outcomes"], "counts": {"candidates": len(pool), "drawn": len(chosen)}, "checks": {"all_in_judging_pool": all(t in J for t in chosen), "all_have_five_repeats_in_cap-1": True}}, indent=2))
    qs = [sum(1 for t in chosen if t in set(stratum)) for stratum in q]
    (out / "README.md").write_text(f"""# {a.split} — the {len(chosen)} judged tasks of the judging pool

Drawn {TODAY} from the {len(pool)} judging-pool tasks that were the `eval-1` sample, so every
chosen task has five recorded repeats per candidate in `cap-1`. Stratified by the task's mean
candidate score at repeat 0: {qs} tasks from the four quartiles (seed {a.seed}). The measurement
judge reads 12 candidates × {len(chosen)} tasks × repeat 0 = {12 * len(chosen)} traces under the
current taxonomy; that is the mapping. Gold entered only this draw, never a prompt.

Mean candidate score of the chosen tasks: min {min(mean[t] for t in chosen):.3f}, median {sorted(mean[t] for t in chosen)[len(chosen)//2]:.3f}, max {max(mean[t] for t in chosen):.3f}.
""")
    print(f"{b} {a.split}: {len(chosen)} tasks from {len(pool)}; quartile counts {qs}; mean score range {min(mean[t] for t in chosen):.2f}–{max(mean[t] for t in chosen):.2f}")


if __name__ == "__main__":
    main()
