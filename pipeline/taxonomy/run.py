#!/usr/bin/env python3
"""End-to-end taxonomy pipeline. One command, one trace pool in, one
ready-to-use taxonomy out.

    python -m taxonomy.run --benchmark X --pool <dir> --structure <file>

The pool is a directory of traces in AdaMAST format. The pipeline splits it
into three task-disjoint corpora itself (see corpora.py) and runs, per
PIPELINE.md:

    generation
      -> refinement round (judge, then refine)
      -> interannotation gate  -> passed? STOP
      -> ... at most 3 cycles, then STOP regardless

Every stage is resumable: re-running skips completed work and picks up where it
stopped. Every model response is written to disk before it is validated, so a
validation failure is diagnosable and re-runnable for free. Every LLM call
retries transient failures with exponential backoff.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path("/Users/andreicojocaru/Desktop/FailureRank")
sys.path.insert(0, str(REPO / "pipeline"))

import goldfree                              # noqa: E402
from taxonomy import corpora, stages          # noqa: E402
from taxonomy.stages import log               # noqa: E402

MAX_CYCLES = 3


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--pool", type=Path, required=True,
                    help="directory of AdaMAST-format traces to split")
    ap.add_argument("--structure", type=Path, required=True,
                    help="known program structure (skips inference)")
    ap.add_argument("--outcomes", type=Path,
                    help="trace_id -> score sidecar, used ONLY to stratify the "
                         "corpora. Prefer this to outcomes in trace metadata: a "
                         "pool that carries no outcome at all is structurally "
                         "gold-free rather than stripped.")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n-generation", type=int, default=200,
                    help="N: generation corpus size; the rest is derived")
    ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--panel", type=int, default=4)
    ap.add_argument("--panel-temperature", type=float, default=0.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-cycles", type=int, default=MAX_CYCLES)
    ap.add_argument("--no-baseline-gate", action="store_true",
                    help="skip the draft measurement; cycle kappas then have "
                         "nothing to be compared against")
    ap.add_argument("--kappa-target", type=float, default=0.75)
    ap.add_argument("--coverage-floor", type=float, default=0.70)
    ap.add_argument("--plan-only", action="store_true",
                    help="split and report sizes; spend nothing")
    a = ap.parse_args()

    os.environ.setdefault("ADAMAST_PROVIDER", "google")
    os.environ["PYTHONUNBUFFERED"] = "1"
    sys.stdout.reconfigure(line_buffering=True)

    import adamast
    import inspect
    if "FailureRank/pipeline" not in inspect.getfile(adamast):
        raise SystemExit(f"wrong adamast package: {inspect.getfile(adamast)}")
    # every local change present in the module that is actually imported; see
    # CHANGES.md "CORRECTION: changes 1-9 targeted a dead code path"
    from taxonomy import preflight
    preflight.assert_ready()

    a.out.mkdir(parents=True, exist_ok=True)
    state_f = a.out / "pipeline_state.json"
    state = json.loads(state_f.read_text()) if state_f.exists() else {
        "benchmark": a.benchmark, "cycles": [], "status": "running"}
    # settings travel with the run so promote.py can cite them without guessing
    state["settings"] = {"model": a.model, "n_generation": a.n_generation,
                         "outcomes": str(a.outcomes) if a.outcomes else None,
                         "panel": a.panel, "panel_temperature": a.panel_temperature,
                         "max_cycles": a.max_cycles, "kappa_target": a.kappa_target,
                         "coverage_floor": a.coverage_floor,
                         "pool": str(a.pool), "structure": str(a.structure)}

    def save():
        state_f.write_text(json.dumps(state, indent=2, default=str))

    t0 = time.time()
    log("=" * 66)
    log(f"TAXONOMY PIPELINE  benchmark={a.benchmark}  N={a.n_generation}  "
        f"max_cycles={a.max_cycles}")
    log("=" * 66)

    # ---- split -----------------------------------------------------------
    split = corpora.plan(a.pool, a.n_generation, outcomes=a.outcomes)
    m = split.manifest
    log(f"pool: {m['pool_traces']} traces over {m['pool_tasks']} tasks")
    for name in ("generation", "refinement", "gate"):
        d = m[name]
        log(f"  {name:11} {d['traces']:>4} traces / {d['tasks']:>3} tasks "
            f"({d['failing']} failing)")
    dirs = corpora.materialise(split, a.out)
    log("  corpora are task-disjoint (asserted)")
    for name, d in dirs.items():
        goldfree.assert_gold_free(d, f"corpus_{name}")
    log("  corpora are gold-free (asserted)")
    state["split"] = {k: m[k] for k in ("generation", "refinement", "gate")}
    save()
    if a.plan_only:
        log("plan only: nothing spent")
        return

    structure = json.loads(a.structure.read_text())

    # ---- generation ------------------------------------------------------
    log("-" * 66)
    tax_path = stages.generate(a.benchmark, dirs["generation"], a.out / "generation",
                               a.model, a.structure, kappa=a.kappa_target,
                               coverage=a.coverage_floor)
    draft = json.loads(tax_path.read_text())
    current = {"repo": a.benchmark, "domain": draft.get("domain", a.benchmark),
               "codes": draft["codes"]}
    ag = (draft.get("generation") or {}).get("agreement") or {}
    if ag.get("skipped"):
        log(f"generation status: {draft.get('status')} "
            "(agreement skipped by design; the cycle gate certifies)")
    else:
        log(f"generation status: {draft.get('status')} "
            f"(kappa {ag.get('final_kappa')})")
    state["generation"] = {"codes": len(current["codes"]),
                           "status": draft.get("status")}
    save()

    # ---- baseline ---------------------------------------------------------
    # A measurement of the DRAFT, before any refinement touches it. Without it
    # the cycle kappas have no reference and the pipeline cannot say whether
    # refinement improved the vocabulary or merely moved it.
    #
    # Diagnostic only, never a stopping rule. Kappa measures agreement and
    # nothing else: a draft can agree well while missing half the failure modes,
    # and refinement does more than raise agreement -- it fixes subject and
    # observability errors, corrects adequacy, and ADDs codes from unmapped
    # evidence. Passing here would say the vocabulary is coherent, not complete.
    #
    # Safe on the certification corpus only because the gate no longer modifies
    # the taxonomy (agreement.Config.INTERNAL_REFINEMENT). Nothing is fitted to
    # it, and holding the corpus constant is what makes the numbers comparable.
    if not a.no_baseline_gate:
        log("-" * 66)
        log("BASELINE  (draft, diagnostic only -- never stops the loop)")
        b = stages.gate(current, draft, dirs["gate"], a.out / "baseline_gate",
                        a.model, a.kappa_target, a.coverage_floor)
        state["baseline"] = {
            "codes": len(current["codes"]),
            "kappa": b.get("certifying_kappa"),
            "coverage": b.get("final_coverage"),
            "n_subjects": (b.get("pooled") or {}).get("n_subjects"),
            "codes_exercised": len((b.get("pooled") or {}).get("codes_exercised") or []),
            "would_have_passed": bool(b.get("passed")),
            "note": "diagnostic; the draft is refined regardless of this number",
        }
        save()
        log(f"baseline: kappa={state['baseline']['kappa']} "
            f"over {state['baseline']['n_subjects']} subjects, "
            f"{state['baseline']['codes_exercised']} codes exercised "
            f"(would_have_passed={state['baseline']['would_have_passed']}) "
            "-- refining regardless")

    # ---- loop ------------------------------------------------------------
    passed = False
    for cycle in range(1, a.max_cycles + 1):
        log("-" * 66)
        log(f"CYCLE {cycle}/{a.max_cycles}")
        cdir = a.out / f"cycle_{cycle}"
        cdir.mkdir(exist_ok=True)
        (cdir / "taxonomy_in.json").write_text(json.dumps(current, indent=2))

        diag = stages.judge(current, dirs["refinement"], cdir / "judged",
                            a.model, workers=a.workers)
        current = stages.refine(current, diag, dirs["refinement"], structure,
                                cdir / "refined", a.model, panel=a.panel,
                                temperature=a.panel_temperature)
        summary = stages.gate(current, draft, dirs["gate"], cdir / "gate",
                              a.model, a.kappa_target, a.coverage_floor)

        state["cycles"].append({
            "cycle": cycle, "codes": len(current["codes"]),
            "kappa": summary.get("final_kappa"),
            "coverage": summary.get("final_coverage"),
            "passed": bool(summary.get("passed"))})
        save()
        if summary.get("codebook"):
            # carries the condition under which this cycle's kappa was measured
            current["codebook"] = summary["codebook"]
        if summary.get("passed"):
            passed = True
            log(f"CYCLE {cycle}: gate PASSED, stopping")
            break
        log(f"CYCLE {cycle}: gate not passed"
            + (", continuing" if cycle < a.max_cycles else ", cycle limit reached"))

    # ---- finish ----------------------------------------------------------
    final = a.out / "taxonomy_final.json"
    current["certified"] = passed
    final.write_text(json.dumps(current, indent=2))
    state["status"] = "passed" if passed else "not_certified"
    state["final_codes"] = len(current["codes"])
    state["minutes"] = round((time.time() - t0) / 60, 1)
    save()

    log("=" * 66)
    log(f"DONE  codes={len(current['codes'])}  certified={passed}  "
        f"cycles={len(state['cycles'])}  {state['minutes']} min")
    base = state.get("baseline") or {}
    if base:
        log(f"  baseline (draft): {base['codes']} codes, kappa={base['kappa']}")
    for c in state["cycles"]:
        log(f"  cycle {c['cycle']}: {c['codes']} codes, kappa={c['kappa']}, "
            f"coverage={c['coverage']}, passed={c['passed']}")
    if base and state["cycles"]:
        d = (state["cycles"][-1].get("kappa") or 0) - (base.get("kappa") or 0)
        log(f"  refinement moved kappa by {d:+.3f} "
            f"({base.get('kappa')} -> {state['cycles'][-1].get('kappa')})")
    if not passed:
        log("  NOT CERTIFIED: shipping with the failure recorded, per PIPELINE.md")
    log(f"  final taxonomy: {final}")


if __name__ == "__main__":
    main()
