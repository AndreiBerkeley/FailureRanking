#!/usr/bin/env python3
"""Refinement round for a v2 taxonomy (GENERATION_v2.md, stage 7).

    python -m new_pipeline.refine --taxonomy <tax.json> --judge-out <judge run dir> \
        --corpus <refinement corpus dir> --structure <f> --out <dir> [--panel 4] [--round 1]

Evidence comes only from the judge's records on the refinement corpus: how
often each code fired, how often readers disagreed about it, the problems the
open reader filed under it and how well they fitted, and the problems no code
fitted. Three calls: a reviewer checklist per reviewer (7a), a consolidation
when the panel has more than one reviewer (7b), and the cross-code operations
(7c). Verdicts are derived from the checks, never asked for. Surviving and new
codes get fresh ids in the round's namespace; retired codes are kept aside.
Every prompt and raw response is written before it is parsed; a finished step
is skipped on re-run.
"""
from __future__ import annotations
import argparse, json, sys, time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from new_pipeline.llm import llm_call, log                    # noqa: E402
from new_pipeline.generation import prompts, contracts         # noqa: E402
from new_pipeline.generation.run import salvage                # noqa: E402

MAX_EXAMPLES, MAX_STRETCHED, MAX_UNMAPPED, MAX_PROBLEM = 3, 3, 60, 320
CHECKS = ("subject", "observable", "mechanism", "contract", "column", "adequacy", "overlap", "reason")
FIX = ("name", "definition", "when_to_use", "when_not_to_use", "column")
OK = {"subject": "candidate", "observable": "yes", "mechanism": "ok", "contract": "ok", "column": "ok", "adequacy": "matches", "overlap": "none"}
CODE_FIELDS = ("id", "column", "name", "definition", "when_to_use", "when_not_to_use")


def gather(judge_out: Path, code_ids: list[str]):
    per = {c: {"fired": 0, "disagreed": 0, "examples": [], "stretched": []} for c in code_ids}
    unmapped, n, silent = [], 0, 0
    for f in sorted((judge_out / "traces").glob("*.json")):
        t = json.loads(f.read_text())
        if t.get("status") != "judged": continue
        n += 1; codes = t.get("codes") or {}; silent += not codes
        ann = (t.get("panel") or {}).get("annotators") or []
        for c in code_ids:
            if codes.get(c): per[c]["fired"] += 1
            yes = sum(1 for a in ann if (a or {}).get(c, 0) > 0)
            if 0 < yes < len(ann): per[c]["disagreed"] += 1
        o = t.get("open") or {}
        for d in o.get("details") or []:
            best = (d.get("codes") or [{}])[0]; c = best.get("code")
            if c not in per: continue
            ex = {"trace": t["trace_id"], "agent": d.get("agent"), "turn": d.get("turn"), "fit": d.get("best_fitness"), "problem": (d.get("problem") or "")[:MAX_PROBLEM]}
            if d.get("verdict") == "covered":
                if len(per[c]["examples"]) < MAX_EXAMPLES: per[c]["examples"].append(ex)
            elif len(per[c]["stretched"]) < MAX_STRETCHED: per[c]["stretched"].append(ex)
        for u in o.get("unmapped") or []:
            unmapped.append({"trace": t["trace_id"], "agent": u.get("agent"), "turn": u.get("turn"), "best_fit": u.get("best_fitness"),
                             "nearest": [f"{x.get('code')}@{x.get('fitness')}" for x in (u.get("codes") or [])[:2]], "problem": (u.get("problem") or "")[:MAX_PROBLEM]})
    return per, unmapped, n, silent


def render_taxonomy(codes):
    return json.dumps([{k: c.get(k) for k in CODE_FIELDS} for c in codes], indent=1, ensure_ascii=False)


