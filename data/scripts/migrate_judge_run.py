#!/usr/bin/env python3
"""Turn a finished new_pipeline judge run into a numbered mapping artifact, in the hover format.

    python3 data/scripts/migrate_judge_run.py --benchmark ifbench --run runs/new_pipeline/ifbench/map-1-judge --mapping map-1 --taxonomy tax-1 --split judging-sample-1

Writes data/<b>/mappings/<map-N>/{mapping.jsonl, judge_records/<candidate>.jsonl.gz, manifest.json,
provenance.json, README.md}. Every judged trace must be in exactly one capture's index, and its
candidate and task must match; codes must belong to the taxonomy; the judge must report that it
stripped nothing; no gold key may appear in a record. Refuses to overwrite.
"""
from __future__ import annotations
import argparse, datetime, gzip, hashlib, json, sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TODAY = datetime.date.today().isoformat()
sys.path.insert(0, str(REPO / "data" / "scripts"))
from audit_mapping import scan  # noqa: E402  (the same gold-key scan the audit uses)


def sha_f(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def fingerprint():
    h = hashlib.sha256()
    for p in sorted((REPO / "new_pipeline" / "judge").glob("*.py")) + [REPO / "new_pipeline" / "llm.py", REPO / "new_pipeline" / "goldfree.py"]:
        h.update(str(p.relative_to(REPO)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True); ap.add_argument("--run", type=Path, required=True); ap.add_argument("--mapping", required=True)
    ap.add_argument("--taxonomy", required=True, help="taxonomy id under data/<b>/taxonomies (the one the judge held)")
    ap.add_argument("--split", default=None, help="split artifact naming the judged tasks, for the record")
    ap.add_argument("--capture", default=None, help="the capture the judged traces belong to; required when a trace id exists in more than one capture (ifbench/hotpotqa induction captures repeat the ids of later fills)")
    ap.add_argument("--note", action="append", default=[], help="a provenance note, repeatable (e.g. how failed traces were completed)")
    ap.add_argument("--out-root", type=Path, default=None, help="testing only: write under this root instead of data/<b>/mappings")
    ap.add_argument("--taxonomy-file", type=Path, default=None, help="testing only: the taxonomy json the judge held, when it is not an artifact")
    a = ap.parse_args(); b = a.benchmark; D = REPO / "data" / b; run = a.run.resolve()
    root = a.out_root or (D / "mappings"); d = root / a.mapping
    if d.exists(): raise SystemExit(f"{d} exists; mappings are append-only, pick the next number")
    summary = json.loads((run / "summary.json").read_text()); settings = summary["settings"]
    tax_path = a.taxonomy_file or (D / "taxonomies" / a.taxonomy / "taxonomy.json")
    codes_allowed = {c["id"] for c in json.loads(tax_path.read_text())["codes"]}
    # capture indexes: trace -> (capture, row)
    idx, dup = {}, set()
    for f in sorted((D / "traces").glob("cap-*/index.jsonl")):
        if a.capture and f.parent.name != a.capture: continue
        for l in open(f):
            r = json.loads(l)
            if r["trace_id"] in idx: dup.add(r["trace_id"])
            idx.setdefault(r["trace_id"], (f.parent.name, r))
    (d / "judge_records").mkdir(parents=True)
    rows, by_cand, status, firing, per_cand, caps = [], {}, Counter(), Counter(), Counter(), Counter()
    audits = {"every_trace_in_capture_index": True, "candidate_and_task_match_capture": True, "codes_within_taxonomy": True, "judge_reported_nothing_stripped": True, "no_gold_keys_in_records": True}
    problems = []
    for f in sorted((run / "traces").glob("*.json")):
        t = json.loads(f.read_text()); tid = t["trace_id"]
        if tid not in idx: audits["every_trace_in_capture_index"] = False; problems.append(f"{tid} not in any capture"); continue
        if tid in dup: raise SystemExit(f"{tid} exists in more than one capture; pass --capture to say which one the judge read")
        cap, r = idx[tid]; caps[cap] += 1; cid = r["candidate_id"]
        if r["task_id"] != t.get("task_id"): audits["candidate_and_task_match_capture"] = False; problems.append(f"{tid}: task differs from capture")
        if t.get("gold_stripped") not in ([], None): audits["judge_reported_nothing_stripped"] = False; problems.append(f"{tid}: judge stripped {t.get('gold_stripped')}")
        codes = t.get("codes") or {}
        bad = set(codes) - codes_allowed
        if bad: audits["codes_within_taxonomy"] = False; problems.append(f"{tid}: codes outside taxonomy {sorted(bad)}")
        full = dict(t); full["candidate_id"] = cid; full["repeat"] = r["repeat"]; full["capture"] = cap; full["legacy_candidate_index"] = full.pop("candidate_index", None)
        if scan({k: v for k, v in full.items() if k != "gold_stripped"}): audits["no_gold_keys_in_records"] = False; problems.append(f"{tid}: gold key in record")
        status[t["status"]] += 1
        if t["status"] == "judged": per_cand[cid] += 1
        for c in codes: firing[c] += 1
        rows.append({"trace_id": tid, "candidate_id": cid, "task_id": r["task_id"], "repeat": r["repeat"], "status": t["status"],
                     "codes": codes if t["status"] == "judged" else None, "source": t.get("source") or {}, "error": t.get("error"), "attempts": t.get("attempts")})
        by_cand.setdefault(cid, []).append(full)
    if len(caps) != 1: raise SystemExit(f"judged traces come from {dict(caps)}; a mapping covers one capture")
    capture = next(iter(caps))
    rows.sort(key=lambda x: (x["candidate_id"], x["task_id"], x["repeat"]))
    with open(d / "mapping.jsonl", "w") as fh:
        for x in rows: fh.write(json.dumps(x, sort_keys=True) + "\n")
    rec_meta = {}
    for cid, recs in sorted(by_cand.items()):
        recs.sort(key=lambda x: (x["task_id"], x["repeat"])); f = d / "judge_records" / f"{cid}.jsonl.gz"
        with gzip.open(f, "wt", compresslevel=6, encoding="utf-8") as fh:
            for x in recs: fh.write(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n")
        rec_meta[cid] = {"file": f"judge_records/{cid}.jsonl.gz", "rows": len(recs), "sha256": sha_f(f)}
    attempted = len(rows); judged = status.get("judged", 0)
    hover_settings = {"annotators": settings["annotators"], "threshold": settings["threshold"], "panel_model": settings.get("panel_model") or settings["model"], "open_model": settings.get("open_model"),
                      "open": settings.get("open", True), "thinking": settings.get("thinking"), "traces_per_call": settings.get("traces_per_call"), "per_turn": settings.get("per_turn"),
                      "max_output": settings.get("max_output"), "timeout_s": settings.get("timeout"), "max_trace_chars": settings.get("max_trace_chars"), "temperature": settings.get("temperature"),
                      "route": "openrouter" if str(settings["model"]).startswith("openrouter/") else "gemini-direct"}
    man = {"mapping_id": a.mapping, "benchmark": b, "capture": capture, "portion": "judging", "split": a.split, "taxonomy": a.taxonomy, "taxonomy_sha256": sha_f(tax_path),
           "instrument": {"module": "new_pipeline/judge", "name": "measurement judge", "version": "panel + open reader, per-trace accounting", "source_fingerprint_sha256": fingerprint()},
           "settings": hover_settings, "counts": {"attempted": attempted, "judged": judged, "failed": status.get("failed", 0), "coverage": judged / attempted if attempted else 0.0, "tasks": len({x["task_id"] for x in rows}), "candidates": len(by_cand)},
           "judged_per_candidate": dict(sorted(per_cand.items())), "traces_firing_each_code": dict(sorted(firing.items())), "codes_never_fired": sorted(codes_allowed - set(firing)),
           "unmapped_problems": summary.get("unmapped_problems"), "judge_records": rec_meta, "complete": status.get("failed", 0) == 0, "last_segment_finished": TODAY,
           "record_format": "mapping.jsonl: one row per attempted trace with the codes that fired; judge_records/: the full judge output per trace (panel votes, open reader), one gzip JSONL per candidate",
           "notes": a.note, "audits": audits, "derives_from": [f"data/{b}/traces/{capture}", f"data/{b}/taxonomies/{a.taxonomy}"] + ([f"data/{b}/splits/{a.split}"] if a.split else []), "original_run": str(run.relative_to(REPO)) if run.is_relative_to(REPO) else str(run)}
    (d / "manifest.json").write_text(json.dumps(man, indent=2))
    (d / "provenance.json").write_text(json.dumps({"id": a.mapping, "kind": "mapping", "benchmark": b, "created": TODAY, "produced_by": "new_pipeline.judge.run, archived by data/scripts/migrate_judge_run.py",
        "instrument": man["instrument"], "derives_from": man["derives_from"], "counts": man["counts"], "checks": audits, "settings": hover_settings}, indent=2))
    fire_rows = "\n".join(f"| `{c}` | {n} |" for c, n in sorted(firing.items(), key=lambda kv: -kv[1]))
    (d / "README.md").write_text(f"""# {a.mapping} — `{a.taxonomy}` applied to the judged sample of the judging pool

The measurement judge read {attempted} traces of `{capture}` ({man['counts']['candidates']} candidates × {man['counts']['tasks']} tasks, repeat 0;
tasks named in `splits/{a.split}`) holding `{a.taxonomy}`: {hover_settings['annotators']} readers, a code counted when at least
{hover_settings['threshold']} agreed, plus the open reader ({hover_settings['open_model']}) that holds no taxonomy and whose problems are mapped
afterwards. {judged} judged, {status.get('failed', 0)} failed. Made {TODAY}.

| file | what it is |
|---|---|
| `mapping.jsonl` | one row per trace: ids, status, the codes that fired with their counts, which readers supplied each |
| `judge_records/<candidate>.jsonl.gz` | the full judge record per trace: panel votes, open-reader problems and their mapping |
| `manifest.json` | settings, counts, per-code firing, audits, record hashes |

Traces firing each code:

| code | traces |
|---|---:|
{fire_rows}

Never fired: {', '.join(f'`{c}`' for c in man['codes_never_fired']) or 'none'}.
""")
    print(f"{b} {a.mapping}: {judged}/{attempted} judged over {capture}; audits {audits}" + (f"; PROBLEMS: {problems[:3]}" if problems else ""))


if __name__ == "__main__":
    main()
