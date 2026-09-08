#!/usr/bin/env python3
"""Duplicate one of the gepa-artifact benchmarks (ifbench, hotpotqa) into the
data/ layout: task registry with gold, the optimizer's split and run, the
candidates, the evaluation split, the trace captures and their outcomes. The
earlier pipeline's taxonomy and judge mapping are NOT carried over; they stay
in benchmarks/<benchmark>/taxonomies and mappings as the archive.

    python3 data/scripts/migrate_gepa_artifact_benchmark.py --benchmark ifbench

Read-only on benchmarks/ and legacy/. Refuses to overwrite an existing
data/<benchmark> unless --force. Every identity is re-keyed to registry ids and
verified; a failed check aborts the run. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TRIAL = REPO / "legacy" / "trials" / "2026-08-25-gepa-cross-benchmark-candidates"
VENDOR = TRIAL / "vendor" / "gepa-artifact" / "gepa_artifact" / "benchmarks"
TODAY = "2026-09-06"
SCRIPT = "data/scripts/migrate_gepa_artifact_benchmark.py"
TASK_MODEL = "gemini/gemini-3.1-flash-lite"

# Keys that must never appear in a trace body, a judge view, or a judge record.
GOLD_KEY_PATTERNS = ("gold", "supporting", "required_titles", "outcome", "score", "answer_gold")
GOLD_KEY_EXACT = {"label"}
# Keys the source corpora carry that are gold and are stripped on migration.
STRIP_FROM_JUDGE_VIEW = ("outcome_score",)

CFG = {
    "ifbench": {
        "title": "IFBench",
        "old": REPO / "benchmarks" / "ifbench",
        "traces": REPO / "benchmarks" / "ifbench" / "traces" / "traces-1",
        "domain_size": 194,
        "structure": None,
        "program_name": "IFBenchCoT2StageProgram (2 modules)",
        "modules": [("generate_response_module", "reads the prompt, writes a response"),
                    ("ensure_correct_response_module", "reads the prompt and that response, checks it against the constraints, writes the final response")],
        "metric": "IFBench official per-instruction average: the fraction of the task's instructions the final response satisfies, 1.0 when all do",
        "task_source": "IFBench (allenai), test and train files as vendored in the gepa-artifact at commit cbefbc1aa0f43dd39874ec4bf42211365dbda42e",
        "domain_corpus": None,
    },
    "hotpotqa": {
        "title": "HotpotQA",
        "old": REPO / "benchmarks" / "hotpotqa",
        "traces": REPO / "legacy" / "archive-2026-09-01" / "hotpotqa" / "traces-1",
        "domain_size": 200,
        "structure": REPO / "runs" / "taxgen-v2" / "structures" / "hotpotqa.json",
        "program_name": "HotpotQA multi-hop program (4 modules + retrieval)",
        "modules": [("summarize1", "reads the question and the first-hop passages, writes a summary"),
                    ("create_query_hop2", "reads the question and that summary, writes the second-hop search query"),
                    ("summarize2", "reads the question, the earlier context and the second-hop passages, writes a summary"),
                    ("final_answer", "reads the question and both summaries, writes the answer")],
        "metric": "HotpotQA official exact match on the answer field, 1.0 or 0.0",
        "task_source": "HotpotQA fullwiki (Hugging Face hotpot_qa) through the pinned gepa-artifact loader at commit cbefbc1aa0f43dd39874ec4bf42211365dbda42e, snapshot inputs/hotpotqa_official_snapshot.json",
        "domain_corpus": "generalization/corpus",
    },
}


# ------------------------------------------------------------------ io ---- #
def log(m): print(m, flush=True)
def jload(p): return json.load(open(p))
def jdump(o, p, indent=2):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(o, f, indent=indent, sort_keys=True, ensure_ascii=False); f.write("\n")
def jsonl_write(rows, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for r in rows: f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()
def first_sentence(s):
    s = " ".join(str(s).split()); m = re.match(r"(.+?\.)(\s|$)", s); return (m.group(1) if m else s)[:200]


def scan_gold_keys(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in GOLD_KEY_EXACT or any(p in kl for p in GOLD_KEY_PATTERNS):
                hits.append(f"{path}/{k}")
            hits.extend(scan_gold_keys(v, f"{path}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj): hits.extend(scan_gold_keys(v, f"{path}[{i}]"))
    return hits


def provenance(pid, kind, bench, derives_from, counts, checks, extra=None):
    d = {"id": pid, "kind": kind, "benchmark": bench, "created": TODAY, "derives_from": derives_from,
         "produced_by": {"script": SCRIPT, "command": f"python3 {SCRIPT} --benchmark {bench}"},
         "counts": counts, "checks": checks}
    if extra: d.update(extra)
    return d


def example_id(bench, ex):
    # run_measurement.example_id, reproduced: sha256 of the sorted-key JSON of the whole record.
    payload = json.dumps(ex, ensure_ascii=False, sort_keys=True)
    dg = sha256_bytes(payload.encode())[:20]
    for k in ("id", "_id", "key"):
        if ex.get(k) is not None: return f"{bench}:{ex[k]}:{dg}"
    return f"{bench}:sha256:{dg}"


def trace_id(bench, cidx, task_id, repeat):
    # convert_traces_for_adamast.trace_id, reproduced, so ids match the source corpora and mappings.
    return sha256_bytes(f"{bench}|{cidx}|{task_id}|{repeat}".encode())[:24]


def cid_of(components): return "cnd-" + sha256_bytes(json.dumps(components, sort_keys=True).encode())[:12]


# ------------------------------------------------------------- pieces ---- #
def load_source_tasks(bench):
    """-> {task_id: row} for every task in the source, with inputs and gold."""
    rows = {}
    if bench == "ifbench":
        for fname, part in (("IFBench_test.jsonl", "test"), ("IFBench_train.jsonl", "train")):
            for line in open(VENDOR / "IFBench" / "data" / fname):
                if not line.strip(): continue
                ex = json.loads(line)
                tid = example_id(bench, ex)
                rows[tid] = {"task_id": tid, "benchmark": bench, "inputs": {"prompt": ex["prompt"]},
                             "gold": {"instruction_id_list": ex["instruction_id_list"], "kwargs": ex["kwargs"]},
                             "source": {"dataset": "IFBench (allenai)", "file": f"gepa-artifact/benchmarks/IFBench/data/{fname}",
                                        "part": part, "key": ex["key"],
                                        "artifact_commit": "cbefbc1aa0f43dd39874ec4bf42211365dbda42e"}}
    else:
        snap = jload(TRIAL / "inputs" / "hotpotqa_official_snapshot.json")
        for part in ("train", "validation", "evaluation"):
            for ex in snap[part]:
                tid = example_id(bench, ex)
                rows[tid] = {"task_id": tid, "benchmark": bench, "inputs": {"question": ex["question"]},
                             "gold": {"answer": ex["answer"], "supporting_facts": ex["supporting_facts"]},
                             "source": {"dataset": "hotpot_qa fullwiki", "snapshot": "legacy/trials/2026-08-25-gepa-cross-benchmark-candidates/inputs/hotpotqa_official_snapshot.json",
                                        "part": part, "id": ex["id"], "level": ex.get("level"), "type": ex.get("type"),
                                        "artifact_commit": snap["artifact_commit"],
                                        "note": "the task id hashes the full snapshot record including its distractor context paragraphs; the context is not copied here"}}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True, choices=sorted(CFG))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    b = a.benchmark; C = CFG[b]; OLD = C["old"]; TR = C["traces"]; NEW = REPO / "data" / b
    if NEW.exists() and any(p for p in NEW.iterdir() if p.name != "scripts"):
        if not a.force: sys.exit(f"{NEW} already populated; pass --force to rebuild")
        for p in NEW.iterdir():
            if p.name != "scripts": shutil.rmtree(p) if p.is_dir() else p.unlink()

    # ---------------- splits ----------------
    log("splits")
    opt = jload(OLD / "splits" / "split-1" / "optimization_split.json")
    ev = jload(OLD / "splits" / "split-1" / "evaluation_split.json")
    train, val = list(opt["train_100_ids"]), list(opt["validation_100_ids"])
    sample, domain = list(ev["measurement_ids"]), list(ev["generalization_ids"])
    parts = {"train": set(train), "validation": set(val), "sample": set(sample), "domain": set(domain)}
    names = list(parts)
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            assert not parts[x] & parts[y], f"{x} overlaps {y}"
    assert len(sample) == 100 and len(domain) == C["domain_size"]
    assert set(opt["evaluation_ids"]) == parts["sample"] | parts["domain"]
    jdump({"benchmark": b, "split_id": "gepa-1", "purpose": "the task partition the optimizer run gepa-1 was given",
           "portions": {"train": train, "validation": val}, "sizes": {"train": 100, "validation": 100},
           "seed": opt.get("split_seed"), "protocol": opt.get("split_protocol"), "source": opt["source"],
           "source_commit": opt.get("source_commit"),
           "source_pool": {"train": opt.get("source_train_count"), "validation": opt.get("source_validation_count")},
           "order": "as frozen in benchmarks/%s/splits/split-1/optimization_split.json" % b}, NEW / "splits" / "gepa-1" / "split.json")
    jdump(provenance("gepa-1", "task split", b, [f"benchmarks/{b}/splits/split-1/optimization_split.json"],
                     {"train": 100, "validation": 100}, {"disjoint": True}), NEW / "splits" / "gepa-1" / "provenance.json")
    (NEW / "splits" / "gepa-1" / "README.md").write_text(f"""# gepa-1 — the split the optimizer ran on