def render_evidence(codes, per, n, silent):
    out = [f"{n} traces judged on the refinement corpus; {silent} had no code at all.\n"]
    for c in codes:
        e = per[c["id"]]
        out.append(f"### {c['id']} {c['name']} [{c['column']}]\nfired on {e['fired']} of {n} traces; readers disagreed on {e['disagreed']} traces")
        if e["examples"]:
            out.append("problems the open reader filed here at a good fit:")
            out += [f"- ({x['agent']}, turn {x['turn']}, fit {x['fit']}) {x['problem']}" for x in e["examples"]]
        if e["stretched"]:
            out.append("problems filed here at a POOR fit (stretched):")
            out += [f"- ({x['agent']}, turn {x['turn']}, fit {x['fit']}) {x['problem']}" for x in e["stretched"]]
        out.append("")
    return "\n".join(out)


def render_unmapped(unmapped):
    if not unmapped: return "None."
    rows = [f"- [{u['trace'][:8]} {u['agent']} turn {u['turn']}; nearest {', '.join(u['nearest']) or 'none'}] {u['problem']}" for u in unmapped[:MAX_UNMAPPED]]
    more = f"\n... and {len(unmapped) - MAX_UNMAPPED} more" if len(unmapped) > MAX_UNMAPPED else ""
    return f"{len(unmapped)} problems fitted no code well.\n" + "\n".join(rows) + more


def ask_json(name, prompt, out: Path, call, model, retries=2, expect_checks=None):
    """Save prompt, call, save raw, parse; re-ask when the checklist omits codes."""
    (out / f"{name}.prompt.txt").write_text(prompt); jf = out / f"{name}.json"
    if jf.exists(): return json.loads(jf.read_text())
    p = prompt
    for k in range(retries + 1):
        raw = call(p, model)
        if raw is None: raise SystemExit(f"{name}: no response")
        (out / f"{name}.raw{'' if k == 0 else k}.txt").write_text(raw)
        d, note = salvage(raw)
        if note: log(f"  {name}: [!] {note}")
        if d is None: log(f"  {name}: unparseable, re-asking ({k+1}/{retries})"); continue
        if expect_checks:
            got = {x.get("code") for x in (d.get("checks") or []) if isinstance(x, dict)}
            missing = [c for c in expect_checks if c not in got]
            if missing and k < retries:
                log(f"  {name}: {len(missing)} codes missing from the checklist, re-asking"); p = prompt + f"\n\nYour previous answer omitted entries for: {missing}. Return the complete checklist, one entry per code."; continue
            if missing: log(f"  {name}: [!] still missing {missing}; treated as keep")
        jf.write_text(json.dumps(d, indent=2)); return d
    raise SystemExit(f"{name}: no usable response after {retries} re-asks; see {out}")


def derive(x):
    if x.get("subject") == "environment" or x.get("observable") == "no": return "retire"
    if x.get("adequacy") == "covers_two": return "split"
    if any(x.get(f) not in (None, "", v) for f, v in OK.items() if f != "overlap"): return "edit"
    return "keep"


