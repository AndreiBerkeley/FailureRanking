#!/usr/bin/env python3
"""The v2 taxonomy pipeline, end to end: generation, refinement, certification,
follow-up checks. One pool of traces in, one certified taxonomy out.

    python -m new_pipeline.run --benchmark hover --pool <dir> --structure <f> --out <dir> \
        [--n-generation 100] [--rounds 1] [--model gemini-3.6-flash] [--dry-run]

Steps, each resumable (a finished artifact is not redone):
  0  split the pool into four task-disjoint corpora: generation (N traces),
     refinement (about N/2), gate (60 over at least 30 tasks), and the gap
     test's corpus (--gap-tasks tasks, --gap-per-task traces each, failing
     first). Failure-bearing tasks are shared among the four (corpora.py).
  1  generation, stages 1-6 (GENERATION_v2.md)              -> draft taxonomy
  2  baseline gate: measure the draft before refinement touches it (diagnostic)
  3  for each round (default 1): judge the refinement corpus, refine (stage 7),
     gate (stage 8); stop on the first pass
  4  follow-up checks on fresh traces: gap test, granularity split -> final taxonomy
Nothing in the gate corpus ever reaches the refiner. No outcome reaches any model.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path
# --prompts must take effect before new_pipeline.generation.prompts is imported (it
# parses the document at import) and is inherited by every stage subprocess.
if "--prompts" in sys.argv:
    os.environ["FR_GENERATION_DOC"] = sys.argv[sys.argv.index("--prompts") + 1]

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from new_pipeline import corpora, goldfree                    # noqa: E402
from new_pipeline.llm import log                               # noqa: E402
from new_pipeline import gate as G, refine as R                # noqa: E402

PY_ = sys.executable


def sh(cmd, dry):
    log("  $ " + " ".join(str(c) for c in cmd))
    if not dry: subprocess.run([str(c) for c in cmd], check=True, cwd=str(REPO))


def judged_or_die(judge_dir: Path, what: str):
    """A judge run in which every call failed (no credits, bad route, dead key) must stop the
    pipeline, not feed an empty evidence base to the refiner or a kappa of None to the gate."""
    sm = json.loads((judge_dir / "summary.json").read_text()) if (judge_dir / "summary.json").exists() else {}
    n = (sm.get("counts") or {}).get("judged")
    if not isinstance(n, int): n = len([f for f in (judge_dir / "traces").glob("*.json") if json.loads(f.read_text()).get("status") == "judged"])
    if not n:
        raise SystemExit(f"{what}: the judge read 0 traces (every call failed; see {judge_dir}/summary.json and the [!] lines above). "
                         f"Fix the cause (credits, key, route), remove {judge_dir.parent} and rerun the same command.")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True); ap.add_argument("--pool", type=Path, required=True, help="directory of judge-view traces (see export_pool.py)")
    ap.add_argument("--prompts", default="GENERATION_v2.md", help="which GENERATION_v*.md is the instrument; recorded in every artifact")
    ap.add_argument("--structure", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--outcomes", type=Path, default=None, help="trace_id -> score sidecar for stratification only; default <pool>/outcomes.json if present")
    ap.add_argument("--n-generation", type=int, default=100); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default="gemini-3.6-flash", help="generator and refiner; openrouter/<vendor>/<model> routes through OpenRouter")
    ap.add_argument("--judge-model", default=None, help="the judge's panel readers (default: --model)")
    ap.add_argument("--followup-model", default=None, help="gap test, mapping and splitter (default: --model)")
    ap.add_argument("--open-model", default=None, help="the judge's open reader (default: the judge's own default)")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--stop-on-pass", action="store_true", help="stop as soon as a gate passes; off by default, because stopping on the gate selects the round that best suits that corpus")
    ap.add_argument("--refine-panel-unused", type=int, default=0, help=argparse.SUPPRESS); ap.add_argument("--refine-panel", type=int, default=4); ap.add_argument("--panel-temperature", type=float, default=0.0)
    ap.add_argument("--gate-readers", type=int, default=4); ap.add_argument("--kappa-target", type=float, default=0.75); ap.add_argument("--coverage-floor", type=float, default=0.70)
    ap.add_argument("--no-baseline-gate", action="store_true"); ap.add_argument("--skip-followups", action="store_true")
    ap.add_argument("--work-ledger", action="store_true",
                    help="stage 2's work pass returns the per-step ledger rather than a count and a one-line account; "
                         "the schema is part of the cache key, so switching it does not reuse batches read the other way")
    ap.add_argument("--max-output", type=int, default=65536,
                    help="output-token cap for the generation stages; on OpenRouter the cap covers reasoning tokens too, and stage 3's "
                         "answer (every observation placed under a mode, quote included) was cut at 32768 on a 160-trace corpus")
    ap.add_argument("--gap-tasks", type=int, default=40); ap.add_argument("--gap-per-task", type=int, default=1, help="traces per gap task, failing first"); ap.add_argument("--dry-run", action="store_true", help="split the corpora and dry-run generation; print every later command")
    a = ap.parse_args(); out = a.out; out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    state_f = out / "state.json"; state = json.loads(state_f.read_text()) if state_f.exists() else {}
    state.update({"benchmark": a.benchmark, "settings": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items()}, "status": "running"})
    def save(): state_f.write_text(json.dumps(state, indent=2))

    # 0. corpora
    log(f"new_pipeline: {a.benchmark}, N={a.n_generation}, rounds={a.rounds}, model={a.model}")
    outcomes = a.outcomes or ((a.pool / "outcomes.json") if (a.pool / "outcomes.json").exists() else None)
    jm = a.judge_model or a.model; fm = a.followup_model or a.model
    split = corpora.plan(a.pool, a.n_generation, seed=a.seed, outcomes=outcomes, n_gap_tasks=a.gap_tasks, rounds=a.rounds)
    dirs = corpora.materialise(split, out)
    # The gap corpus: the dealt gap tasks, --gap-per-task traces each, failing
    # traces first (outcomes for stratification only, never shown). The gap test
    # reads it blind, so what is in it decides what it can find.
    fresh = out / "corpus_fresh"
    by_task = corpora._index(a.pool, corpora.load_outcomes(outcomes))
    nf = nff = 0; planned = []
    for t in split.manifest["task_ids"]["gap"]:
        picks = (by_task[t]["fail"] + by_task[t]["pass"])[:a.gap_per_task]
        nff += min(len(by_task[t]["fail"]), a.gap_per_task)
        planned += picks
    corpora._reset(fresh, {p.name for p in planned})       # exact to the plan, like the other corpora
    for p in planned:
        dst = fresh / p.name
        if not dst.exists(): goldfree.strip_file(p, dst)
        nf += 1
    state["corpora"] = {k: len(v) for k, v in split.manifest["task_ids"].items()} | {"fresh_traces": nf, "fresh_failing": nff, "spare_tasks": split.manifest["spare_tasks"]}
    log(f"  corpora: " + ", ".join(f"{k} {len(getattr(split, k))} traces / {len(split.manifest['task_ids'][k])} tasks ({split.manifest[k]['failing']} failing)" for k in ("generation", "refinement", "gate")) + f"; gap {nf} traces / {len(split.manifest['task_ids']['gap'])} tasks ({nff} failing); {split.manifest['spare_tasks']} tasks unused"); save()

    # 1. generation
    gen = out / "generation"; gen.mkdir(exist_ok=True)
    ids_f = gen / "corpus_trace_ids.txt"; ids_f.write_text("\n".join(sorted(p.stem for p in dirs["generation"].glob("*.json"))) + "\n")
    draft = gen / "taxonomy_v2.json"
    cmd = ([PY_, "-m", "new_pipeline.generation.run", "--benchmark", a.benchmark, "--corpus", dirs["generation"], "--structure", a.structure, "--out", gen, "--model", a.model, "--trace-ids", ids_f, "--max-output", str(a.max_output)]
           + (["--work-ledger"] if a.work_ledger else []))
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
        g0 = G.run(draft, dirs["gate"], a.structure, out / "baseline_gate", jm, a.gate_readers, a.kappa_target, a.coverage_floor, a.open_model)
        judged_or_die(out / "baseline_gate" / "judge", "baseline gate")
        state["baseline_gate"] = {k: v for k, v in g0.items() if k != "kappa_per_code"}; save()

    # 3. rounds
    state.setdefault("rounds", [])
    for r in range(1, a.rounds + 1):
        rd = out / f"round_{r}"; rd.mkdir(exist_ok=True); log(f"step 3: round {r}")
        jd = rd / "judge"
        if not (jd / "summary.json").exists():
            sh([PY_, "-m", "new_pipeline.judge.run", "--taxonomy", current, "--traces", dirs[f"refinement_{r}"], "--out", jd, "--structure", a.structure, "--model", jm,
                "--annotators", "2", "--threshold", "2", "--traces-per-call", "5", "--thinking", "HIGH"] + (["--open-model", a.open_model] if a.open_model else []), False)
        judged_or_die(jd, f"round {r} judge")
        refined = R.run(current, jd, dirs[f"refinement_{r}"], a.structure, rd / "refine", a.model, a.refine_panel, a.panel_temperature, r)
        g = G.run(refined, dirs["gate"], a.structure, rd / "gate", jm, a.gate_readers, a.kappa_target, a.coverage_floor, a.open_model)
        judged_or_die(rd / "gate" / "judge", f"round {r} gate")
        rr = json.loads((rd / "refine" / "refine_report.json").read_text())
        state["rounds"] = [x for x in state["rounds"] if x.get("round") != r] + [{"round": r, "refine": rr, "gate": {k: v for k, v in g.items() if k != "kappa_per_code"}}]
        current = refined; save()
        if g.get("passed") and a.stop_on_pass: log(f"  round {r}: gate passed; stopping (--stop-on-pass)"); break
        if g.get("passed"): log(f"  round {r}: gate passed; continuing, the round count is fixed in advance so the gate is not selected on")
        log(f"  round {r}: gate not passed" + ("; next round" if r < a.rounds else "; no rounds left, shipping with the gate numbers"))
    state["refined"] = str(current); save()

    # v3 rule, applied a second time on the gate's own reading: a code the open reader
    # corroborates under the threshold at the last gate is retired before the follow-ups.
    v3 = os.environ.get("FR_GENERATION_DOC", "GENERATION_v2.md") != "GENERATION_v2.md"
    last_gate = out / f"round_{a.rounds}" / "gate" / "gate.json"
    if v3 and last_gate.exists():
        gj0 = json.loads(last_gate.read_text()); weak = gj0.get("weakly_corroborated") or []
        if weak:
            tx = json.loads(Path(current).read_text())
            corr = gj0.get("corroboration_per_code") or {}
            tx["codes"] = [c for c in tx["codes"] if c["id"] not in weak]
            tx.setdefault("provenance", []).extend({"from": w, "to": None, "operation": "retire",
                "why": f"weakly corroborated at the final gate: open reader {corr.get(w, {}).get('corroborated')}/{corr.get(w, {}).get('fired')} (rule: share < 0.30)"} for w in weak)
            pruned = out / "taxonomy_pruned.json"; pruned.write_text(json.dumps(tx, indent=2))
            log(f"  corroboration rule at the final gate: retired {weak} -> {pruned}")
            current = pruned; state["pruned"] = {"retired": weak, "taxonomy": str(pruned)}; save()

    # 4. follow-ups
    final = out / "taxonomy_final.json"
    if a.skip_followups:
        final.write_text(current.read_text()); state["final"] = str(final); state["status"] = "done"; save(); log(f"done (follow-ups skipped) -> {final}"); return
    log("step 4: follow-up checks on fresh traces")
    gaps = out / "gaps"
    if not (gaps / "gaps.json").exists():
        sh([PY_, "-m", "new_pipeline.generation.gaps", "--benchmark", a.benchmark, "--taxonomy", current, "--corpus", fresh, "--structure", a.structure, "--exclude", gen, "--out", gaps, "--model", fm, "--tasks", str(a.gap_tasks), "--per-task", str(a.gap_per_task)], False)
    gran = out / "granularity"
    if not (gran / "granularity.json").exists():
        sh([PY_, "-m", "new_pipeline.generation.granularity", "--taxonomy", current, "--records", gaps / "gaps.json", "--out", gran, "--model", fm, "--min-findings", "4"], False)
    split_out = out / "taxonomy_before_proposals.json" if v3 else final
    if not split_out.exists():
        sh([PY_, "-m", "new_pipeline.generation.apply_splits", "--taxonomy", current, "--granularity", gran / "granularity.json", "--out", split_out], False)
    # v3: propose codes for every gap-test finding no code fits well (uncovered, stretched,
    # loose), validate them with stage 6, and ADMIT the survivors: the taxonomy that ships
    # covers what its own gap test found, with provenance saying so. No hand codes.
    prop = out / "proposals"
    if v3 and not (prop / "proposals.json").exists():
        sh([PY_, "-m", "new_pipeline.generation.propose", "--taxonomy", split_out, "--gaps", gaps / "gaps.json", "--corpus", fresh, "--structure", a.structure, "--out", prop, "--model", fm], False)
    if v3 and not final.exists():
        sh([PY_, "-m", "new_pipeline.generation.apply_proposals", "--taxonomy", split_out, "--proposals", prop / "proposals.json", "--out", final], False)
    gj = json.loads((gaps / "gaps.json").read_text()); grj = json.loads((gran / "granularity.json").read_text())
    state["followups"] = {"gaps": {k: gj.get(k) for k in ("fresh_traces", "findings", "verdicts", "fitness", "codes_never_matched_well")}, "granularity": {k: grj.get(k) for k in ("examined", "left_alone", "mode")}}
    if (prop / "proposals.json").exists():
        pj = json.loads((prop / "proposals.json").read_text())
        state["followups"]["proposals"] = {"proposed": len(pj.get("proposals") or []), "surviving_stage6": len(pj.get("surviving") or []), "too_few": len(pj.get("too_few") or [])}
        log(f"  proposals: {state['followups']['proposals']} -> {prop}/proposals.json (survivors admitted into {final.name})")
    state["prompt_document"] = os.environ.get("FR_GENERATION_DOC", "GENERATION_v2.md")
    state["final"] = str(final); state["status"] = "done"; state["minutes"] = round((time.time() - t0) / 60, 1); save()
    log(f"done -> {final}  ({state['minutes']} min)")


if __name__ == "__main__":
    main()