Train 100 and validation 100 task ids, drawn with seed 0 and a proportional
stratified protocol from the artifact's own train and validation pools, frozen
before the optimizer run `gepa-1` and consumed by it. Copied without reordering
from `benchmarks/{b}/splits/split-1`.

Every candidate in the registry was proposed and scored on these tasks. They are
forbidden for any scoring that claims to be free of optimizer influence; the
taxonomy-induction corpus was drawn from the train portion on purpose.
""")
    jdump({"benchmark": b, "split_id": "eval-1",
           "purpose": "evaluation: a sample to read closely and a held-out domain to generalise to",
           "portions": {"sample": sample, "domain": domain}, "sizes": {"sample": 100, "domain": C["domain_size"]},
           "protocol": ev.get("split_protocol"), "cut": ev.get("cut"), "disjoint_from": ["gepa-1"],
           "old_names": {"sample": "split-1 measurement_ids", "domain": "split-1 generalization_ids"},
           "note": "both portions come from the artifact's test set, which the optimizer never saw; together they are the whole test set"},
          NEW / "splits" / "eval-1" / "split.json")
    jdump(provenance("eval-1", "task split", b, [f"benchmarks/{b}/splits/split-1/evaluation_split.json"],
                     {"sample": 100, "domain": C["domain_size"]}, {"portions_disjoint": True, "disjoint_from_gepa_1": True}),
          NEW / "splits" / "eval-1" / "provenance.json")
    (NEW / "splits" / "eval-1" / "README.md").write_text(f"""# eval-1 — the evaluation split

