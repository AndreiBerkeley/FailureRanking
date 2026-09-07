#!/usr/bin/env python3
"""The v2 taxonomy pipeline, end to end: generation, refinement, certification,
follow-up checks. One pool of traces in, one certified taxonomy out.

    python -m new_pipeline.run --benchmark hover --pool <dir> --structure <f> --out <dir> \
        [--n-generation 100] [--rounds 1] [--model gemini-3.6-flash] [--dry-run]

Steps, each resumable (a finished artifact is not redone):
  0  split the pool into three task-disjoint corpora: generation (N traces),
     refinement (about N/2), gate (60 over at least 30 tasks); plus the fresh
     remainder for the gap test
  1  generation, stages 1-6 (GENERATION_v2.md)              -> draft taxonomy
  2  baseline gate: measure the draft before refinement touches it (diagnostic)
  3  for each round (default 1): judge the refinement corpus, refine (stage 7),
     gate (stage 8); stop on the first pass
  4  follow-up checks on fresh traces: gap test, granularity split -> final taxonomy
Nothing in the gate corpus ever reaches the refiner. No outcome reaches any model.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from new_pipeline import corpora, goldfree                    # noqa: E402
from new_pipeline.llm import log                               # noqa: E402
from new_pipeline import gate as G, refine as R                # noqa: E402

PY_ = sys.executable


def sh(cmd, dry):
    log("  $ " + " ".join(str(c) for c in cmd))
    if not dry: subprocess.run([str(c) for c in cmd], check=True, cwd=str(REPO))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True); ap.add_argument("--pool", type=Path, required=True, help="directory of judge-view traces (see export_pool.py)")
    ap.add_argument("--structure", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--outcomes", type=Path, default=None, help="trace_id -> score sidecar for stratification only; default <pool>/outcomes.json if present")
    ap.add_argument("--n-generation", type=int, default=100); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="gemini-3.6-flash", help="generator, refiner, and judge panel; openrouter/<vendor>/<model> routes through OpenRouter")
    ap.add_argument("--open-model", default=None, help="the judge's open reader (default: the judge's own default)")
    ap.add_argument("--rounds", type=int, default=1); ap.add_argument("--refine-panel", type=int, default=4); ap.add_argument("--panel-temperature", type=float, default=0.0)
    ap.add_argument("--gate-readers", type=int, default=4); ap.add_argument("--kappa-target", type=float, default=0.75); ap.add_argument("--coverage-floor", type=float, default=0.70)
    ap.add_argument("--no-baseline-gate", action="store_true"); ap.add_argument("--skip-followups", action="store_true")
    ap.add_argument("--gap-tasks", type=int, default=40); ap.add_argument("--dry-run", action="store_true", help="split the corpora and dry-run generation; print every later command")
    a = ap.parse_args(); out = a.out; out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    state_f = out / "state.json"; state = json.loads(state_f.read_text()) if state_f.exists() else {}
    state.update({"benchmark": a.benchmark, "settings": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items()}, "status": "running"})
    def save(): state_f.write_text(json.dumps(state, indent=2))

    # 0. corpora
    log(f"new_pipeline: {a.benchmark}, N={a.n_generation}, rounds={a.rounds}, model={a.model}")
    outcomes = a.outcomes or ((a.pool / "outcomes.json") if (a.pool / "outcomes.json").exists() else None)
    split = corpora.plan(a.pool, a.n_generation, seed=a.seed, outcomes=outcomes)
    dirs = corpora.materialise(split, out)
    used = set().union(*(set(split.manifest["task_ids"][k]) for k in ("generation", "refinement", "gate")))
    fresh = out / "corpus_fresh"; fresh.mkdir(exist_ok=True)
    nf = 0
    for p in sorted(a.pool.glob("*.json")):
        if p.name in ("outcomes.json", "pool_manifest.json"): continue
        md = json.loads(p.read_text()).get("metadata") or {}
        if md.get("task_source_id") and md["task_source_id"] not in used:
            dst = fresh / p.name
            if not dst.exists(): goldfree.strip_file(p, dst)
            nf += 1
    state["corpora"] = {k: len(v) for k, v in split.manifest["task_ids"].items()} | {"fresh_traces": nf}
    log(f"  corpora: " + ", ".join(f"{k} {len(getattr(split, k))} traces / {len(split.manifest['task_ids'][k])} tasks" for k in ("generation", "refinement", "gate")) + f"; fresh remainder {nf} traces"); save()

    # 1. generation
    gen = out / "generation"; gen.mkdir(exist_ok=True)
    ids_f = gen / "corpus_trace_ids.txt"; ids_f.write_text("\n".join(sorted(p.stem for p in dirs["generation"].glob("*.json"))) + "\n")
    draft = gen / "taxonomy_v2.json"
    cmd = [PY_, "-m", "new_pipeline.generation.run", "--benchmark", a.benchmark, "--corpus", dirs["generation"], "--structure", a.structure, "--out", gen, "--model", a.model, "--trace-ids", ids_f]
    if not draft.exists():
        log("step 1: generation"); sh(cmd + (["--dry-run"] if a.dry_run else []), False)
    else: log("step 1: generation already done")
    if a.dry_run:
        log("dry run: generation planned above; the remaining steps would run these commands:")
        log(f"  baseline gate:  new_pipeline.gate --taxonomy {draft} --corpus {dirs['gate']} --readers {a.gate_readers}")
        log(f"  round 1 judge:  new_pipeline.judge.run --taxonomy {draft} --traces {dirs['refinement']} --annotators 2 --threshold 2")
        log(f"  round 1 refine: new_pipeline.refine --taxonomy {draft} --judge-out {out}/round_1/judge --corpus {dirs['refinement']} --panel {a.refine_panel}")
        log(f"  round 1 gate:   new_pipeline.gate --taxonomy {out}/round_1/refine/taxonomy_refined.json --corpus {dirs['gate']} --readers {a.gate_readers}")
        log(f"  follow-ups:     new_pipeline.generation.gaps --corpus {fresh} ; granularity ; apply_splits -> {out}/taxonomy_final.json")
        state["status"] = "dry-run"; save(); return
    current = draft; state["draft"] = str(draft); save()

    # 2. baseline gate
    if not a.no_baseline_gate:
        log("step 2: baseline gate on the draft")
        state["baseline_gate"] = {k: v for k, v in G.run(draft, dirs["gate"], a.structure, out / "baseline_gate", a.model, a.gate_readers, a.kappa_target, a.coverage_floor, a.open_model).items() if k != "kappa_per_code"}; save()

    # 3. rounds
    state.setdefault("rounds", [])
    for r in range(1, a.rounds + 1):
        rd = out / f"round_{r}"; rd.mkdir(exist_ok=True); log(f"step 3: round {r}")
        jd = rd / "judge"
        if not (jd / "summary.json").exists():
            sh([PY_, "-m", "new_pipeline.judge.run", "--taxonomy", current, "--traces", dirs["refinement"], "--out", jd, "--structure", a.structure, "--model", a.model,
                "--annotators", "2", "--threshold", "2", "--traces-per-call", "5", "--thinking", "HIGH"] + (["--open-model", a.open_model] if a.open_model else []), False)
        refined = R.run(current, jd, dirs["refinement"], a.structure, rd / "refine", a.model, a.refine_panel, a.panel_temperature, r)
        g = G.run(refined, dirs["gate"], a.structure, rd / "gate", a.model, a.gate_readers, a.kappa_target, a.coverage_floor, a.open_model)
        rr = json.loads((rd / "refine" / "refine_report.json").read_text())
        state["rounds"] = [x for x in state["rounds"] if x.get("round") != r] + [{"round": r, "refine": rr, "gate": {k: v for k, v in g.items() if k != "kappa_per_code"}}]
        current = refined; save()
        if g.get("passed"): log(f"  round {r}: gate passed"); break
        log(f"  round {r}: gate not passed" + ("; next round" if r < a.rounds else "; no rounds left, shipping with the gate numbers"))
    state["refined"] = str(current); save()

    # 4. follow-ups
    final = out / "taxonomy_final.json"
    if a.skip_followups:
        final.write_text(current.read_text()); state["final"] = str(final); state["status"] = "done"; save(); log(f"done (follow-ups skipped) -> {final}"); return
    log("step 4: follow-up checks on fresh traces")
    gaps = out / "gaps"
    if not (gaps / "gaps.json").exists():
        sh([PY_, "-m", "new_pipeline.generation.gaps", "--benchmark", a.benchmark, "--taxonomy", current, "--corpus", fresh, "--structure", a.structure, "--exclude", gen, "--out", gaps, "--model", a.model, "--tasks", str(a.gap_tasks)], False)
    gran = out / "granularity"
    if not (gran / "granularity.json").exists():
        sh([PY_, "-m", "new_pipeline.generation.granularity", "--taxonomy", current, "--records", gaps / "gaps.json", "--out", gran, "--model", a.model], False)
    if not final.exists():
        sh([PY_, "-m", "new_pipeline.generation.apply_splits", "--taxonomy", current, "--granularity", gran / "granularity.json", "--out", final], False)
    gj = json.loads((gaps / "gaps.json").read_text()); grj = json.loads((gran / "granularity.json").read_text())
    state["followups"] = {"gaps": {k: gj.get(k) for k in ("fresh_traces", "findings", "verdicts", "fitness", "codes_never_matched_well")}, "granularity": {k: grj.get(k) for k in ("examined", "left_alone", "mode")}}
    state["final"] = str(final); state["status"] = "done"; state["minutes"] = round((time.time() - t0) / 60, 1); save()
    log(f"done -> {final}  ({state['minutes']} min)")


if __name__ == "__main__":
    main()
