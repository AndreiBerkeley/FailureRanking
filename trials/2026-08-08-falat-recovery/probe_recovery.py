#!/usr/bin/env python3
"""Two probes, offline, gold only after the fact:

A. Multi-label: how often do several modes land on ONE failure point
   (same trace, same step)? Then simulate Andrei's hypothetical — one
   mode per failure point — and re-score.
B. Recovery value: sweep how much a recovery is worth, INCLUDING the
   diagnostic region delta>1 where recovering raises the charge. That
   asks directly whether recovery is a negative quality signal here.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "../2026-08-07-legacy-hover-phi-harness"))
import phi_harness as ph  # noqa: E402
from score_phi import load_gold, TAXONOMY  # noqa: E402

CONF_RANK = {"high": 3, "medium": 2, "low": 1, "": 0}
SEV_RANK = {"critical": 4, "major": 3, "moderate": 2, "minor": 1, "": 0}


def load_records():
    meta = {f.stem: json.loads(f.read_text())["metadata"]
            for f in (HERE / "scored_traces").glob("*.json")}
    s1 = {d["trace_id"]: (d.get("failure_modes") or [])
          for d in json.loads((HERE / "scored_stage1.json").read_text())["diagnoses"]}
    recs = []
    for f in (HERE / "scored_stage2").glob("*.json"):
        if f.name in ("recovery.json", "program_prior.json"):
            continue
        d = json.loads(f.read_text())
        d["meta"] = meta[d["trace_id"]]
        d["s1"] = s1.get(d["trace_id"], [])
        recs.append(d)
    return recs


def build(recs, one_per_point: bool):
    """{candidate: {task: {mode: [status]}}}; optionally collapse each
    failure point (same step) to its single best-supported mode."""
    prio = {}
    for r in recs:
        for fm in r["s1"]:
            prio[(r["trace_id"], fm["code"])] = (
                CONF_RANK.get(str(fm.get("confidence", "")).lower(), 0),
                SEV_RANK.get(str(fm.get("severity", "")).lower(), 0))
    cands = defaultdict(dict)
    for r in recs:
        occ = {o["id"]: o for o in r["occurrences"]}
        keep = []
        for oid, st in r["statuses"].items():
            o = occ.get(oid)
            if o:
                keep.append((o.get("step"), o.get("code"), st["status"]))
        if one_per_point:
            by_step = defaultdict(list)
            for step, code, status in keep:
                by_step[step].append((code, status))
            keep = []
            for step, items in by_step.items():
                code, status = max(
                    items, key=lambda cs: prio.get((r["trace_id"], cs[0]), (0, 0)))
                keep.append((step, code, status))
        modes = defaultdict(list)
        for _step, code, status in keep:
            modes[code].append(status)
        cands[f"candidate_{r['meta']['candidate_index']:03d}"][
            r["meta"]["task_source_id"]] = dict(modes)
    return dict(cands)


def phi_delta(tasks, delta, w0, allow_gt1=False):
    """Phi v0.1 with delta free to exceed 1 (diagnostic only: delta>1
    means a recovered mode is charged MORE, not less)."""
    import math
    affected, recovered = ph.per_mode_rates(tasks)
    q = {}
    for m, aff in affected.items():
        rr = recovered.get(m, 0) / aff
        val = w0 * (delta ** rr)
        q[m] = min(val, 0.999) if allow_gt1 else val
    burdens = []
    for modes in tasks.values():
        qs = [q[m] for m in modes]
        burdens.append(1.0 - math.prod(1.0 - x for x in qs))
    return 100.0 * (1.0 - sum(burdens) / len(tasks))


def tau_of(score_fn, cands, gold):
    names = sorted(cands)
    return ph.kendall_tau([score_fn(cands[c]) for c in names],
                          [gold[c] for c in names])


def main():
    K = len(json.loads(TAXONOMY.read_text())["codes"])
    recs = load_records()
    _, g300 = load_gold()

    # ---- A. how much multi-labelling is there?
    pts = shared = 0
    per_point = Counter()
    for r in recs:
        occ = {o["id"]: o for o in r["occurrences"]}
        by_step = defaultdict(set)
        for oid in r["statuses"]:
            o = occ.get(oid)
            if o:
                by_step[o.get("step")].add(o.get("code"))
        for step, codes in by_step.items():
            pts += 1
            per_point[len(codes)] += 1
            if len(codes) > 1:
                shared += 1
    print("=== A. multi-label structure ===")
    print(f"  failure points (distinct trace-steps): {pts}")
    print(f"  points carrying >1 mode: {shared} ({100*shared/pts:.1f}%)")
    print(f"  modes per point: {dict(sorted(per_point.items()))}")

    full = build(recs, one_per_point=False)
    one = build(recs, one_per_point=True)
    fm = sum(len(m) for t in full.values() for m in t.values())
    om = sum(len(m) for t in one.values() for m in t.values())
    print(f"  (task,mode) pairs: full {fm} -> one-per-point {om} "
          f"({100*(fm-om)/fm:.1f}% removed)")

    print("\n=== A2. re-scored under one-mode-per-failure-point ===")
    for label, cands in (("as-judged   ", full), ("1 mode/point", one)):
        t0 = tau_of(lambda tk: ph.phi_v0(tk, len(tk), K, 0.5)[0], cands, g300)
        t1 = tau_of(lambda tk: ph.phi_v01(tk, len(tk), 0.5, 0.5)[0], cands, g300)
        tb = tau_of(lambda tk: tau_best(tk), cands, g300) if False else None
        print(f"  {label}: v0 {t0:+.3f} | v0.1 {t1:+.3f}")

    # ---- B. what is a recovery worth?
    print("\n=== B. value of recovery (delta), Phi v0.1 w0=0.1, vs gold-300 ===")
    print("  delta<1 = recovery reduces charge | delta>1 = recovery RAISES it")
    for cands, label in ((full, "as-judged   "), (one, "1 mode/point")):
        cells = []
        for d in (0.3, 0.5, 0.7, 0.9, 1.0, 1.5, 2.0, 3.0):
            cells.append((d, tau_of(
                lambda tk, dd=d: phi_delta(tk, dd, 0.1, allow_gt1=True),
                cands, g300)))
        print(f"  {label}: " + "  ".join(f"d={d}:{t:+.3f}" for d, t in cells))

    print("\n  outcome-only baseline: +0.439 | prevalence-only: +0.561")


if __name__ == "__main__":
    main()
