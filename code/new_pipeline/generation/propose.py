"""Stage 9 (v3) -- propose codes for what the gap test could not place.

Reads gaps.json, takes every 'uncovered' and 'stretch' record, and asks the model
to group them by mechanism and propose one code per group of at least --min-size.
The proposals are then put through stage 6 exactly as generated codes would be.
Output is a list of validated candidates for a human decision, never an amended
taxonomy.

    python3 -m new_pipeline.generation.propose --taxonomy <taxonomy.json>
        --gaps <gaps.json> --corpus <pool> --structure <structure.json>
        --out <dir> [--model ...] [--min-size 4]

Requires a prompt document that defines the section (GENERATION_v3.md or later):
set FR_GENERATION_DOC or run through run.py --prompts.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from new_pipeline.llm import llm_call, log                          # noqa: E402
from new_pipeline.generation import contracts, prompts               # noqa: E402
from new_pipeline.generation.run import call_stage, require         # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--gaps", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, required=True, help="the pool the gap traces came from (for contracts)")
    ap.add_argument("--structure", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--min-size", type=int, default=4)
    ap.add_argument("--thinking", choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"], default="HIGH")
    ap.add_argument("--max-output", type=int, default=32768)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if prompts.PROPOSE is None:
        sys.exit(f"propose: {prompts.DOC.name} has no proposal section; use GENERATION_v3.md or later")

    t0 = time.time(); a.out.mkdir(parents=True, exist_ok=True)
    tax = json.load(open(a.taxonomy)); codes = tax["codes"] if isinstance(tax, dict) else tax
    gaps = json.load(open(a.gaps))
    recs = [r for r in gaps.get("records") or [] if r.get("verdict") in ("uncovered", "stretch")]
    log(f"propose: {len(recs)} uncovered/stretched findings from {a.gaps}; {len(codes)} codes")

    lines = []
    for i, r in enumerate(recs):
        near = "; ".join(f"{c.get('code')}@{c.get('fitness')}: {c.get('why','')}" for c in (r.get("codes") or [])[:2])
        lines.append(f"[{i}] trace {r.get('trace_id')} · {r.get('agent') or '?'} turn {r.get('turn') or '?'} · {r.get('verdict')}\n"
                     f"    problem: {r.get('problem')}\n"
                     f"    ruled out: {near or '(none named)'}")
    gaps_text = "\n".join(lines)
    tax_text = json.dumps([{k: c.get(k) for k in ("id", "column", "name", "definition", "when_to_use", "when_not_to_use", "consequence")} for c in codes], indent=1, ensure_ascii=False)
    structure = json.load(open(a.structure))
    by_cand = contracts.extract_all(a.corpus, structure)
    ctext = contracts.render_all(by_cand)

    p = prompts.build("propose", gaps=gaps_text, taxonomy=tax_text, contracts=ctext)
    p = p.replace("Minimum group size: 4.", f"Minimum group size: {a.min_size}.")
    if a.dry_run:
        print(p[:4000] + "\n...\n" + p[-1500:]); print(f"\ndry run: {len(p):,} chars, nothing spent"); return

    call, model = llm_call(a.model, temperature=0.0, retries=5, max_output=a.max_output, thinking=a.thinking)
    def ok(d):
        if not isinstance(d, dict) or not isinstance(d.get("proposals"), list):
            return "expected an object with a 'proposals' list (may be empty)"
        for x in d["proposals"]:
            for f in ("name", "column", "definition", "when_to_use", "when_not_to_use", "consequence", "evidence"):
                if not x.get(f): return f"proposal {x.get('name')!r} lacks {f}"
            if x["column"] not in ("general", "domain"): return f"proposal {x['name']!r}: bad column"
            if len(x["evidence"]) < a.min_size: return f"proposal {x['name']!r} has {len(x['evidence'])} evidence entries, under the minimum {a.min_size}"
        return None
    prop = call_stage("stage9_proposals", p, a.out, call, model)
    prop = require(prop, "stage9_proposals", ok, a.out, p, call, model, retries=2)
    props = prop.get("proposals") or []
    log(f"  {len(props)} proposal(s); not_proposed {len(prop.get('not_proposed') or [])}; too_few {len(prop.get('too_few') or [])}")
    if not props:
        (a.out / "proposals.json").write_text(json.dumps({"proposals": [], "raw": prop, "minutes": round((time.time()-t0)/60, 1)}, indent=2)); return

    # stage 6 on the proposals alone, with provisional ids
    for i, x in enumerate(props): x["id"] = f"PROP_{i+1:02d}"
    p6 = (prompts.build("stage6") + "\n\n## THE TAXONOMY\n" + json.dumps(props, indent=2)
          + "\n\n## WHAT EACH CODE CAME FROM\n" + json.dumps([{"from": ["gap-test proposal"], "to": x["id"], "operation": "propose",
                                                                 "why": f"grouped from {len(x['evidence'])} uncovered findings"} for x in props], indent=2)
          + "\n\n## THE MODES BEFORE CONSOLIDATION\n[]")
    def v_ok(d):
        return None if isinstance(d, dict) and isinstance(d.get("taxonomy"), list) and isinstance(d.get("checks"), list) else "expected 'checks' and 'taxonomy'"
    val = call_stage("stage9_validation", p6, a.out, call, model)
    val = require(val, "stage9_validation", v_ok, a.out, p6, call, model, retries=2)
    surviving = val.get("taxonomy") or []
    out = {"taxonomy_validated_against": str(a.taxonomy), "gaps": str(a.gaps), "prompt_document": prompts.DOC.name,
           "min_size": a.min_size, "findings_considered": len(recs),
           "proposals": props, "validation": val, "surviving": surviving,
           "not_proposed": prop.get("not_proposed") or [], "too_few": prop.get("too_few") or [],
           "note": "candidates for a decision; admitting one is a new taxonomy version beside the old",
           "minutes": round((time.time()-t0)/60, 1)}
    (a.out / "proposals.json").write_text(json.dumps(out, indent=2))
    log(f"  after stage 6: {len(surviving)} of {len(props)} survive -> {a.out}/proposals.json")
    for x in surviving: log(f"    {x.get('id')} [{x.get('column')}] {x.get('name')}")


if __name__ == "__main__":
    main()