def apply_operations(codes, checklist, ops, round_no):
    """Pure: (codes, consolidated checklist by id, ops) -> (new codes, retired, provenance, report)."""
    active = {c["id"]: dict(c) for c in codes}; order = [c["id"] for c in codes]
    retired, prov, applied = [], [], Counter()
    verdict = {cid: derive(checklist.get(cid, {})) for cid in order}
    for cid in order:
        if verdict[cid] == "retire":
            x = checklist[cid]; why = "environment" if x.get("subject") == "environment" else "unobservable"
            retired.append({**active.pop(cid), "retired_by": "checklist", "reason": f"[{why}] {x.get('reason', '')}"}); applied["retire"] += 1
    new_codes = []
    for cid in order:
        if cid not in active: continue
        c = active[cid]; x = checklist.get(cid, {})
        if verdict[cid] == "edit":
            for f in FIX:
                if f == "column":
                    if x.get("column") in ("general", "domain"): c["column"] = x["column"]   # "ok" means unchanged
                elif x.get(f): c[f] = x[f]
            applied["edit"] += 1
        new_codes.append((c, "edit" if verdict[cid] == "edit" else "keep", [cid], x.get("reason", "")))
    for mg in (ops.get("merge") or []):
        srcs = [s for s in (mg.get("codes") or []) if s in active]
        if len(srcs) < 2 or not mg.get("name"): continue
        col = mg.get("column") if mg.get("column") in ("general", "domain") else active[srcs[0]]["column"]
        new = {"column": col, **{f: mg.get(f, "") for f in ("name", "definition", "when_to_use", "when_not_to_use")}, "evidence": sum((active[s].get("evidence") or [] for s in srcs), [])}
        new_codes = [t for t in new_codes if t[0].get("id") not in srcs]
        for s in srcs: retired.append({**active.pop(s), "retired_by": "merge", "reason": mg.get("reason", "")})
        new_codes.append((new, "merge", srcs, mg.get("reason", ""))); applied["merge"] += 1
    for sp in (ops.get("split") or []):
        pid = sp.get("code"); kids = sp.get("into") or []
        if pid not in active or len(kids) < 2: continue
        parent = active.pop(pid); new_codes = [t for t in new_codes if t[0].get("id") != pid]
        for k in kids:
            new_codes.append(({"column": k.get("column") if k.get("column") in ("general", "domain") else parent["column"], **{f: k.get(f, "") for f in ("name", "definition", "when_to_use", "when_not_to_use")}, "evidence": []}, "split", [pid], sp.get("reason", "")))
        retired.append({**parent, "retired_by": "split", "reason": sp.get("reason", "")}); applied["split"] += 1
    for ad in (ops.get("add") or []):
        if ad.get("column") in ("general", "domain") and ad.get("name"):
            new_codes.append(({"column": ad["column"], **{f: ad.get(f, "") for f in ("name", "definition", "when_to_use", "when_not_to_use")}, "evidence": [], "evidence_trace_ids": ad.get("evidence_trace_ids") or []}, "add", [], ad.get("reason", ""))); applied["add"] += 1
    final = []
    for i, (c, op, src, why) in enumerate(new_codes, 1):
        nid = f"R{round_no}_{i:03d}"; c = {k: v for k, v in c.items() if k != "id"}
        final.append({"id": nid, **c}); prov.append({"from": src, "to": nid, "operation": op, "why": why})
    return final, retired, prov, {"verdicts": dict(Counter(verdict.values())), "applied": dict(applied), "codes_before": len(codes), "codes_after": len(final)}