Two portions of tasks the optimizer never saw, disjoint from each other and
from `gepa-1`; together they are the artifact's entire test set.

| portion | tasks | role |
|---|---:|---|
| `sample` | 100 | the set a candidate is read closely on |
| `domain` | {C['domain_size']} | the held-out set the sample is supposed to speak for |

Copied without reordering from `benchmarks/{b}/splits/split-1`, where the
portions were called `measurement` and `generalization`. Nothing about `domain`
may be used to build an instrument or a formula; it is only ever the target.
""")

    # ---------------- tasks ----------------
    log("tasks")
    src_tasks = load_source_tasks(b)
    wanted = parts["train"] | parts["validation"] | parts["sample"] | parts["domain"]
    missing = wanted - set(src_tasks)
    assert not missing, f"{len(missing)} task ids do not reproduce from the source data"
    tags = {}
    for p in names:
        for t in parts[p]:
            tags.setdefault(t, []).append(("gepa-1/" if p in ("train", "validation") else "eval-1/") + p)
    task_rows = []
    for t in sorted(wanted):
        r = dict(src_tasks[t]); r["splits"] = sorted(tags[t]); task_rows.append(r)
    jsonl_write(task_rows, NEW / "tasks" / "tasks.jsonl")
    jdump(provenance("tasks", "task registry", b, [C["task_source"]],
                     {"tasks": len(task_rows), "by_split": {k: len(v) for k, v in parts.items()}},
                     {"every_task_id_recomputed_from_source_record": True, "disjoint_splits": True},
                     {"id_recipe": "<benchmark>:<source key or id>:<first 20 hex of sha256 of the sorted-key JSON of the full source record>"}),
          NEW / "tasks" / "provenance.json")
    gold_desc = ("`gold.instruction_id_list` and `gold.kwargs`: the constraints the official checker verifies" if b == "ifbench"
                 else "`gold.answer` and `gold.supporting_facts`: the official answer and the sentences that support it")
    (NEW / "tasks" / "README.md").write_text(f"""# tasks — the {C['title']} task registry

One row per task. Gold-bearing: this is the only place gold lives.

| field | meaning |
|---|---|
| `task_id` | `{b}:<key>:<hash>`, the id the artifact's runner assigned; recomputed here from the source record and verified |
| `inputs` | what the program is given |
| `gold` | {gold_desc} |
| `source` | where the record comes from |
| `splits` | which split portions the task belongs to, as `split/portion` |

{len(task_rows)} tasks: {len(train)} train and {len(val)} validation (`gepa-1`), {len(sample)} sample and
{len(domain)} domain (`eval-1`). The source has more tasks than these; the registry
holds every task any stored capture references and grows as captures are added.
""")

    # ---------------- program ----------------
    log("program")
    prog = NEW / "program"; prog.mkdir(parents=True)
    if C["structure"]:
        shutil.copyfile(C["structure"], prog / "structure.json")
    mods = "\n".join(f"| `{m}` | {d} |" for m, d in C["modules"])
    (prog / "README.md").write_text(f"""# program — the {C['title']} program every candidate runs

All 12 candidates are the same program with different instructions:
{C['program_name']}, from the pinned gepa-artifact.

| module | what it does |
|---|---|
{mods}

A candidate is the instruction text for each module (see `../candidates/`). A
trace of one run records each module's inputs and outputs in order.

{"`structure.json` is the machine-readable description both instruments read: trace format, turn markers, modules and roles. Copied verbatim from `runs/taxgen-v2/structures/" + b + ".json`." if C["structure"] else "No structure file exists for this program yet; the earlier taxonomy pipeline inferred the structure from the traces. One is needed before the current taxonomy generator or judge can be run here."}

