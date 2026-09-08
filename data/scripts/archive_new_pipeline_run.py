#!/usr/bin/env python3
"""Archive a finished new_pipeline run as a numbered taxonomy artifact plus its run record.

    python3 data/scripts/archive_new_pipeline_run.py --benchmark ifbench --run runs/new_pipeline/ifbench/run-1 --taxonomy tax-1

Writes data/<b>/taxonomies/<tax-N>/{taxonomy.json, README.md, provenance.json} and copies the
run directory (prompts, raw model outputs, judge records, gates, refinement, follow-ups; the
corpus trace copies are replaced by their id lists, since the traces are already captures) to
data/<b>/taxonomies/runs/<run-name>/ with its own provenance. Refuses to overwrite either.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TODAY = datetime.date.today().isoformat()
CORPORA = ("corpus_generation", "corpus_refinement", "corpus_gate", "corpus_fresh")


def sha_f(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()


def instrument_fingerprint() -> str:
    h = hashlib.sha256()
    for p in sorted((REPO / "new_pipeline").rglob("*.py")) + [REPO / "GENERATION_v2.md"]:
        if "__pycache__" in p.parts: continue
        h.update(str(p.relative_to(REPO)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True); ap.add_argument("--run", type=Path, required=True); ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--run-name", default=None, help="name under taxonomies/runs/ (default new_pipeline-<run dir name>)")
    a = ap.parse_args(); b = a.benchmark; run = a.run.resolve()
    D = REPO / "data" / b / "taxonomies"; tax_dir = D / a.taxonomy; run_name = a.run_name or f"new_pipeline-{run.name}"; run_dst = D / "runs" / run_name
    for d in (tax_dir, run_dst):
        if d.exists(): raise SystemExit(f"{d} exists; artifacts are append-only, pick the next number")
    state = json.loads((run / "state.json").read_text()); assert state.get("status") == "done", f"run status is {state.get('status')!r}, not done"
    final = json.loads((run / "taxonomy_final.json").read_text()); codes = final["codes"]
    split = json.loads((run / "split_manifest.json").read_text())
    pool = Path(state["settings"]["pool"]); pm = json.loads((REPO / pool / "pool_manifest.json").read_text())

    # --- run record: everything except the corpus trace copies, which become id lists
    run_dst.mkdir(parents=True)
    ids = {}
    for item in run.iterdir():
        if item.name in CORPORA:
            ids[item.name] = sorted(p.stem for p in item.glob("*.json")); continue
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, run_dst / item.name)
    (run_dst / "corpus_trace_ids.json").write_text(json.dumps(ids, indent=1))
    b_gate = state.get("baseline_gate") or {}; rounds = state.get("rounds") or []; last = rounds[-1]["gate"] if rounds else {}
    gates = {"baseline": {k: b_gate.get(k) for k in ("kappa_pooled_exercised_codes", "coverage", "traces", "passed", "codes")},
             **{f"round_{r['round']}": {k: r["gate"].get(k) for k in ("kappa_pooled_exercised_codes", "coverage", "traces", "passed", "codes")} for r in rounds}}
    run_prov = {"id": f"taxonomies/runs/{run_name}", "kind": "taxonomy generation run", "benchmark": b, "created": TODAY,
                "instrument": {"name": "new_pipeline (v2 generation, refinement round, interannotation gate, follow-ups)", "module": "new_pipeline", "design": "GENERATION_v2.md",
                               "source_fingerprint_sha256": instrument_fingerprint()},
                "settings": state["settings"], "corpora": state.get("corpora"), "split_manifest": {k: v for k, v in split.items() if k != "task_ids"},
                "gates": gates, "followups": state.get("followups"), "rounds": [{"round": r["round"], "refine": r.get("refine")} for r in rounds],
                "derives_from": [str(pool), f"data/{b}/program/structure.json"] + [f"data/{b}/traces/{c}" for c in pm["captures"]],
                "pool_export": pm, "original_location": str(run.relative_to(REPO)), "notes": [
                    "corpus_* directories replaced by corpus_trace_ids.json; the traces are the captures listed in derives_from",
                    "gate 'traces' counts judged traces; the difference to 60 is calls that exhausted their retries (rate limits), recorded as failed in the judge records"]}
    (run_dst / "provenance.json").write_text(json.dumps(run_prov, indent=2))

    # --- the taxonomy artifact
    tax_dir.mkdir(parents=True); shutil.copy2(run / "taxonomy_final.json", tax_dir / "taxonomy.json")
    cols = {"general": sum(1 for c in codes if c["column"] == "general"), "domain": sum(1 for c in codes if c["column"] == "domain")}
    rr = rounds[0]["refine"] if rounds else {}
    def g(x, k): v = x.get(k); return "—" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))
    rows = "\n".join(f"| `{c['id']}` | {c['column']} | {c['name']} | {str(c.get('definition', '')).replace('|', '/')[:220]} |" for c in codes)
    gate_rows = "\n".join(f"| {name} | {g(x, 'codes')} | {g(x, 'kappa_pooled_exercised_codes')} | {g(x, 'coverage')} | {g(x, 'traces')} | {'pass' if x.get('passed') else 'fail'} |" for name, x in gates.items())
    fu = (state.get("followups") or {}).get("gaps") or {}; gr = (state.get("followups") or {}).get("granularity") or {}
    readme = f"""# {a.taxonomy} — {len(codes)} failure modes for the {b} program

