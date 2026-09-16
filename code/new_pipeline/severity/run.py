"""Study 1 — general importance per failure mode.

Three raters, one call each, every code rated in one pass over a shared corpus.
The mapping judge never sees the result: it is written beside the taxonomy, never
into it.

  python3 -m new_pipeline.severity.run --taxonomy ... --mapping <pointjudge run>
      --traces <pool> --structure ... --out ... --raters m1 m2 m3 [--dry-run]
"""
from __future__ import annotations
import argparse, json, sys, time
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from new_pipeline import goldfree                                   # noqa: E402
from new_pipeline.llm import llm_call, log                          # noqa: E402
from new_pipeline.pointjudge import judge                           # noqa: E402
from new_pipeline.severity import render, prompts                   # noqa: E402


def build(a):
    tax = json.load(open(a.taxonomy))["codes"]
    codes = [c["id"] for c in tax]
    st = json.load(open(a.structure))
    agents = st["discovered_agents"]["agents"]
    arch = st["architecture"]
    program = (f"topology: {arch['topology']}\n{arch['topology_details']}\n"
               f"verification: {arch['verification_details']}")

    recs = sorted((json.loads(p.read_text()) for p in (a.mapping / "traces").glob("*.json")),
                  key=lambda r: r["trace_id"])
    recs = [r for r in recs if r.get("status") == "judged"]
    tnum = {r["trace_id"]: f"T{i+1:02d}" for i, r in enumerate(recs)}

    by_code = defaultdict(list)
    for r in recs:
        for q in r["points"]:
            for m in q.get("codes") or []:
                by_code[m].append((tnum[r["trace_id"]], q))
    # pointer list only: the full finding text lives at the head of each trace
    index_lines = []
    for c in codes:
        items = by_code.get(c, [])
        where = ", ".join(f"{t}·t{q['turn']}" for t, q in items) or "(no findings in this corpus)"
        index_lines.append(f"{c}  {len(items):>3} finding(s):  {where}")
    index = "\n".join(index_lines)

    seen = {}
    blocks = []
    for r in recs:
        raw = json.loads((a.traces / f"{r['trace_id']}.json").read_text())
        clean, _ = goldfree.strip(raw)
        txt, _ = judge.render_turns(clean, agents)
        body = render.condense(txt, seen)
        head = [f"FINDINGS ON THIS TRACE ({len(r['points'])}):"]
        for q in sorted(r["points"], key=lambda q: q["turn"]):
            cs = "/".join(q.get("codes") or ["none_fits"])
            ev = (q.get("evidence") or "").replace("\n", " ")[:160]
            head.append(f"  turn {q['turn']} {q.get('agent')} [{cs}]\n     evidence: {ev}\n"
                        f"     problem : {(q.get('problem') or '')[:220]}")
        blocks.append(f"\n\n################ {tnum[r['trace_id']]} ################\n" +
                      "\n".join(head) + "\n" + body)
    instructions = "\n\n".join(f"--- {ag} ---\n{txt}" for ag, txt in seen.items())
    taxonomy = "\n\n".join(
        f"{c['id']} ({c['column']}) {c['name']}\n  definition: {c['definition']}\n"
        f"  when to use: {c.get('when_to_use','')}\n  when not to use: {c.get('when_not_to_use','')}"
        for c in tax)
    prompt = prompts.PROMPT.format(program=program, instructions=instructions, taxonomy=taxonomy,
                                   index=index, n_traces=len(recs), traces="".join(blocks))
    valid_cites = {c: {t for t, _ in by_code.get(c, [])} for c in codes}
    counts = {c: len(by_code.get(c, [])) for c in codes}
    return prompt, codes, valid_cites, counts, tnum


def parse(text, codes, valid_cites):
    try:
        d = json.loads(text)
    except Exception:
        return None, "not JSON"
    rs = d.get("ratings")
    if not isinstance(rs, list):
        return None, "no ratings list"
    out, problems = {}, []
    for e in rs:
        c = e.get("code"); lv = str(e.get("level", "")).lower().strip()
        if c not in codes: problems.append(f"unknown code {c}"); continue
        if lv not in prompts.ORD: problems.append(f"{c}: bad level {lv!r}"); continue
        cited = [t for t in (e.get("cited") or []) if t in valid_cites[c]]
        if valid_cites[c] and not cited:
            problems.append(f"{c}: no valid citation (cited {e.get('cited')})")
        out[c] = {"level": lv, "cited": cited, "cited_raw": e.get("cited") or [],
                  "mechanism": e.get("mechanism", ""), "support": e.get("support", "")}
    missing = [c for c in codes if c not in out]
    if missing: problems.append(f"missing codes {missing}")
    return out, "; ".join(problems)