Gold: {C['metric']}.
""")
    jdump(provenance("program", "program structure", b, [str(C["structure"].relative_to(REPO))] if C["structure"] else [],
                     {"modules": len(C["modules"])}, {"copied_verbatim": bool(C["structure"])}), prog / "provenance.json")

    # ---------------- candidates ----------------
    log("candidates")
    pool = jload(OLD / "pools" / "pool-1" / "candidates.json")
    comps = pool["candidates"]; vals = pool["val_aggregate_scores"]; best = pool["best_idx"]
    assert len(comps) == len(vals) == 12
    run_src = TRIAL / "runs" / f"{b}_g31lite_g36_seed0_representative_v3"
    run_cands = jload(run_src / "gepa_run" / "candidates.json")
    rc = run_cands["candidates"] if isinstance(run_cands, dict) else run_cands
    assert [json.dumps(c.get("components", c), sort_keys=True) for c in rc] == [json.dumps(c, sort_keys=True) for c in comps], "pool-1 != optimizer run candidates"
    registry, idx_to_cid = [], {}
    for i, c in enumerate(comps):
        cid = cid_of(c); idx_to_cid[i] = cid
        registry.append({"candidate_id": cid, "alias": f"cand-{i:02d}", "benchmark": b, "program": C["program_name"],
                         "components": c, "component_sha256": sha256_bytes(json.dumps(c, sort_keys=True).encode()),
                         "val_score": vals[i], "optimizer_best": i == best, "seed_program": i == 0,
                         "origin": {"run": "gepa-1", "candidate_index": i,
                                    "note": "one of the 12 candidates the optimizer tracked; accept/reject and lineage were not harvested for this pool"},
                         "legacy": {"pool": "pool-1", "candidate_index": i, "report_number": i + 1}})
    assert len({r["candidate_id"] for r in registry}) == 12
    registry.sort(key=lambda r: r["candidate_id"])
    jsonl_write(registry, NEW / "candidates" / "registry.jsonl")
    jdump(provenance("candidates", "candidate registry", b, [f"benchmarks/{b}/pools/pool-1/candidates.json"],
                     {"candidates": 12}, {"ids_unique": True, "components_match_optimizer_run": True}), NEW / "candidates" / "provenance.json")
    jdump({"set_id": "pool-1", "benchmark": b, "candidate_ids": sorted(idx_to_cid.values()),
           "aliases": {cid: f"cand-{i:02d}" for i, cid in idx_to_cid.items()},
           "rule": "all 12 candidates the optimizer tracked, including the unmodified seed program (cand-00)",
           "legacy": f"benchmarks/{b}/pools/pool-1"}, NEW / "candidates" / "sets" / "pool-1.json")
    (NEW / "candidates" / "sets" / "README.md").write_text("""# sets — named lists of candidate ids

| set | size | rule |
|---|---:|---|
| `pool-1` | 12 | every candidate the optimizer tracked, including the unmodified seed program |
""")
    (NEW / "candidates" / "README.md").write_text(f"""# candidates — the {C['title']} candidate registry

One row per candidate in `registry.jsonl`. A candidate is the instruction text
for each module of the program.

| field | meaning |
|---|---|
| `candidate_id` | `cnd-` plus the first 12 hex of the sha256 of the components (sorted-key JSON) |
| `alias` | `cand-00` to `cand-11`; the artifact's own index. Reports of the earlier trial numbered them 1 to 12 |
| `components` | the instruction texts, keyed by module |
| `val_score` | the optimizer's validation aggregate on `splits/gepa-1` |
| `optimizer_best` | the candidate the optimizer judged best |
| `seed_program` | true for `cand-00`, the unmodified program |

The optimizer stopped when 12 candidates had been tracked; which were accepted
onto its frontier and which rejected was not harvested for this pool, unlike
HoVer's. `runs/gepa-1/` holds the run that produced them.
""")
    rd = NEW / "candidates" / "runs" / "gepa-1"; rd.mkdir(parents=True)
    for n in ("gepa_result.json", "run_config.json", "split_manifest.json", "usage.json", "launcher.log"):
        if (run_src / n).exists(): shutil.copyfile(run_src / n, rd / n)
    if (run_src / "usage_launches").exists(): shutil.copytree(run_src / "usage_launches", rd / "usage_launches")
    subprocess.run(["tar", "-czf", str(rd / "gepa_run.tar.gz"), "-C", str(run_src), "gepa_run"], check=True)
    pp = jload(OLD / "pools" / "pool-1" / "provenance.json")
    jdump(provenance("gepa-1", "optimizer run", b, [str(run_src.relative_to(REPO))], {"candidates_tracked": 12},
                     {"copied_whole": True, "candidates_match_pool": True}, {"optimizer": pp["produced_by"], "split": "gepa-1"}),
          rd / "provenance.json")
    (rd / "README.md").write_text(f"""# gepa-1 — the optimizer run that produced the candidates

