#!/usr/bin/env python3
"""pools-1: the judged / eval partition of the 89 Terminal-Bench 2.0 tasks.

    python3 data/terminalbench/scripts/make_split.py --submissions <dir with Terminus2__*/> --out data/terminalbench/splits/pools-1

judged (20 tasks): repeat 0 is judged; repeats 1-4 are the taxonomy generator's
corpora (generation, refinement, gate, gap) and are never judged.
eval (69 tasks): repeat 0 is the generalization target; never read by any model.

Stratified draw: each task's mean pass rate over the seven frontier Terminus 2
models' five trials (a trial without a verifier reward counts 0, as the
leaderboard counts it) puts it in one of four strata [0,.25) [.25,.5) [.5,.75)
[.75,1]; 20/89 of each stratum is drawn into judged with random.Random(2026),
rounding settled from the last stratum. The AfterQuery submission (an
unresolved-trial outlier) is not used for the strata. Outcomes are used here
for stratification only; the split carries no score.
"""
from __future__ import annotations
import argparse, datetime, glob, json, random, statistics as st
from collections import defaultdict
from pathlib import Path

JUDGED = 20; SEED = 2026


def load_results(submissions: Path):
    res = defaultdict(lambda: defaultdict(list))
    for p in glob.glob(f"{submissions}/Terminus2__*/*/*/result.json"):
        d = json.loads(Path(p).read_text()); m = p.split("/")[-4]
        r = ((d.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        res[m][d["task_name"]].append((d.get("started_at") or "", 0.0 if r is None else float(r)))
    return res


def split(res, seed=SEED, n_judged=JUDGED):
    tasks = sorted(set().union(*[set(v) for v in res.values()])); models = sorted(res)
    mean_pass = {t: st.mean(st.mean(x[1] for x in res[m][t]) for m in models if t in res[m]) for t in tasks}
    rnd = random.Random(seed); strata = defaultdict(list)
    for t in tasks: strata[min(3, int(mean_pass[t] * 4))].append(t)
    judged, evalp = [], []
    for k, ts in sorted(strata.items()):
        rnd.shuffle(ts); j = round(len(ts) * n_judged / len(tasks)); judged += ts[:j]; evalp += ts[j:]
    while len(judged) > n_judged: evalp.append(judged.pop())
    while len(judged) < n_judged: judged.append(evalp.pop())
    return sorted(judged), sorted(evalp), models, {k: len(v) for k, v in sorted(strata.items())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submissions", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--check", action="store_true", help="compare with the split already at --out instead of writing")
    a = ap.parse_args()
    judged, evalp, models, strata = split(load_results(a.submissions))
    doc = {"benchmark": "terminalbench", "split_id": "pools-1", "seed": SEED, "created": datetime.date.today().isoformat(),
           "purpose": "judged = taxonomy generation (repeats 1-4) and judging (repeat 0); eval = the generalization target (repeat 0)",
           "protocol": "four strata by the seven frontier Terminus 2 models' mean pass rate over their five trials (outcomes used for stratification only); "
                       f"{JUDGED}/89 of each stratum drawn into judged with random.Random({SEED}); repeat 0 is the only trial used for judging and for the eval outcomes; "
                       "the judged tasks' repeats 1-4 are the taxonomy generator's corpora and are never judged",
           "strata_models": models, "strata_sizes": strata,
           "sizes": {"judged": len(judged), "eval": len(evalp)}, "portions": {"judged": judged, "eval": evalp}}
    if a.check:
        old = json.loads((a.out / "split.json").read_text())
        same = all(sorted(old["portions"][p]) == doc["portions"][p] for p in ("judged", "eval"))
        print("reproduces the recorded split" if same else "DIFFERS from the recorded split"); raise SystemExit(0 if same else 1)
    a.out.mkdir(parents=True, exist_ok=True); (a.out / "split.json").write_text(json.dumps(doc, indent=1))
    print(f"judged {len(judged)}, eval {len(evalp)}; strata {strata}; -> {a.out / 'split.json'}")


if __name__ == "__main__":
    main()
