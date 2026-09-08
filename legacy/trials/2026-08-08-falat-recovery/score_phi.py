#!/usr/bin/env python3
"""Score the 12 candidates with Phi v0.1 on the rebuilt instruments, then
validate the ranking against gold (after-the-fact only, hard rule 3).

Scoring path reads ONLY:
  scored_stage1.json   mode presence per trace (frozen 16-code taxonomy)
  scored_stage2/       per-(task,mode) recovery from the FALAT-derived graph
Gold is loaded separately, after every score exists, and never enters Phi.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
HOME = Path.home()
HARNESS = HOME / "Desktop/FailureRank/trials/2026-08-07-legacy-hover-phi-harness"
sys.path.insert(0, str(HARNESS))
from phi_harness import phi_v0, phi_v01, kendall_tau  # noqa: E402

TAXONOMY = HERE / "../2026-08-07-adamast-taxonomy-generation/taxonomy_frozen_v1.json"
RUN = HOME / "Desktop/GEPA_Experiments/runs/plain_gepa_hover_seed0_20260804T003430Z"
DELTA, W0 = 0.5, 0.5


def build_phi_inputs():
    """{candidate: {task: {mode: [status,...]}}} — the harness's format."""
    s1 = json.loads((HERE / "scored_stage1.json").read_text())
    meta = {f.stem: json.loads(f.read_text())["metadata"]
            for f in (HERE / "scored_traces").glob("*.json")}
    rec = {}
    for f in (HERE / "scored_stage2").glob("*.json"):
        if f.name in ("recovery.json", "program_prior.json"):
            continue
        d = json.loads(f.read_text())
        rec[d["trace_id"]] = d["mode_recovery"]

    cands = defaultdict(dict)
    no_stage2 = []
    for diag in s1["diagnoses"]:
        tid = diag["trace_id"]
        m = meta[tid]
        codes = {fm["code"] for fm in diag.get("failure_modes") or []}
        mr = rec.get(tid)
        if mr is None and codes:
            no_stage2.append(tid)
        modes = {}
        for c in codes:
            # missing stage-2 => conservative: treat as unrecovered
            status = (mr or {}).get(c, "unrecovered")
            modes[c] = [status]
        cands[f"candidate_{m['candidate_index']:03d}"][m["task_source_id"]] = modes
    return dict(cands), no_stage2


def load_gold():
    """After-the-fact validation only. Never touched by Phi."""
    seed0, g300 = {}, {}
    for cdir in sorted((RUN / "evaluation/gold_do_not_pass_to_judge").glob("candidate_*")):
        per_task, rep0 = defaultdict(list), {}
        for f in cdir.glob("*.json"):
            d = json.loads(f.read_text())
            t = d["task"]["source_id"]
            per_task[t].append(d["gold_score"])
            if d["evaluation_repeat"] == 0:
                rep0[t] = d["gold_score"]
        seed0[cdir.name] = rep0
        g300[cdir.name] = 100 * sum(sum(v) / len(v) for v in per_task.values()) / len(per_task)
    return seed0, g300


def main():
    tax = json.loads(TAXONOMY.read_text())
    K = len(tax["codes"])
    cands, no_stage2 = build_phi_inputs()
    print(f"K={K} | candidates={len(cands)} | "
          f"traces missing stage-2 (scored conservatively): {len(no_stage2)}")

    rows = []
    for cand in sorted(cands):
        tasks = cands[cand]
        n = len(tasks)
        v0, _ = phi_v0(tasks, n, K, DELTA)
        v01, infl, maxco = phi_v01(tasks, n, DELTA, W0)
        pairs = sum(len(m) for m in tasks.values())
        recovered = sum(1 for m in tasks.values() for st in m.values()
                        if st[0] == "fully_recovered")
        rows.append(dict(cand=cand, n=n, phi_v0=v0, phi_v01=v01,
                         modes_per_task=pairs / n,
                         rec_rate=100 * recovered / max(1, pairs),
                         top=sorted(infl.items(), key=lambda kv: -kv[1])[:3]))

    seed0, g300 = load_gold()
    for r in rows:
        rep0 = seed0[r["cand"]]
        ts = cands[r["cand"]].keys()
        r["gold_s0"] = 100 * sum(rep0[t] for t in ts) / len(list(ts))
        r["gold_300"] = g300[r["cand"]]

    print(f"\n{'cand':>13} {'phi_v01':>8} {'phi_v0':>7} {'modes/t':>8} "
          f"{'rec%':>6} {'gold_s0':>8} {'gold300':>8}")
    for r in sorted(rows, key=lambda r: -r["phi_v01"]):
        print(f"{r['cand']:>13} {r['phi_v01']:>8.2f} {r['phi_v0']:>7.2f} "
              f"{r['modes_per_task']:>8.2f} {r['rec_rate']:>6.1f} "
              f"{r['gold_s0']:>8.1f} {r['gold_300']:>8.1f}")

    v01 = [r["phi_v01"] for r in rows]
    v0 = [r["phi_v0"] for r in rows]
    gs0 = [r["gold_s0"] for r in rows]
    g3 = [r["gold_300"] for r in rows]
    print("\n=== gold ladder (Kendall tau-a, 12 candidates) ===")
    print(f"  Phi v0.1      vs gold-300 (generalization): {kendall_tau(v01, g3):+.3f}")
    print(f"  Phi v0        vs gold-300                 : {kendall_tau(v0, g3):+.3f}")
    print(f"  Phi v0.1      vs gold seed-0 (in-sample)  : {kendall_tau(v01, gs0):+.3f}")
    print(f"  outcome-only  vs gold-300 (BASELINE)      : {kendall_tau(gs0, g3):+.3f}")
    print("\n  reference (old shakedown instruments): Phi 0.20, outcome-only 0.46")

    (HERE / "phi_results.json").write_text(json.dumps(
        {"K": K, "delta": DELTA, "w0": W0, "rows": rows,
         "tau": {"v01_vs_gold300": kendall_tau(v01, g3),
                 "v0_vs_gold300": kendall_tau(v0, g3),
                 "v01_vs_gold_seed0": kendall_tau(v01, gs0),
                 "outcome_only_vs_gold300": kendall_tau(gs0, g3)},
         "traces_missing_stage2": no_stage2}, indent=1, default=str))
    print(f"\nwrote {HERE / 'phi_results.json'}")


if __name__ == "__main__":
    main()