GEPA 0.1.4 on split `gepa-1`, task model `{TASK_MODEL}`, reflection model
`gemini/gemini-3.6-flash`, Pareto selection, merge disabled, stopped when 12
tracked candidates were recorded. Run 2026-08-25 as
`legacy/trials/2026-08-25-gepa-cross-benchmark-candidates/runs/{b}_g31lite_g36_seed0_representative_v3`;
copied here on {TODAY}.

| file | what it is |
|---|---|
| `gepa_result.json` | the optimizer's result object: candidates, validation aggregates, best index |
| `run_config.json`, `split_manifest.json` | settings and the split it saw |
| `usage.json`, `usage_launches/`, `launcher.log` | cost, call counts, log |
| `gepa_run.tar.gz` | the optimizer's working directory, archived whole |

An earlier run of the same launcher (`{b}_g31lite_g36_seed0_v1`) is invalid and
was stopped: it drew the first 100 records of an ordered pool. It is not copied.
""")

    # ---------------- captures ----------------
    log("captures")
    outcomes_old = jload(OLD / "outcomes" / "outcomes-1" / "outcomes.json")
    task_of_stage_input = "prompt" if b == "ifbench" else "question"

    def corpus_lookup(sub):
        d = TR / sub
        if not d.exists(): return {}
        out = {}
        for f in d.glob("*.json"):
            c = jload(f); out[c["trace_id"]] = c
        return out

    def strip_view(corpus):
        meta = dict(corpus["metadata"]); stripped = [k for k in STRIP_FROM_JUDGE_VIEW if k in meta]
        for k in stripped: meta.pop(k)
        return {"messages": corpus["messages"], "metadata": meta}, stripped

    def write_capture(cap, bodies_by_cid, manifest_extra, readme_title, readme_body, outcome_rows, derives, audits_extra=None):
        d = NEW / "traces" / cap; (d / "bodies").mkdir(parents=True)
        index_rows, meta, statuses, gold_hits = [], {}, Counter(), 0
        for cid in sorted(bodies_by_cid):
            rows = sorted(bodies_by_cid[cid], key=lambda x: (x["task_id"], x["repeat"]))
            out = d / "bodies" / f"{cid}.jsonl.gz"
            with gzip.open(out, "wt", compresslevel=6, encoding="utf-8") as f:
                for x in rows:
                    if scan_gold_keys(x): gold_hits += 1
                    statuses[x["status"]] += 1
                    line = json.dumps(x, sort_keys=True, ensure_ascii=False); f.write(line + "\n")
                    index_rows.append({"trace_id": x["trace_id"], "candidate_id": cid, "task_id": x["task_id"], "repeat": x["repeat"],
                                       "status": x["status"], "body_sha256": sha256_bytes(line.encode())})
            meta[cid] = {"file": f"bodies/{cid}.jsonl.gz", "rows": len(rows), "sha256": sha256_file(out)}
        assert not gold_hits, f"{cap}: gold-bearing keys in {gold_hits} bodies"
        keys = [(r["candidate_id"], r["task_id"], r["repeat"]) for r in index_rows]
        assert len(keys) == len(set(keys)), f"{cap}: duplicate (candidate, task, repeat)"
        index_rows.sort(key=lambda r: (r["candidate_id"], r["task_id"], r["repeat"]))
        jsonl_write(index_rows, d / "index.jsonl")
        audits = {"candidate_task_repeat_unique": True, "no_gold_keys_in_bodies": True, "tasks_within_split_portions": True}
        if audits_extra: audits.update(audits_extra)
        man = {"capture_id": cap, "benchmark": b, "candidate_set": "pool-1", "candidate_ids": sorted(idx_to_cid.values()),
               "solver": {"model": TASK_MODEL}, "program": C["program_name"], "present_traces": len(index_rows),
               "status_counts": dict(statuses), "bodies": meta, "audits": audits, "derives_from": derives}
        man.update(manifest_extra)
        jdump(man, d / "manifest.json")
        jdump(provenance(cap, "trace capture", b, derives, {"traces": len(index_rows), "candidates": len(meta)}, audits), d / "provenance.json")
        (d / "README.md").write_text(f"# {cap} — {readme_title}\n\n{readme_body}")
        if outcome_rows is not None:
            outcome_rows.sort(key=lambda r: (r["candidate_id"], r["task_id"], r["repeat"]))
            jsonl_write(outcome_rows, NEW / "outcomes" / f"{cap}.jsonl")
            per = {}
            for r in outcome_rows: per.setdefault(r["candidate_id"], []).append(r["score"])
            jdump(provenance(f"outcomes/{cap}", "gold outcomes", b, [f"data/{b}/traces/{cap}", f"benchmarks/{b}/outcomes/outcomes-1/outcomes.json"],
                             {"records": len(outcome_rows), "mean_score_by_candidate": {c: round(sum(v) / len(v), 4) for c, v in sorted(per.items())}},
                             {"copied_from_recorded_scores": True, "equals_outcomes_1_on_every_trace": True},
                             {"scorer": C["metric"], "note": "scores are the runner's recorded metric values; the official checker is not re-run here"}),
                  NEW / "outcomes" / f"{cap}.provenance.json")
        return len(index_rows)

    # cap-1: the sample, from measurement shards (12 × 100 × 5)
    meas_corpus = corpus_lookup("measurement/corpus")
    bodies, outs, mism, matched_view = {}, [], 0, 0
    for shard in sorted((TR / "measurement" / "records").glob("*.json")):
        sh = jload(shard); cidx, rep = int(sh["candidate_idx"]), int(sh["repeat"]); cid = idx_to_cid[cidx]
        assert sh["task_count"] == len(sh["records"]) == 100
        for r in sh["records"]:
            tid = r["task_id"]; assert tid in parts["sample"], f"{tid} not in sample"
            trid = trace_id(b, cidx, tid, rep)
            body = {"trace_id": trid, "benchmark": b, "capture": "cap-1", "candidate_id": cid, "task_id": tid, "repeat": rep,
                    "status": "parse_failed" if r.get("parse_failed") else "ok",
                    "solver": {"models": [TASK_MODEL], "n_stages": len(r["trace"])},
                    "input": {task_of_stage_input: r["trace"][0]["inputs"].get(task_of_stage_input if b == "hotpotqa" else "query")} if r["trace"] else {},
                    "prediction": r["prediction"], "stages": r["trace"],
                    "legacy": {"candidate_index": cidx, "shard": f"{TR.relative_to(REPO)}/measurement/records/{shard.name}"}}
            if trid in meas_corpus:
                body["judge_view"], stripped = strip_view(meas_corpus[trid]); body["judge_view"]["stripped_keys"] = stripped; matched_view += 1
            bodies.setdefault(cid, []).append(body)
            old = float(outcomes_old["measurement"][str(cidx)][str(rep)][tid])
            if old != float(r["score"]): mism += 1
            outs.append({"candidate_id": cid, "task_id": tid, "repeat": rep, "trace_id": trid, "score": float(r["score"]), "capture": "cap-1"})
    assert mism == 0, f"cap-1: {mism} shard scores differ from outcomes-1"
    assert matched_view == len(meas_corpus), "cap-1: some measurement corpus traces did not match a body"
    n1 = write_capture("cap-1", bodies,
                       {"split": "eval-1", "portions": ["sample"], "task_count": 100, "repeats": [0, 1, 2, 3, 4],
                        "expected_traces": 6000, "captured_on": "2026-08-26",
                        "judge_view_present_for": f"{matched_view} traces (repeat 0) from the source's judge-facing corpus" if matched_view else "none; the earlier judge read the stage records directly",
                        "stripped_from_judge_view": list(STRIP_FROM_JUDGE_VIEW),
                        "runner": jload(TR / "provenance.json")["produced_by"]},
                       "pool-1 on the sample portion, five runs each",
                       f"""12 candidates × 100 tasks (split `eval-1`, portion `sample`) × 5 repeats = 6,000
