#!/usr/bin/env python3
"""pools-3 (and the superseded pools-1, pools-2): the taxonomy / judged / eval partition of the 500 SWE-bench Verified tasks.

    python3 data/swebench/scripts/make_split.py --split-id pools-3 --out data/swebench/splits/pools-3 [--check]

pools-3: taxonomy 30 / judged 50 / eval 420 (Andrei, 2026-09-24). The taxonomy pool feeds the gate-free pipeline:
generation 16 tasks x 4 traces, refinement 9 x 3, gap test 5 x 4, every stage on its own tasks. The judged draw comes
first with the same seed, so the judged 50 are pools-2's.

pools-2 raises judged from 25 to 50 (Andrei, 2026-09-24): at 25 the ranking resolves pass-rate gaps of about
0.18 while 9 of the 12 candidates sit within 0.07, and 13 of the 25 were tasks every candidate solves or none does.
pools-2 sizes: taxonomy 75 / judged 50 / eval 375 (J/G 13%). pools-1 (below) was 75 / 25 / 400.

Sizes follow sharing/pipeline.md §2 at N = 500, with the taxonomy pool sized for the whole generation
pipeline rather than its generation corpus alone: T_gen = 4% N = 20 tasks (80 traces at 4 per task), plus the
same number of refinement tasks, 15 gate tasks and 20 gap-test tasks -> taxonomy 75; judged J = 5% N = 25;
eval G = 400 (J/G = 6.3%, above the rule's 5.5% because the taxonomy pool is larger than T_gen).
Strata: each task's mean resolve rate over the 12 mini-v2-1 candidates (outcomes/cap-1.jsonl; stratification
only): none resolve / under half / half or more / all resolve. Each portion takes its share of every stratum,
drawn with random.Random(2026). One trace per candidate per task (no repeats).
"""
from __future__ import annotations
import argparse, datetime, json, statistics as st, sys
from collections import defaultdict
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(REPO / "data" / "scripts"))
from stratified import strata_of, allocate  # noqa: E402

SEED = 2026
SPLITS = {"pools-1": {"judged": 25, "taxonomy": 75, "eval": 400},   # superseded 2026-09-24, never used
          "pools-2": {"judged": 50, "taxonomy": 75, "eval": 375},   # judged raised to 50 (Andrei, 2026-09-24); superseded, never used
          "pools-3": {"judged": 50, "taxonomy": 30, "eval": 420}}   # taxonomy pool 30 for the gate-free pipeline (Andrei, 2026-09-24)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True); ap.add_argument("--check", action="store_true")
    ap.add_argument("--split-id", default="pools-3", choices=sorted(SPLITS))
    a = ap.parse_args(); D = REPO / "data" / "swebench"; SIZES = SPLITS[a.split_id]
    cands = json.loads((D / "candidates" / "sets" / "mini-v2-1.json").read_text())["active_candidate_ids"]
    tasks = [json.loads(l)["task_id"] for l in open(D / "tasks" / "tasks.jsonl")]
    res = defaultdict(list)
    for l in open(D / "outcomes" / "cap-1.jsonl"):
        o = json.loads(l)
        if o["candidate_id"] in cands: res[o["task_id"]].append(o["score"])
    mean_pass = {t: st.mean(res[t]) for t in tasks}
    strata = strata_of(mean_pass); por = allocate(strata, SIZES, SEED)
    doc = {"benchmark": "swebench", "split_id": a.split_id, "seed": SEED, "created": datetime.date.today().isoformat(),
           "purpose": "taxonomy = the generation pipeline's corpora (generation, refinement, gate, gap); judged = judging; eval = the generalization target",
           "protocol": "four strata by the 12 mini-v2-1 candidates' mean resolve rate (none / under half / half or more / all; outcomes for stratification only); "
                       f"each portion takes its proportional share of every stratum, drawn with random.Random({SEED}); one trace per candidate per task",
           "strata_candidates": cands, "strata_sizes": {str(k): len(v) for k, v in strata.items()},
           "sizes": {p: len(v) for p, v in por.items()}, "portions": por}
    if a.check:
        old = json.loads((a.out / "split.json").read_text()); same = all(sorted(old["portions"][p]) == por[p] for p in por)
        print("reproduces the recorded split" if same else "DIFFERS from the recorded split"); raise SystemExit(0 if same else 1)
    a.out.mkdir(parents=True, exist_ok=True); (a.out / "split.json").write_text(json.dumps(doc, indent=1))
    print(f"sizes {doc['sizes']}; strata {doc['strata_sizes']}; -> {a.out / 'split.json'}")
    for p, v in por.items():
        print(f"  {p}: mean pass {st.mean(mean_pass[t] for t in v):.3f}, by stratum {[sum(1 for t in v if t in set(strata[s])) for s in strata]}")


if __name__ == "__main__":
    main()
