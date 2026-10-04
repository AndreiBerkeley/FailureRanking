#!/usr/bin/env python3
"""Copy the RedoAdamast multi-model taxonomy and judge runs of swebench, tau2bench and bfcl into data/<bench>/.

    python3 data/scripts/import_redo_adamast.py [--src ~/Desktop/RedoAdamast] [--date 2026-09-29]

RedoAdamast is only read: every file is copied with shutil.copy2, and a listing of (path, size, mtime) of every
source tree is taken before and after and must be identical. Nothing in FailureRank is overwritten: the script stops
before copying anything if a destination exists (artifacts are append-only; a re-import is the next number).

Per benchmark it writes
  traces/view-1/        source/ = data/<b>/multi-model copied whole (the judge views: generation sample and
                        validation, and test); index.jsonl maps every view trace id to candidate, task, repeat and the
                        cap-1 trace id; source_data_manifest.json = data/<b>/manifest.json
  outcomes/cap-1-complete.jsonl   data/<b>/outcomes.jsonl (cap-1 rows of the tasks every candidate ran)
  splits/pools-4/       taxonomy portion (generation stages), judged portion (the test tasks and their traces),
                        eval = every complete task in neither (bfcl: whose scenario is in neither)
  taxonomies/tax-1/     taxonomy.json = runs/<b>-multi/final_taxonomy.json; run/ = that run folder minus prompts/
  mappings/map-1/       run/ = runs/<b>-multi-test minus prompts/; mapping.jsonl = one row per judged trace with
                        its candidate, task, repeat and failure instances (no outcome)
and once data/redo_adamast/code-1/ = RedoAdamast generation/ minus __pycache__, with sha256 of every file.
prompts/ are left out: they are the full request texts (27-100 MB a run), rebuilt from the views and the taxonomy.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCHES = ("swebench", "tau2bench", "bfcl")
OUTCOME_KEYS = {"score", "resolved", "outcome", "reward", "gold", "passed"}
SKIP_DIRS = {"prompts", "__pycache__"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def listing(paths):
    out = {}
    for base in paths:
        for dp, _, fs in os.walk(base):
            for f in fs:
                p = Path(dp) / f
                st = p.stat()
                out[str(p)] = (st.st_size, st.st_mtime_ns)
    return out


def copy_tree(src: Path, dst: Path, copied: list, skip=SKIP_DIRS):
    for dp, dns, fs in os.walk(src):
        dns[:] = sorted(d for d in dns if d not in skip)
        rel = Path(dp).relative_to(src)
        for f in sorted(fs):
            copy_file(Path(dp) / f, dst / rel / f, copied)


def copy_file(src: Path, dst: Path, copied: list):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append((src, dst))


def dump(obj, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def dump_jsonl(rows, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def gold_keys(x) -> set:
    if isinstance(x, dict):
        return (set(x) & OUTCOME_KEYS) | set().union(*(gold_keys(v) for v in x.values()))
    if isinstance(x, list):
        return set().union(*(gold_keys(v) for v in x)) if x else set()
    return set()


PRICE_PER_M = {"arena/gemini-3.8-flash": (0.75, 3.75)}


def usage(run: Path, model: str) -> dict:
    """Token use of a generation run from its call_log.jsonl; generation runs log no billed cost, so it is estimated."""
    log = run / "call_log.jsonl"
    if not log.exists():
        return {"logged": False, "note": "the run has no call_log.jsonl; its token use and cost were not recorded"}
    rows = [json.loads(l) for l in open(log)]
    t = {k: sum(r.get(k) or 0 for r in rows) for k in ("prompt_tokens", "output_tokens", "thought_tokens")}
    pi, po = PRICE_PER_M[model]
    return {"logged": True, "attempts": len(rows), **t,
            "estimated_usd": round(t["prompt_tokens"] * pi / 1e6 + t["output_tokens"] * po / 1e6, 2),
            "estimate_note": f"list price ${pi} / ${po} per M tokens in / out; output_tokens include thinking. The "
                             f"run logs no billed cost; the same rule gives $57.52 for swebench map-1, billed $57.43"}


def import_bench(b: str, src: Path, date: str, code_manifest: dict, copied: list) -> dict:
    D = ROOT / "data" / b
    view, outc = D / "traces" / "view-1", D / "outcomes"
    split, tax, mp = D / "splits" / "pools-4", D / "taxonomies" / "tax-1", D / "mappings" / "map-1"
    s_mm, s_gen, s_test = src / "data" / b / "multi-model", src / "runs" / f"{b}-multi", src / "runs" / f"{b}-multi-test"
    man = json.load(open(s_mm / "manifest.json"))

    # ---- traces/view-1 ----------------------------------------------------------------------------------------
    copy_tree(s_mm, view / "source", copied)
    copy_file(src / "data" / b / "manifest.json", view / "source_data_manifest.json", copied)
    files = {}
    for sub in ("sample", "validation", "test"):
        for f in sorted((view / "source" / sub).iterdir()):
            v = json.load(open(f))
            files[v["trace_id"]] = (f"source/{sub}/{f.name}", v)
    entries = [dict(t, portion=t["stage"]) for t in man["traces"]] + [dict(t, portion="test") for t in man["test"]["traces"]]
    want = {(t["model"], t["task_id"], t["repeat"]): t for t in entries}
    body = {}
    for g in sorted((src / "data" / b / "traces").glob("*.jsonl.gz")):
        with gzip.open(g, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                k = (r["candidate_id"], r["task_id"], r.get("repeat", 0))
                if k in want:
                    body[k] = r
    index, identical, view_keys = [], 0, set()
    for k, t in want.items():
        rel, v = files[t["trace_id"]]
        view_keys |= set(v)
        identical += v["messages"] == body[k]["judge_view"]["messages"] and v["task_id"] == k[1]
        index.append({"view_trace_id": t["trace_id"], "file": rel, "portion": t["portion"], "candidate_id": k[0],
                      "task_id": k[1], "repeat": k[2], "cap1_trace_id": body[k]["trace_id"]})
    index.sort(key=lambda r: (r["portion"] != "test", r["portion"], r["task_id"], r["candidate_id"]))
    dump_jsonl(index, view / "index.jsonl")
    by_view = {r["view_trace_id"]: r for r in index}
    n_view = len(index)
    assert identical == n_view == len(files), (b, identical, n_view, len(files))

    # ---- outcomes/cap-1-complete ------------------------------------------------------------------------------
    copy_file(src / "data" / b / "outcomes.jsonl", outc / "cap-1-complete.jsonl", copied)
    rows = [json.loads(l) for l in open(outc / "cap-1-complete.jsonl")]
    head = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:data/{b}/outcomes/cap-1.jsonl"],
                          capture_output=True, text=True, check=True).stdout
    ours = {(r["candidate_id"], r["task_id"], r["repeat"]): r for r in map(json.loads, head.splitlines())}
    same_rows = sum(ours.get((r["candidate_id"], r["task_id"], r["repeat"])) == r for r in rows)
    cands = sorted({r["candidate_id"] for r in rows})
    per_task = collections.defaultdict(set)
    for r in rows:
        per_task[r["task_id"]].add(r["candidate_id"])
    complete = sorted(t for t, cs in per_task.items() if len(cs) == len(cands))
    scen = {r["task_id"]: r.get("scenario") for r in rows}
    assert len(complete) == len(per_task)
    dump({"id": "cap-1-complete", "kind": "outcomes", "benchmark": b, "created": date,
          "produced_by": f"copied from {src}/data/{b}/outcomes.jsonl by data/scripts/import_redo_adamast.py",
          "derives_from": [f"outcomes/cap-1.jsonl (git HEAD; removed from the working tree when the capture moved "
                           f"to RedoAdamast on 2026-09-26)"],
          "rule": json.load(open(src / "data" / b / "manifest.json")).get("rule"),
          "counts": {"rows": len(rows), "candidates": len(cands), "tasks": len(per_task),
                     "cap1_rows": len(ours), "cap1_tasks": len({k[1] for k in ours})},
          "checks": {"every_row_identical_to_cap1": same_rows == len(rows),
                     "every_task_run_by_every_candidate": True},
          "sha256": sha(outc / "cap-1-complete.jsonl")}, outc / "cap-1-complete.provenance.json")

    # ---- splits/pools-4 ---------------------------------------------------------------------------------------
    stage_tasks = collections.defaultdict(list)
    for t in man["traces"]:
        if t["task_id"] not in stage_tasks[t["stage"]]:
            stage_tasks[t["stage"]].append(t["task_id"])
    taxonomy_tasks = [x for s in ("initial", "seg1", "final") for x in stage_tasks[s]]
    judged = sorted({t["task_id"] for t in man["test"]["traces"]})
    if b == "bfcl":
        used = {scen[t] for t in taxonomy_tasks + judged}
        evals = sorted(t for t in complete if scen[t] not in used)
    else:
        evals = sorted(set(complete) - set(taxonomy_tasks) - set(judged))
    assert not (set(taxonomy_tasks) & set(judged)) and not (set(evals) & (set(taxonomy_tasks) | set(judged)))
    trace_rows = lambda lst: [{"candidate_id": t["model"], "task_id": t["task_id"], "repeat": t["repeat"],
                               "view_trace_id": t["trace_id"], **({"stage": t["stage"]} if "stage" in t else {})}
                              for t in lst]
    sp = {"benchmark": b, "split_id": "pools-4", "created": date,
          "unit": man["test"]["unit"],
          "purpose": "taxonomy = the RedoAdamast generation run's tasks (initial, seg1, final); judged = its test "
                     "tasks, judged by map-1; eval = the generalization target",
          "protocol": {"taxonomy": f"RedoAdamast data/{b}/multi-model/manifest.json: tasks {man['tasks']}, "
                                   f"{man['models_per_task']} candidates per task, seed {man['seed']}",
                       "judged": man["test"]["rule"] + f" (seed {man['test']['seed']})",
                       "eval": "every task all candidates ran that is in neither portion" +
                               ("; a task is out if its scenario is in either portion" if b == "bfcl" else "")},
          "sizes": {"taxonomy": len(taxonomy_tasks), "judged": len(judged), "eval": len(evals),
                    "complete_tasks": len(complete)},
          "portions": {"taxonomy": taxonomy_tasks, "judged": judged, "eval": evals},
          "taxonomy_stages": {s: stage_tasks[s] for s in ("initial", "seg1", "final")},
          "judged_traces": trace_rows(man["test"]["traces"]),
          "taxonomy_traces": trace_rows(man["traces"])}
    if b == "bfcl":
        sp["scenarios"] = {"taxonomy": sorted({scen[t] for t in taxonomy_tasks}), "judged": sorted({scen[t] for t in judged}),
                           "eval": sorted({scen[t] for t in evals})}
    dump(sp, split / "split.json")
    dump({"id": "pools-4", "kind": "task split", "benchmark": b, "created": date, "counts": sp["sizes"],
          "produced_by": {"script": "data/scripts/import_redo_adamast.py",
                          "drawn_by": f"RedoAdamast generation/select_tasks.py and generation/export_test.py "
                                      f"(snapshot data/redo_adamast/code-1)"},
          "derives_from": ["traces/view-1/source/manifest.json", "outcomes/cap-1-complete.jsonl (task list only)"],
          "checks": {"portions_disjoint": True, "scenarios_disjoint": True if b == "bfcl" else None,
                     "judged_traces": len(sp["judged_traces"]),
                     "one_trace_per_candidate_per_judged_task":
                         len(sp["judged_traces"]) == len(judged) * len(cands) and
                         len({(t["candidate_id"], t["task_id"]) for t in sp["judged_traces"]}) == len(sp["judged_traces"])},
          "note": "not stratified and not drawn by our make_split.py; the other pools-* splits are unrelated draws"},
         split / "provenance.json")

    # ---- taxonomies/tax-1 -------------------------------------------------------------------------------------
    copy_tree(s_gen, tax / "run", copied)
    copy_file(s_gen / "final_taxonomy.json", tax / "taxonomy.json", copied)
    modes = json.load(open(tax / "taxonomy.json"))
    tax_ids = {m["id"] for m in modes}
    config = json.load(open(s_gen / "config.json"))
    gen_usage = usage(s_gen, config["model"])
    dump({"id": "tax-1", "kind": "taxonomy", "benchmark": b, "created": date,
          "produced_by": f"RedoAdamast generation/run.py, run folder {s_gen} (copied minus prompts/)",
          "model": config["model"], "config": config,
          "derives_from": ["traces/view-1 (portions initial, seg1, final)", "splits/pools-4#taxonomy"],
          "counts": {"codes": len(modes), "by_origin": dict(collections.Counter(m.get("origin") for m in modes)),
                     "instances": sum(len(m.get("instances", [])) for m in modes)},
          "usage": gen_usage, "code": code_manifest, "sha256": sha(tax / "taxonomy.json")}, tax / "provenance.json")

    # ---- mappings/map-1 ---------------------------------------------------------------------------------------
    copy_tree(s_test, mp / "run", copied)
    summ = json.load(open(s_test / "summary.json"))
    ext = json.load(open(s_test / "taxonomy_extended.json"))
    recs = [json.load(open(p)) for p in sorted((s_test / "traces").glob("*.json"))]
    out, gold, codes_out, cand_task_ok = [], set(), set(), 0
    test_ids = {t["trace_id"] for t in man["test"]["traces"]}
    for r in recs:
        ix = by_view[r["trace_id"]]
        cand_task_ok += ix["portion"] == "test" and ix["task_id"] == r["task_id"]
        gold |= gold_keys(r)
        insts = r.get("points") or []
        for p in insts:
            codes_out |= set(p.get("codes") or [])
        out.append({"trace_id": r["trace_id"], "cap1_trace_id": ix["cap1_trace_id"], "candidate_id": ix["candidate_id"],
                    "task_id": r["task_id"], "repeat": ix["repeat"], "status": r["status"], "error": r.get("error"),
                    "attempts": r.get("attempts"), "turns": r.get("turns"), "codes": r.get("codes") or {},
                    "n_instances": len(insts), "n_rejected": len(r.get("rejected") or []),
                    "instances": insts, "rejected": r.get("rejected") or [], "modes_added": r.get("modes_added") or []})
    out.sort(key=lambda x: (x["candidate_id"], x["task_id"]))
    dump_jsonl(out, mp / "mapping.jsonl")
    failed = sorted(x["trace_id"] for x in out if x["status"] != "judged")
    per_cand = collections.Counter(x["candidate_id"] for x in out if x["status"] == "judged")
    dump({"id": "map-1", "kind": "mapping", "benchmark": b, "created": date,
          "produced_by": f"RedoAdamast generation/judge.py, run folder {s_test} (copied minus prompts/); "
                         f"mapping.jsonl by data/scripts/import_redo_adamast.py",
          "judge": {"model": summ["model"], "design": summ["judge"], "workers": summ["workers"],
                    "answers": summ["answers"]},
          "derives_from": ["traces/view-1 (portion test)", "taxonomies/tax-1", "splits/pools-4#judged"],
          "counts": {"attempted": len(recs), "judged": len(recs) - len(failed), "failed": len(failed),
                     "coverage": round((len(recs) - len(failed)) / len(recs), 4), "tasks": len({x["task_id"] for x in out}),
                     "candidates": len(per_cand), "instances": sum(x["n_instances"] for x in out),
                     "rejected": sum(x["n_rejected"] for x in out), "judged_per_candidate": dict(sorted(per_cand.items()))},
          "failed_trace_ids": failed,
          "summary": {k: summ[k] for k in ("fit_existing_mode", "modes_start", "modes_added", "quotes_not_verbatim",
                                           "starting_modes_never_used", "possible_modes_points")},
          "cost": summ["cost"],
          "checks": {"every_trace_in_view_index_as_test": cand_task_ok == len(recs),
                     "records_equal_judged_traces_of_split": {r["trace_id"] for r in recs} == test_ids,
                     "codes_within_taxonomy": codes_out <= tax_ids,
                     "taxonomy_extended_equals_tax1": ext.get("taxonomy") == modes and not ext.get("added"),
                     "instance_count_equals_summary": sum(x["n_instances"] for x in out) == summ["points"],
                     "failed_equal_summary": failed == sorted(summ["failed"]),
                     "no_gold_keys_in_records": not gold},
          "code": code_manifest}, mp / "provenance.json")
    return {"bench": b, "view_traces": n_view, "outcome_rows": len(rows), "complete_tasks": len(complete),
            "split": sp["sizes"], "tax_codes": len(modes), "gen_usd_est": gen_usage.get("estimated_usd"),
            "judged": len(recs) - len(failed), "failed": len(failed), "instances": summ["points"],
            "judge_cost": summ["cost"]["billed_usd"]}


def document(b: str, src: Path, date: str):
    """view-1's provenance.json and the READMEs of view-1, pools-4, tax-1 and map-1, from what is on disk."""
    D = ROOT / "data" / b
    view, split, tax, mp = D / "traces/view-1", D / "splits/pools-4", D / "taxonomies/tax-1", D / "mappings/map-1"
    index = [json.loads(l) for l in open(view / "index.jsonl")]
    sp, tp, mpv = (json.load(open(p)) for p in (split / "split.json", tax / "provenance.json", mp / "provenance.json"))
    portions = collections.Counter(r["portion"] for r in index)
    keys = set()
    for r in index:
        keys |= set(json.load(open(view / r["file"])))
    sub_n = {s: len(list((view / "source" / s).iterdir())) for s in ("sample", "validation", "test")}
    n_c, n_i = len({r["candidate_id"] for r in index if r["portion"] == "test"}), len(index)
    dump({"id": "view-1", "kind": "trace view", "benchmark": b, "created": date,
          "produced_by": f"RedoAdamast generation/prepare_data.py (sample, validation) and export_test.py (test) from "
                         f"cap-1; copied from {src}/data/{b}/multi-model by data/scripts/import_redo_adamast.py",
          "derives_from": ["traces/cap-1 (moved to RedoAdamast data/%s/traces on 2026-09-26)" % b],
          "counts": {"views": n_i, "by_portion": dict(portions), "files": sub_n},
          "checks": {"messages_identical_to_cap1_judge_view": n_i, "view_keys": sorted(keys),
                     "no_candidate_or_outcome_in_views": keys == {"trace_id", "task_id", "messages"}},
          "join": "index.jsonl: view_trace_id -> candidate_id, task_id, repeat, portion, cap1_trace_id"},
         view / "provenance.json")
    (view / "README.md").write_text(f"""# view-1 — RedoAdamast's judge views of cap-1 ({b})

The judge's view (`trace_id`, `task_id`, `messages`) of {n_i} cap-1 runs, as RedoAdamast exported them for its
multi-model taxonomy run (`sample/` {sub_n['sample']}, `validation/` {sub_n['validation']}) and its judge run
(`test/` {sub_n['test']}). Copied {date} from `~/Desktop/RedoAdamast/data/{b}/multi-model/` by
`data/scripts/import_redo_adamast.py`; the original stays there.

- `source/` — that folder copied whole. The trace files are not in git; `source/manifest.json` is.
- `index.jsonl` — view trace id → candidate, task, repeat, portion (initial / seg1 / final / test), cap-1 trace id.
- `source_data_manifest.json` — RedoAdamast's manifest of the capture it moved out of `traces/cap-1`.

View ids are not cap-1 trace ids; join through `index.jsonl`. Every view's messages equal the cap-1 body's
`judge_view.messages` (checked for all {n_i}). Views carry no candidate identity and no outcome.
""")
    s, st = sp["sizes"], sp["taxonomy_stages"]
    ev = set(sp["portions"]["eval"])
    n_ev_rows = sum(json.loads(l)["task_id"] in ev for l in open(D / "outcomes/cap-1-complete.jsonl"))
    oc = json.load(open(D / "outcomes/cap-1-complete.provenance.json"))["counts"]
    scen = (f"Taxonomy and judged take one variant of each of {len(sp['scenarios']['taxonomy'])} and "
            f"{len(sp['scenarios']['judged'])} scenarios; eval takes every complete variant of the other "
            f"{len(sp['scenarios']['eval'])}.") if b == "bfcl" else ""
    thin = ("\n**The eval portion is thin:** 17 tasks (4 trials each) — τ²-bench banking has 97 tasks, 10 of them not "
            "run by every candidate, and generation plus test take 70.\n") if s["eval"] < 50 else ""
    (split / "README.md").write_text(f"""# pools-4 — RedoAdamast's generation and test draw ({b})

| portion | tasks | traces | role |
|---|---:|---:|---|
| taxonomy | {s['taxonomy']} (initial {len(st['initial'])}, seg1 {len(st['seg1'])}, final {len(st['final'])}) | {len(sp['taxonomy_traces'])} | generated `taxonomies/tax-1` |
| judged | {s['judged']} | {len(sp['judged_traces'])} (all {n_c} candidates, one run each) | judged by `mappings/map-1` |
| eval | {s['eval']} | {n_ev_rows:,} outcomes | generalization target |
{scen and chr(10) + scen + chr(10)}
Drawn by RedoAdamast (`select_tasks.py`, `export_test.py`, seed 0; snapshot in `data/redo_adamast/code-1`), not
by our `make_split.py`: not stratified, and unrelated to `pools-1`..`pools-3`. **eval** = every task all
{n_c} candidates ran that is in neither portion{'; a task is out if its scenario is in either' if b == 'bfcl' else ''}.
The {oc['cap1_tasks'] - oc['tasks']} cap-1 tasks some candidate did not run are in no portion; see
`outcomes/cap-1-complete.provenance.json`.
{thin}""")
    u = tp["usage"]
    cost = (f"~${u['estimated_usd']:.2f} estimated from {u['prompt_tokens']:,} input and {u['output_tokens']:,} output "
            f"tokens (the run logs no billed cost)") if u.get("logged") else "not recorded (the run has no call log)"
    cfg = tp["config"]
    (tax / "README.md").write_text(f"""# tax-1 — RedoAdamast multi-model taxonomy ({b})

{tp['counts']['codes']} codes ({', '.join(f'{v} {k}' for k, v in tp['counts']['by_origin'].items())}), generated by
RedoAdamast `generation/run.py` with `{cfg['model']}` on the taxonomy portion of `splits/pools-4`: stages
{cfg['stages']}, {cfg['annotators']} annotators, {cfg['rounds']} round and {cfg['final_rounds']} final round,
{cfg['traces_per_round']} traces per round. Cost: {cost}.

- `taxonomy.json` — `runs/{b}-multi/final_taxonomy.json` (each code: definition, when to use / not use,
  origin, and its evidence instances).
- `run/` — that run folder minus `prompts/`: every stage's output (`01_field_analysis` … `10_taxonomy_seg3_r1`),
  `config.json`, `allocation.json`, `final_taxonomy_evidence.json`, call report and log. `run/calls/` (raw
  replies) is not in git.

Codes are RedoAdamast's `FM-NN`; they are unrelated to the codes of our own `runs/new_pipeline/{b}` run.
""")
    c, sm = mpv["counts"], mpv["summary"]
    failed = (f" Failed (no reply after retries): {', '.join(mpv['failed_trace_ids'])}." if mpv["failed_trace_ids"] else "")
    (mp / "README.md").write_text(f"""# map-1 — RedoAdamast judge run on the judged portion ({b})

`{mpv['judge']['model']}`, {mpv['judge']['design']}. Taxonomy `tax-1`, no modes added.
{c['attempted']} traces ({c['tasks']} tasks × {c['candidates']} candidates), {c['judged']} judged.{failed}
{c['instances']:,} failure instances, {c['rejected']:,} candidate instances the judge rejected;
{sm['fit_existing_mode']:.1%} fit an existing mode; {sm['quotes_not_verbatim']} quotes not verbatim.
Billed ${mpv['cost']['billed_usd']:.2f}. No recovery pass has been run on these traces.

- `mapping.jsonl` — one row per trace: view and cap-1 trace ids, candidate, task, repeat, status, per-code counts,
  the failure instances (turn, message, codes, problem, missing, evidence, quote_valid, none_fits) and the rejected
  ones. No outcome: join `outcomes/cap-1-complete.jsonl` on `cap1_trace_id`.
- `run/` — RedoAdamast's run folder minus `prompts/`: per-trace records (`run/traces/`), `summary.json`,
  `call_report.txt`, `call_log.jsonl`, `taxonomy_extended.json` (identical to `tax-1`). `run/calls/` is not in git.
- `provenance.json` — counts, checks, cost, code hashes.
""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(Path.home() / "Desktop" / "RedoAdamast"))
    ap.add_argument("--date", default="2026-09-29")
    ap.add_argument("--document-only", action="store_true",
                    help="only (re)write view-1/provenance.json and the READMEs of an existing import")
    a = ap.parse_args()
    src = Path(a.src).resolve()
    if a.document_only:
        for b in BENCHES:
            document(b, src, a.date)
        return
    code_dst = ROOT / "data" / "redo_adamast" / "code-1"
    dests = [code_dst] + [ROOT / "data" / b / p for b in BENCHES for p in
                          ("traces/view-1", "outcomes/cap-1-complete.jsonl", "splits/pools-4", "taxonomies/tax-1",
                           "mappings/map-1")]
    clash = [str(d) for d in dests if d.exists()]
    if clash:
        sys.exit("destinations exist (append-only; import into the next number instead):\n  " + "\n  ".join(clash))
    trees = [src / "generation"] + [src / "data" / b for b in BENCHES] + \
            [src / "runs" / f"{b}-multi{s}" for b in BENCHES for s in ("", "-test")]
    before = listing(trees)

    copied = []
    copy_tree(src / "generation", code_dst, copied, skip={"__pycache__"})   # the code's own prompts/ are part of the code
    code_files = {str(p.relative_to(code_dst)): sha(p) for p in sorted(code_dst.rglob("*")) if p.is_file()}
    dump({"id": "code-1", "kind": "code snapshot", "created": a.date, "source": str(src / "generation"),
          "note": "RedoAdamast is not a git repository; this snapshot is the code as it stood when its runs were copied",
          "sha256": code_files}, code_dst.parent / "code-1.provenance.json")
    code_manifest = {"snapshot": "data/redo_adamast/code-1",
                     "files": {k: code_files[k] for k in ("run.py", "judge.py", "llm.py", "export_test.py",
                                                          "select_tasks.py", "prepare_data.py") if k in code_files}}
    report = [import_bench(b, src, a.date, code_manifest, copied) for b in BENCHES]
    for b in BENCHES:
        document(b, src, a.date)

    bad = [str(d) for s, d in copied if sha(s) != sha(d)]
    after = listing(trees)
    print(json.dumps({"copied_files": len(copied), "copies_not_identical": bad,
                      "source_unchanged": before == after, "source_files": len(before), "benchmarks": report}, indent=1))
    if bad or before != after:
        sys.exit(1)


if __name__ == "__main__":
    main()