def run(taxonomy: Path, judge_out: Path, corpus: Path, structure: Path, out: Path, model: str, panel: int = 4, temperature: float = 0.0,
        round_no: int = 1, dry_run: bool = False) -> Path:
    out.mkdir(parents=True, exist_ok=True); final_f = out / "taxonomy_refined.json"
    if final_f.exists(): log(f"refine: already done -> {final_f}"); return final_f
    tax = json.loads(taxonomy.read_text()); codes = tax["codes"]; ids = [c["id"] for c in codes]
    st = json.loads(structure.read_text())
    ctext = contracts.render_all(contracts.extract_all(corpus, st))
    per, unmapped, n, silent = gather(judge_out, ids)
    (out / "evidence.json").write_text(json.dumps({"per_code": per, "unmapped": unmapped, "traces": n, "silent": silent}, indent=1))
    ttext, etext = render_taxonomy(codes), render_evidence(codes, per, n, silent)
    p7a = prompts.build("stage7a", contracts=ctext, taxonomy=ttext, evidence=etext)
    (out / "stage7a.prompt.txt").write_text(p7a)
    log(f"refine round {round_no}: {len(ids)} codes, {n} judged traces, {len(unmapped)} unfitted problems, panel {panel}")
    if dry_run:
        log(f"  dry run: 7a prompt {len(p7a):,} chars written to {out}; no calls"); return out / "stage7a.prompt.txt"
    call, mid = llm_call(model, temperature=temperature); call0, _ = llm_call(model, temperature=0.0)
    reviewers = []
    for i in range(1, panel + 1):
        d = ask_json(f"reviewer_{i}", p7a, out, call, mid, expect_checks=ids)
        reviewers.append({x["code"]: x for x in (d.get("checks") or []) if isinstance(x, dict) and x.get("code") in ids})
        log(f"  reviewer {i}/{panel}: {len(reviewers[-1])}/{len(ids)} codes")
    if len(reviewers) > 1:
        split = {c: {f: dict(Counter(r[c].get(f) for r in reviewers if c in r and r[c].get(f))) for f in CHECKS if f != "reason"} for c in ids}
        split = {c: {f: v for f, v in s.items() if len(v) > 1} for c, s in split.items()}; split = {c: s for c, s in split.items() if s}
        (out / "panel_agreement.json").write_text(json.dumps({"reviewers": len(reviewers), "temperature": temperature, "split": split}, indent=1))
        log(f"  panel: {len(ids) - len(split)}/{len(ids)} codes unanimous, {len(split)} split")
        ptext = json.dumps([{"reviewer": i, "checks": list(r.values())} for i, r in enumerate(reviewers, 1)], indent=1, ensure_ascii=False)
        d = ask_json("consolidation", prompts.build("stage7b", taxonomy=ttext, panel=ptext), out, call0, mid, expect_checks=ids)
        checklist = {x["code"]: x for x in (d.get("checks") or []) if isinstance(x, dict) and x.get("code") in ids}
        for c in ids:  # majority fallback for anything the consolidator dropped
            if c not in checklist:
                base = {}
                for f in CHECKS + FIX:
                    votes = Counter(r[c].get(f) for r in reviewers if c in r and r[c].get(f))
                    if votes: base[f] = votes.most_common(1)[0][0]
                checklist[c] = {"code": c, **base}
    else:
        checklist = reviewers[0]
    for c in ids: checklist.setdefault(c, {"code": c}); checklist[c]["verdict"] = derive(checklist[c])
    (out / "checklist.json").write_text(json.dumps(checklist, indent=1))
    log(f"  verdicts: {dict(Counter(x['verdict'] for x in checklist.values()))}")
    ktext = "\n".join(f"{c}: verdict={checklist[c]['verdict']} " + " ".join(f"{f}={checklist[c].get(f)}" for f in CHECKS if f != "reason") + f" :: {(checklist[c].get('reason') or '')[:160]}" for c in ids)
    ops = ask_json("operations", prompts.build("stage7c", contracts=ctext, taxonomy=ttext, checklist=ktext, unmapped=render_unmapped(unmapped)), out, call0, mid)
    ops = ops if isinstance(ops, dict) else {}
    new, retired, prov, report = apply_operations(codes, checklist, ops, round_no)
    refined = {"benchmark": tax.get("benchmark"), "framework": "v2", "produced_by": f"new_pipeline.refine (round {round_no})",
               "derives_from": {"taxonomy": str(taxonomy), "judge_out": str(judge_out), "corpus": str(corpus)},
               "codes": new, "provenance": prov, "retired": retired, "checklist": checklist, "counts": report, "model": model, "panel": panel}
    final_f.write_text(json.dumps(refined, indent=2, ensure_ascii=False))
    (out / "refine_report.json").write_text(json.dumps(report, indent=1))
    log(f"refine: {report['codes_before']} -> {report['codes_after']} codes; {report['applied']}")
    return final_f


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taxonomy", type=Path, required=True); ap.add_argument("--judge-out", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, required=True); ap.add_argument("--structure", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True); ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--panel", type=int, default=4); ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--round", type=int, default=1); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    run(a.taxonomy, a.judge_out, a.corpus, a.structure, a.out, a.model, a.panel, a.temperature, a.round, a.dry_run)


if __name__ == "__main__":
    main()