def wkappa(a, b, k=4):
    """Quadratic-weighted Cohen's kappa on two aligned ordinal lists."""
    n = len(a)
    if n == 0: return float("nan")
    O = [[0]*k for _ in range(k)]
    for x, y in zip(a, b): O[x][y] += 1
    ra = [sum(O[i]) for i in range(k)]; rb = [sum(O[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * O[i][j]; den += w * ra[i] * rb[j] / n
    return 1 - num / den if den else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--mapping", type=Path, required=True, help="pointjudge run dir over the corpus")
    ap.add_argument("--traces", type=Path, required=True, help="pool dir with the source traces")
    ap.add_argument("--structure", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--raters", nargs="+", required=True)
    ap.add_argument("--thinking", default="HIGH")
    ap.add_argument("--max-output", type=int, default=16384)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--retries", type=int, default=2, help="re-asks on a rejected answer")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    prompt, codes, valid_cites, counts, tnum = build(a)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "prompt.txt").write_text(prompt)
    (a.out / "trace_numbers.json").write_text(json.dumps(tnum, indent=2))
    log(f"severity: {len(codes)} codes | {len(tnum)} traces | prompt {len(prompt):,} chars "
        f"≈ {len(prompt)//4:,} tokens | raters {a.raters}")
    log("  findings per code: " + ", ".join(f"{c}:{counts[c]}" for c in codes))
    if a.dry_run:
        print("\n" + prompt[:6000] + "\n...\n" + prompt[-2500:]); print("\ndry run: nothing spent"); return

    results = {}
    for model in a.raters:
        call, mid = llm_call(model, temperature=0.0, retries=5, max_output=a.max_output,
                             thinking=a.thinking, timeout=a.timeout)
        prior = a.out / f"rater_{mid.replace('/','_')}.json"
        if prior.exists():
            pr = json.loads(prior.read_text())
            if pr.get("ratings") and not pr.get("problems"):
                log(f"  rater {mid}: accepted answer already on disk, not re-asked")
                results[mid] = pr; continue
        got = None
        for attempt in range(1, a.retries + 2):
            log(f"  rater {mid} attempt {attempt}")
            t0 = time.time()
            text = call(prompt, mid)
            if text is None:
                log(f"    no response"); continue
            parsed, problems = parse(text, codes, valid_cites)
            (a.out / f"rater_{mid.replace('/','_')}_raw_{attempt}.txt").write_text(text)
            if parsed and not problems:
                got = parsed; log(f"    ok ({time.time()-t0:.0f}s)"); break
            log(f"    rejected: {problems[:300]}")
            if parsed: got = parsed   # keep best-effort; problems recorded below
        results[mid] = {"ratings": got, "problems": problems if got else "no parse"}
        (a.out / f"rater_{mid.replace('/','_')}.json").write_text(json.dumps(results[mid], indent=2))

    raters = [m for m in results if results[m]["ratings"]]
    per_code = {}
    for c in codes:
        lv = {m: results[m]["ratings"][c]["level"] for m in raters if c in results[m]["ratings"]}
        ords = sorted(prompts.ORD[l] for l in lv.values())
        med = prompts.LEVELS[ords[len(ords)//2]] if ords else None
        per_code[c] = {"levels": lv, "median": med, "findings": counts[c],
                       "support": "ok" if counts[c] >= 5 else ("low" if counts[c] else "none"),
                       "spread": (max(ords) - min(ords)) if ords else None,
                       "mechanism": {m: results[m]["ratings"][c]["mechanism"] for m in raters if c in results[m]["ratings"]},
                       "cited": {m: results[m]["ratings"][c]["cited"] for m in raters if c in results[m]["ratings"]}}
    kappas = {}
    for i in range(len(raters)):
        for j in range(i+1, len(raters)):
            x = [prompts.ORD[results[raters[i]]["ratings"][c]["level"]] for c in codes]
            y = [prompts.ORD[results[raters[j]]["ratings"][c]["level"]] for c in codes]
            kappas[f"{raters[i]} vs {raters[j]}"] = round(wkappa(x, y), 3)
    summary = {"taxonomy": str(a.taxonomy), "mapping": str(a.mapping), "corpus": str(a.traces),
               "definition": "how much one occurrence, on its own, reduces the chance the final output is correct",
               "levels": prompts.LEVELS, "raters": raters, "per_code": per_code,
               "weighted_kappa_pairwise": kappas,
               "weighted_kappa_mean": round(sum(kappas.values())/len(kappas), 3) if kappas else None}
    (a.out / "severity.json").write_text(json.dumps(summary, indent=2))
    log("=" * 60)
    log(f"{'code':<7}{'median':<17}" + "".join(f"{m.split('/')[-1][:14]:>16}" for m in raters) + "  support")
    for c in codes:
        pc = per_code[c]
        log(f"{c:<7}{str(pc['median']):<17}" + "".join(f"{pc['levels'].get(m,'-'):>16}" for m in raters) + f"  {pc['support']}")
    log(f"weighted kappa: {kappas}  mean {summary['weighted_kappa_mean']}")
    log(f"-> {a.out}/severity.json")


if __name__ == "__main__":
    main()