Generated on {TODAY} by `new_pipeline` from the `pools-1` taxonomy pool: {cols['general']} general
and {cols['domain']} domain codes. The draft came from stages 1–6 of `GENERATION_v2.md` on
{split['generation']['traces']} traces over {split['generation']['tasks']} tasks; one refinement round
rewrote it against the judge's reading of {split['refinement']['traces']} traces on {split['refinement']['tasks']} other tasks;
the interannotation gate measured draft and result on {split['gate']['traces']} traces of {split['gate']['tasks']} further tasks
with four readers and the open reader; the gap test read {fu.get('fresh_traces', '—')} fresh traces. No outcome
was in view at any stage; outcomes were used only to compose the corpora.

Refinement verdicts: {json.dumps(rr.get('verdicts') or {})}. Granularity: {json.dumps({k: gr.get(k) for k in ('examined', 'left_alone') if k in gr})}.
Gap test: {fu.get('findings', '—')} findings, verdicts {json.dumps(fu.get('verdicts') or {})}, fitness {json.dumps(fu.get('fitness') or {})}.

| gate | codes | pooled kappa | coverage | traces judged | result |
|---|---:|---:|---:|---:|---|
{gate_rows}

The full run record, with every prompt, raw model output, judge record and gate file, is in
`../runs/{run_name}/`. Ids are the `SP_` namespace assigned when the granularity splits were applied,
with the refinement round's `R1_` ids and the draft's ids recorded in `taxonomy.json` provenance.

| id | column | name | definition |
|---|---|---|---|
{rows}
"""
    (tax_dir / "README.md").write_text(readme)
    prov = {"id": a.taxonomy, "kind": "taxonomy", "benchmark": b, "created": TODAY, "produced_by": "new_pipeline.run (generation -> refinement round -> gate -> gap test -> granularity -> apply_splits)",
            "instrument": run_prov["instrument"], "structure": f"data/{b}/program/structure.json",
            "derives_from": [f"data/{b}/taxonomies/runs/{run_name}"] + run_prov["derives_from"],
            "counts": {"codes": len(codes), **cols, "draft_codes": gates["baseline"].get("codes"), "after_round_1": gates.get("round_1", {}).get("codes")},
            "gates": gates, "checks": {"copied_verbatim": sha_f(tax_dir / "taxonomy.json") == sha_f(run / "taxonomy_final.json"), "run_status_done": True}}
    (tax_dir / "provenance.json").write_text(json.dumps(prov, indent=2))
    print(f"{b} {a.taxonomy}: {len(codes)} codes; run record at {run_dst.relative_to(REPO)}")


if __name__ == "__main__":
    main()