traces. Solver `{TASK_MODEL}`. Repeats are independent samples from the
provider's default sampler, not seeded replicates; caching was disabled, so they
genuinely re-execute. Captured 2026-08-26 as `{TR.relative_to(REPO)}/measurement`;
duplicated here on {TODAY}, re-keyed to the registries.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what is present, audit results |
| `index.jsonl` | one row per trace: ids, status, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces, one candidate per file, one trace per line |

A body holds each module's inputs and outputs in order (`stages`), the final
`prediction`, and, where the source produced one, the outcome-blind message
list a judge reads (`judge_view`). The runner's per-trace score is not in the
body; it is in `../../outcomes/cap-1.jsonl`. Trace ids follow the source's own
recipe, so anything the earlier trial recorded against these traces can be
looked up by the same id.
""",
                       outs, [f"{TR.relative_to(REPO)}/measurement", f"benchmarks/{b}/pools/pool-1", f"benchmarks/{b}/splits/split-1"],
                       {"shard_scores_equal_outcomes_1": True, "judge_view_ids_match_bodies": True})

    caps_written = ["cap-1"]
    # domain capture (hotpotqa only): judge-view-only bodies from the generalization corpus
    if C["domain_corpus"]:
        dom = corpus_lookup(C["domain_corpus"]); bodies, outs, mism = {}, [], 0
        for trid, c in dom.items():
            m = c["metadata"]; cidx, tid, rep = int(m["candidate_index"]), m["task_source_id"], int(m["evaluation_repeat"])
            assert tid in parts["domain"] and trace_id(b, cidx, tid, rep) == trid
            cid = idx_to_cid[cidx]; view, stripped = strip_view(c); view["stripped_keys"] = stripped
            bodies.setdefault(cid, []).append({"trace_id": trid, "benchmark": b, "capture": "cap-2", "candidate_id": cid, "task_id": tid,
                                               "repeat": rep, "status": "ok", "solver": {"models": [TASK_MODEL]},
                                               "judge_view": view, "legacy": {"candidate_index": cidx, "source": f"{TR.relative_to(REPO)}/{C['domain_corpus']}"}})
            old = float(outcomes_old["generalization"][str(cidx)][str(rep)][tid])
            if old != float(m["outcome_score"]): mism += 1
            outs.append({"candidate_id": cid, "task_id": tid, "repeat": rep, "trace_id": trid, "score": old, "capture": "cap-2"})
        assert mism == 0
        write_capture("cap-2", bodies, {"split": "eval-1", "portions": ["domain"], "task_count": C["domain_size"], "repeats": [0],
                                        "expected_traces": 12 * C["domain_size"], "captured_on": "2026-08-27",
                                        "body_form": "judge view only: the source kept the outcome-blind message list and not the stage records",
                                        "stripped_from_judge_view": list(STRIP_FROM_JUDGE_VIEW)},
                      "pool-1 on the domain portion, one run each, judge view only",
                      f"""12 candidates × {C['domain_size']} tasks (split `eval-1`, portion `domain`) × 1 repeat =
{12 * C['domain_size']:,} traces. Solver `{TASK_MODEL}`. The source kept only the
outcome-blind message list for these runs, so each body carries a `judge_view`
and no stage record. The recorded scores are in `../../outcomes/cap-2.jsonl`;
the `outcome_score` the source stored beside each message list was removed.
Source: `{TR.relative_to(REPO)}/{C['domain_corpus']}`.
""", outs, [f"{TR.relative_to(REPO)}/{C['domain_corpus']}", f"benchmarks/{b}/outcomes/outcomes-1"],
                      {"corpus_metadata_scores_equal_outcomes_1": True, "trace_ids_match_recipe": True})
        caps_written.append("cap-2")
    else:
        # ifbench: domain runs exist as scores only
        rows = []
        for cidx in range(12):
            for tid, sc in outcomes_old["generalization"][str(cidx)]["0"].items():
                assert tid in parts["domain"]
                rows.append({"candidate_id": idx_to_cid[cidx], "task_id": tid, "repeat": 0, "trace_id": None, "score": float(sc), "capture": None})
        rows.sort(key=lambda r: (r["candidate_id"], r["task_id"]))
        jsonl_write(rows, NEW / "outcomes" / "eval-1-domain-uncaptured.jsonl")
        jdump(provenance("outcomes/eval-1-domain-uncaptured", "gold outcomes without traces", b, [f"benchmarks/{b}/outcomes/outcomes-1/outcomes.json"],
                         {"records": len(rows)}, {"tasks_within_domain": True},
                         {"scorer": C["metric"], "note": "12 candidates × 194 domain tasks × 1 run were executed and scored, but the runner did not record their traces; there is no capture for them. A capture on this portion is still to be made."}),
              NEW / "outcomes" / "eval-1-domain-uncaptured.provenance.json")

    # induction corpus: 300 judge-view traces on gepa-1 train tasks
    gen = corpus_lookup("generation/corpus"); cap_gen = "cap-2" if b == "ifbench" else "cap-3"
    bodies, outs = {}, []
    for trid, c in gen.items():
        m = c["metadata"]; cidx, tid, rep = int(m["candidate_index"]), m["task_source_id"], int(m["evaluation_repeat"])
        assert tid in parts["train"], f"induction trace {trid} not on a train task"
        assert trace_id(b, cidx, tid, rep) == trid
        cid = idx_to_cid[cidx]; view, stripped = strip_view(c); view["stripped_keys"] = stripped
        bodies.setdefault(cid, []).append({"trace_id": trid, "benchmark": b, "capture": cap_gen, "candidate_id": cid, "task_id": tid, "repeat": rep,
                                           "status": "ok", "solver": {"models": [TASK_MODEL]}, "judge_view": view,
                                           "legacy": {"candidate_index": cidx, "source": f"{TR.relative_to(REPO)}/generation/corpus"}})
        outs.append({"candidate_id": cid, "task_id": tid, "repeat": rep, "trace_id": trid, "score": float(m["outcome_score"]), "capture": cap_gen})
    gen_tasks = {c["metadata"]["task_source_id"] for c in gen.values()}
    write_capture(cap_gen, bodies, {"split": "gepa-1", "portions": ["train"], "task_count": len(gen_tasks), "repeats": [0],
                                    "expected_traces": len(gen), "captured_on": "2026-08-26",
                                    "body_form": "judge view only", "stripped_from_judge_view": list(STRIP_FROM_JUDGE_VIEW),
                                    "role": "the corpus the earlier pipeline's taxonomy was induced from"},
                  "the taxonomy-induction corpus",
                  f"""{len(gen)} traces of the 12 candidates on {len(gen_tasks)} tasks of the optimizer's train portion,
