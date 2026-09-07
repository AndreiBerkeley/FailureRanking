#!/usr/bin/env python3
"""Promote a finished pipeline run into a benchmark taxonomy artifact.

    python -m taxonomy.promote --run <run_dir> [--dry-run]

The pipeline leaves `taxonomy_final.json` inside its run directory, which is
scratch. This copies it into `benchmarks/<benchmark>/taxonomies/tax-N` as a
citable artifact with a README and a provenance.json, per CLAUDE.md.

Append-only: N is the next free number. An existing tax-N is never overwritten
and never edited. A superseded taxonomy stays where it is and is marked
superseded in its own README by hand.

The artifact records the exact task ids each corpus consumed. Those tasks are
spent: a later measurement run that reuses them is no longer reading a taxonomy
built on disjoint evidence.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/Users/andreicojocaru/Desktop/FailureRank")
PIPE = REPO / "pipeline"


def pipeline_commit() -> dict:
    """Identify the vendored adamast and any uncommitted drift in it."""
    prov = PIPE / "PROVENANCE.json"
    info = json.loads(prov.read_text()) if prov.exists() else {}
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "pipeline"],
                               cwd=REPO, capture_output=True, text=True, timeout=30)
        info["uncommitted_pipeline_changes"] = bool(dirty.stdout.strip())
    except Exception:
        info["uncommitted_pipeline_changes"] = "unknown"
    return info


def certification_scope(run: Path, tax: dict) -> dict:
    """What the reported kappa actually measured.

    Kappa is computed over reconciled errors, not over codes. A 30-trace gate
    yields on the order of 10-30 errors, which cannot exercise a 20-code
    taxonomy. Reporting the scalar alone implies the whole vocabulary was
    certified; this records how much of it really was.
    """
    from collections import Counter
    assigned, rounds = Counter(), []
    for f in sorted(run.glob("**/round_*.json")):
        try:
            r = json.loads(f.read_text())
        except Exception:                                      # noqa: BLE001
            continue
        if "code_distribution" not in r:
            continue
        rounds.append({"round": r.get("round"), "kappa": r.get("kappa"),
                       "n_subjects": r.get("kappa_n_subjects"),
                       "errors": r.get("total_errors")})
        for code, n in (r.get("code_distribution") or {}).items():
            assigned[code] += n
    # the gate's own pooled statistic, when the run produced one
    pooled = {}
    for f in sorted(run.glob("**/gate_summary.json")):
        try:
            s = json.loads(f.read_text())
        except Exception:                                      # noqa: BLE001
            continue
        if s.get("pooled"):
            pooled = {"certifying_kappa": s.get("certifying_kappa"),
                      "certified_on": s.get("certified_on"),
                      "pooled_n_subjects": s["pooled"].get("n_subjects"),
                      "per_code_kappa": s["pooled"].get("per_code_kappa"),
                      "final_round_kappa": s.get("final_kappa"),
                      "final_round_n_subjects": s.get("final_kappa_n_subjects")}
    all_ids = {c["id"] for c in tax["codes"]}
    return {
        "pooled": pooled,
        "codes_total": len(all_ids),
        "codes_exercised": sorted(set(assigned) & all_ids),
        "codes_never_exercised": sorted(all_ids - set(assigned)),
        "assignments_per_code": dict(assigned.most_common()),
        "rounds": rounds,
        "note": ("kappa is computed over reconciled errors, not codes; codes "
                 "never exercised carry no agreement evidence either way"),
    }


def next_id(tax_dir: Path) -> str:
    used = []
    for d in tax_dir.glob("tax-*"):
        if d.is_dir() and d.name[4:].isdigit():
            used.append(int(d.name[4:]))
    return f"tax-{max(used) + 1 if used else 1}"


def render_readme(tid, bench, tax, state, manifest, prov) -> str:
    codes = tax["codes"]
    cats = Counter(str(c.get("category", "?")).upper()[:1] for c in codes)
    certified = bool(tax.get("certified"))
    cycles = state.get("cycles", [])
    gen = state.get("generation", {})

    L = [f"# {tid} — {bench} failure taxonomy", ""]
    L.append(f"{len(codes)} codes "
             f"(A {cats.get('A', 0)}, B {cats.get('B', 0)}, C {cats.get('C', 0)}).")
    L.append("")

    scope = state.get("certification_scope") or {}
    n_ex = len(scope.get("codes_exercised") or [])
    n_all = scope.get("codes_total") or len(codes)
    if certified:
        p = next((c for c in cycles if c.get("passed")), {})
        L += ["**Certified.** Passed the interannotation gate on cycle "
              f"{p.get('cycle', '?')} with kappa {p.get('kappa')} and coverage "
              f"{p.get('coverage')}.", ""]
        if scope:
            L += [f"**Read that number narrowly.** Kappa is computed over "
                  f"reconciled errors, not over codes, and only {n_ex} of {n_all} "
                  "codes were ever assigned by an annotator. It says annotators "
                  "who found an error agreed how to code it; it says nothing "
                  "about the "
                  f"{len(scope.get('codes_never_exercised') or [])} codes that "
                  "never fired. Per-code detail is in `provenance.json`.", ""]
    else:
        L += ["**Not certified.** The interannotation gate was not passed within "
              f"{len(cycles)} cycles. Per `PIPELINE.md` the taxonomy ships carrying "
              "that failure rather than being iterated until it agrees with itself. "
              "Any result computed with it inherits the failure and must say so.", ""]

    L += ["## How it was produced", "",
          "`PIPELINE.md` is the procedure. Generation induced a draft vocabulary; "
          "each cycle judged the refinement corpus, refined by four-reviewer panel, "
          "then measured interannotator agreement on the gate corpus.", ""]

    L += ["| cycle | codes | kappa | coverage | passed |", "|---|---|---|---|---|"]
    if gen:
        L.append(f"| generation | {gen.get('codes')} | - | - | - |")
    base = state.get("baseline") or {}
    if base:
        L.append(f"| baseline (draft) | {base.get('codes')} | {base.get('kappa')} "
                 f"| {base.get('coverage')} | diagnostic |")
    for c in cycles:
        L.append(f"| {c['cycle']} | {c['codes']} | {c.get('kappa')} | "
                 f"{c.get('coverage')} | {c.get('passed')} |")
    L.append("")

    L += ["## Corpora", "",
          "Three task-disjoint corpora drawn from one pool. Disjointness is asserted "
          "in code, not assumed: a taxonomy is never certified on the traces it was "
          "induced from.", "",
          "| corpus | traces | tasks | failing | role |", "|---|---|---|---|---|"]
    roles = {"generation": "induced the draft vocabulary",
             "refinement": "re-judged every cycle; drives the edits",
             "gate": "identical every cycle; measures agreement only"}
    for k in ("generation", "refinement", "gate"):
        d = manifest.get(k, {})
        L.append(f"| {k} | {d.get('traces')} | {d.get('tasks')} | "
                 f"{d.get('failing')} | {roles[k]} |")
    L.append("")

    spent = sum(len(v) for v in manifest.get("task_ids", {}).values())
    L += ["## Tasks consumed", "",
          f"{spent} tasks were spent building this taxonomy; their ids are in "
          "`split_manifest.json`. A later measurement run that reuses them is no "
          "longer reading a vocabulary built on disjoint evidence. Draw fresh "
          "tasks, or record the overlap.", ""]

    L += ["## What is not here", "",
          "No support counts and no support-based removal. A code that did not fire "
          "on these corpora has not been shown not to occur, and this taxonomy will "
          "be applied to a different task set than any corpus above. See "
          "`PIPELINE.md`.", ""]

    L += ["## Provenance", "",
          f"- pipeline: `adamast` {prov.get('adamast_version', '?')} @ "
          f"`{str(prov.get('source_commit', '?'))[:12]}`, vendored at `pipeline/` "
          f"with local changes (`pipeline/CHANGES.md`)",
          f"- model: {state.get('settings', {}).get('model', 'not recorded in this run')}",
          f"- full record: `provenance.json`", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True, help="pipeline --out directory")
    ap.add_argument("--benchmark", help="defaults to the run's recorded benchmark")
    ap.add_argument("--settings-json", type=Path,
                    help="settings for a run that predates settings capture; "
                         "recorded as reconstructed, not observed")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    final = a.run / "taxonomy_final.json"
    state_f = a.run / "pipeline_state.json"
    man_f = a.run / "split_manifest.json"
    for f in (final, state_f, man_f):
        if not f.exists():
            raise SystemExit(f"missing {f} — has the run finished?")

    tax = json.loads(final.read_text())
    state = json.loads(state_f.read_text())
    manifest = json.loads(man_f.read_text())
    if a.settings_json:
        if state.get("settings"):
            raise SystemExit("run already recorded its own settings; refusing to "
                             "override an observed record with a reconstructed one")
        s = json.loads(a.settings_json.read_text())
        s["_source"] = ("reconstructed from the launch command; this run predates "
                        "in-run settings capture")
        state["settings"] = s
    bench = a.benchmark or state.get("benchmark")
    if not bench:
        raise SystemExit("no benchmark recorded; pass --benchmark")

    tax_dir = REPO / "benchmarks" / bench / "taxonomies"
    if not tax_dir.parent.exists():
        raise SystemExit(f"unknown benchmark: {tax_dir.parent} does not exist")
    tax_dir.mkdir(parents=True, exist_ok=True)
    tid = next_id(tax_dir)
    dest = tax_dir / tid
    if dest.exists():                       # belt and braces: never overwrite
        raise SystemExit(f"{dest} already exists; refusing to overwrite")

    state["certification_scope"] = certification_scope(a.run, tax)
    prov_pipe = pipeline_commit()
    provenance = {
        "id": tid,
        "kind": "taxonomy",
        "benchmark": bench,
        "certified": bool(tax.get("certified")),
        "derives_from": [f"pipeline run: {a.run}"],
        "generated_by": {
            "procedure": "PIPELINE.md",
            "orchestrator": "pipeline/taxonomy/run.py",
            "pipeline": prov_pipe,
            "cycles_run": len(state.get("cycles", [])),
            "cycle_results": state.get("cycles", []),
            "generation": state.get("generation", {}),
            "minutes": state.get("minutes"),
            "settings": state.get("settings", {}),
        },
        "baseline": state.get("baseline", {}),
        "certification_scope": state.get("certification_scope", {}),
        "corpora": {k: manifest.get(k, {}) for k in
                    ("generation", "refinement", "gate")},
        "tasks_consumed": manifest.get("task_ids", {}),
        "not_applied": [
            "support measurement",
            "removal by support",
            "coverage quotas",
        ],
        "counts": {
            "codes": len(tax["codes"]),
            **{f"category_{c.lower()}": n for c, n in
               Counter(str(x.get("category", "?")).upper()[:1]
                       for x in tax["codes"]).items()},
        },
        "outputs": ["taxonomy.json", "split_manifest.json", "pipeline_state.json"],
    }
    readme = render_readme(tid, bench, tax, state, manifest, prov_pipe)

    if a.dry_run:
        print(f"would create {dest}\n")
        print(readme)
        return

    dest.mkdir(parents=True)
    (dest / "taxonomy.json").write_text(json.dumps(tax, indent=2))
    (dest / "provenance.json").write_text(json.dumps(provenance, indent=2, default=str))
    (dest / "README.md").write_text(readme)
    shutil.copy2(man_f, dest / "split_manifest.json")
    shutil.copy2(state_f, dest / "pipeline_state.json")
    print(f"created {dest}")
    print(f"  {len(tax['codes'])} codes, certified={bool(tax.get('certified'))}")
    if not tax.get("certified"):
        print("  NOT CERTIFIED — the README records the failure; results using it "
              "must repeat that")


if __name__ == "__main__":
    main()