one run each, kept in the outcome-blind message form a taxonomy generator
reads. This is the corpus the earlier pipeline's taxonomy was induced from;
that taxonomy is archived in `benchmarks/{b}/taxonomies/tax-1` and not carried
here. The tasks
were seen by the optimizer, which is why they and not the evaluation tasks were
spent on induction. Scores recorded beside the source traces are in
`../../outcomes/{cap_gen}.jsonl`; the `outcome_score` field was removed from the
message metadata. Source: `{TR.relative_to(REPO)}/generation/corpus`.
""", outs, [f"{TR.relative_to(REPO)}/generation/corpus", f"benchmarks/{b}/pools/pool-1"],
                  {"tasks_within_gepa_1_train": True, "trace_ids_match_recipe": True})
    caps_written.append(cap_gen)
    rows_tbl = []
    for p in sorted((NEW / "outcomes").glob("*.jsonl")):
        rows_tbl.append(f"| `{p.stem}` | {sum(1 for _ in open(p))} |")
    (NEW / "outcomes" / "README.md").write_text(f"""# outcomes — gold scores per run

One file per capture, one row per trace: `candidate_id`, `task_id`, `repeat`,
`trace_id`, `score`. Scores are the runner's recorded values of the official
metric ({C['metric']}); they were checked equal to the earlier outcome table on
every trace. Each file has a `.provenance.json` beside it.
{"`eval-1-domain-uncaptured.jsonl` holds scores of runs whose traces were not recorded; it has no capture." if b == "ifbench" else ""}

Gold-bearing by construction. A scoring path that claims to be free of gold must
not read this directory.

| file | records |
|---|---:|
""" + "\n".join(rows_tbl) + "\n")

    # ---------------- benchmark README ----------------
    log("readme")
    (NEW / "README.md").write_text(f"""# {b}

{C['title']}, from the pinned gepa-artifact (commit `cbefbc1a…`). Program:
{C['program_name']}. Gold: {C['metric']}.

## Identities

| thing | id | where defined |
|---|---|---|
| task | `{b}:<key>:<hash>`, the artifact runner's id | `tasks/tasks.jsonl` |
| candidate | `cnd-` + first 12 hex of sha256 of its components | `candidates/registry.jsonl` |
| trace | (candidate, task, repeat); `trace_id` = first 24 hex of sha256 of `{b}|<index>|<task>|<repeat>`, the source's own recipe | `traces/<capture>/index.jsonl` |
| capture | `cap-N` | `traces/cap-N/manifest.json` |
| split | `gepa-1`, `eval-1` | `splits/<id>/split.json` |

## Layout

```
tasks/            registry with gold                              {len(task_rows)} tasks
program/          the program every candidate runs{" (with structure.json)" if C["structure"] else " (no structure file yet)"}
candidates/       registry of 12; sets/pool-1; runs/gepa-1 (the optimizer run)
splits/gepa-1/    train 100 + validation 100                       what the optimizer saw
splits/eval-1/    sample 100 + domain {C['domain_size']}                       the artifact's test set
traces/cap-1/     pool-1 × sample × 5 repeats                      6,000 traces with stage records
{"traces/cap-2/     pool-1 × domain × 1                              " + f"{12*C['domain_size']:,} traces, judge view only" if C["domain_corpus"] else "traces/cap-2/     induction corpus on gepa-1 train                  300 traces, judge view only"}
outcomes/         recorded gold scores per capture
{"traces/cap-3/     induction corpus on gepa-1 train                  300 traces, judge view only" if C["domain_corpus"] else "outcomes/eval-1-domain-uncaptured.jsonl   12 × 194 domain scores whose traces were never recorded"}
```

No taxonomy or mapping yet: the current generator and judge have not been run
here.

## What is here and what is not

Migrated on {TODAY} from `benchmarks/{b}` and the trial directory
`legacy/trials/2026-08-25-gepa-cross-benchmark-candidates`, all left untouched.
{"Domain traces exist only in judge-view form; the runner did not keep stage records for them." if C["domain_corpus"] else "The 194 domain tasks were run once per candidate and scored, but their traces were not recorded, so there is no domain capture yet; capturing one is the first thing this benchmark needs."}
Not carried over: the earlier pipeline's taxonomy (`benchmarks/{b}/taxonomies/tax-1`)
and its judge mapping (`benchmarks/{b}/mappings/mapping-1`). They were made
with a different instrument, stay where they are as the archive, and are not
evidence for anything built here.

## Rules

- `traces/` and `mappings/` never contain gold; each capture and mapping is
  scanned for gold-bearing keys and the result recorded in its manifest.
- The tasks in `splits/gepa-1` were seen by the optimizer. `eval-1` `domain`
  is only ever the target.
- Nothing is edited in place. A changed split, set, capture, taxonomy or
  mapping is a new id.

## Verification

```
python3 data/scripts/audit_capture.py {b} cap-1
```
""")
    log(f"done: {b} tasks {len(task_rows)} captures {caps_written} cap-1 traces {n1}")


if __name__ == "__main__":
    main()
