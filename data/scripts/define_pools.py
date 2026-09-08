#!/usr/bin/env python3
"""Define the master partition `pools-1` for hover, ifbench and hotpotqa: three
pools, taxonomy / judging / generalization, from which every later study draws
and which nothing crosses. Existing captured tasks keep their roles: the
optimizer's tasks go to taxonomy, eval-1 sample to judging, eval-1 domain to
generalization; the remaining pool sizes are filled by a seeded, stratified draw
from tasks that were never run.

Run with an interpreter that has `datasets` (HoVer is reloaded from the local
Hugging Face cache, offline):
    HF_DATASETS_OFFLINE=1 HF_HUB_OFFLINE=1 <venv>/bin/python data/scripts/define_pools.py

Also grows each task registry to cover every task the pools reference. Refuses
to overwrite an existing pools-1.
"""
from __future__ import annotations
import collections, hashlib, json, random, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TRIAL = REPO / "legacy" / "trials" / "2026-08-25-gepa-cross-benchmark-candidates"
IFB = TRIAL / "vendor" / "gepa-artifact" / "gepa_artifact" / "benchmarks" / "IFBench" / "data"
TODAY = "2026-09-06"; SEED = 2026
SCRIPT = "data/scripts/define_pools.py"
TARGETS = {"hover": {"taxonomy": 600, "judging": 500}, "ifbench": {"taxonomy": 300, "judging": 500}, "hotpotqa": {"taxonomy": 200, "judging": 150, "generalization": 400}}

def jload(p): return json.load(open(p))
def jdump(o, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f: json.dump(o, f, indent=2, sort_keys=True, ensure_ascii=False); f.write("\n")
def jsonl(p): return [json.loads(l) for l in open(p) if l.strip()]
def jsonl_write(rows, p):
    with open(p, "w") as f:
        for r in rows: f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
def sha(s): return hashlib.sha256(s.encode()).hexdigest()

def stratified_draw(rows, key, k, rng):
    """Draw k rows keeping the strata in their natural proportions (largest remainder)."""
    strata = collections.defaultdict(list)
    for r in rows: strata[key(r)].append(r)
    for s in strata.values(): s.sort(key=lambda r: r["task_id"]); rng.shuffle(s)
    total = len(rows); quota = {s: k * len(v) / total for s, v in strata.items()}
    take = {s: int(q) for s, q in quota.items()}
    for s in sorted(strata, key=lambda s: -(quota[s] - take[s]))[: k - sum(take.values())]: take[s] += 1
    drawn = [r for s, v in strata.items() for r in v[:take[s]]]
    rest = [r for s, v in strata.items() for r in v[take[s]:]]
    return drawn, rest

def example_id(bench, ex):
    payload = json.dumps(ex, ensure_ascii=False, sort_keys=True); dg = sha(payload)[:20]
    for k in ("id", "_id", "key"):
        if ex.get(k) is not None: return f"{bench}:{ex[k]}:{dg}"
    return f"{bench}:sha256:{dg}"

# ------------------------------------------------------------- universes -- #
def hover_universe():
    from datasets import load_dataset
    ds = load_dataset("hover-nlp/hover", split="train", trust_remote_code=True)
    rows = {}
    for i, row in enumerate(ds):
        facts = row.get("supporting_facts") or []
        titles = [f[0] if isinstance(f, (list, tuple)) else f.get("key") for f in facts]
        tset = sorted({t for t in titles if t})
        if len(tset) != 3: continue
        rows[row["uid"]] = {"task_id": row["uid"], "benchmark": "hover", "claim": row["claim"], "label": row["label"],
                            "gold": {"supporting_titles": tset},
                            "source": {"dataset": "hover-nlp/hover", "dataset_split": "train", "source_index": i,
                                       "claim_sha256": sha(row["claim"]), "filter": "exactly three distinct supporting titles"},
                            "_stratum": str(row["label"])}
    assert len(rows) == 6084, len(rows)
    return rows

def ifbench_universe():
    train = [json.loads(l) for l in open(IFB / "IFBench_train.jsonl") if l.strip()]
    test = [json.loads(l) for l in open(IFB / "IFBench_test.jsonl") if l.strip()]
    rows = {}
    for fname, part, recs in (("IFBench_test.jsonl", "test", test), ("IFBench_train.jsonl", "train", train)):
        for ex in recs:
            tid = example_id("ifbench", ex)
            rows[tid] = {"task_id": tid, "benchmark": "ifbench", "inputs": {"prompt": ex["prompt"]},
                         "gold": {"instruction_id_list": ex["instruction_id_list"], "kwargs": ex["kwargs"]},
                         "source": {"dataset": "IFBench (allenai)", "file": f"gepa-artifact/benchmarks/IFBench/data/{fname}", "part": part,
                                    "key": ex["key"], "artifact_commit": "cbefbc1aa0f43dd39874ec4bf42211365dbda42e"},
                         "_stratum": str(len(ex["instruction_id_list"])), "_n": len(ex["instruction_id_list"])}
    return rows

def hotpotqa_universe():
    snap = jload(TRIAL / "inputs" / "hotpotqa_official_snapshot.json"); rows = {}
    for part in ("train", "validation", "evaluation"):
        for ex in snap[part]:
            tid = example_id("hotpotqa", ex)
            rows[tid] = {"task_id": tid, "benchmark": "hotpotqa", "inputs": {"question": ex["question"]},
                         "gold": {"answer": ex["answer"], "supporting_facts": ex["supporting_facts"]},
                         "source": {"dataset": "hotpot_qa fullwiki", "snapshot": "legacy/trials/2026-08-25-gepa-cross-benchmark-candidates/inputs/hotpotqa_official_snapshot.json",
                                    "part": part, "id": ex["id"], "level": ex.get("level"), "type": ex.get("type"), "artifact_commit": snap["artifact_commit"],
                                    "note": "the task id hashes the full snapshot record including its distractor context paragraphs; the context is not copied here"},
                         "_stratum": f"{ex.get('level')}/{ex.get('type')}"}
    return rows

# ------------------------------------------------------------------ main -- #
def define(bench, universe, rng):
    D = REPO / "data" / bench
    if (D / "splits" / "pools-1").exists(): sys.exit(f"{bench}: pools-1 already exists; splits are append-only")
    reg = {r["task_id"]: r for r in jsonl(D / "tasks" / "tasks.jsonl")}
    gepa = jload(D / "splits" / "gepa-1" / "split.json"); ev = jload(D / "splits" / "eval-1" / "split.json")
    seen = set(gepa["portions"]["train"]) | set(gepa["portions"]["validation"])
    sample, domain = set(ev["portions"]["sample"]), set(ev["portions"]["domain"])
    assert seen <= set(universe) and sample <= set(universe) and domain <= set(universe)
    fixed = {"taxonomy": set(seen), "judging": set(sample), "generalization": set(domain)}
    reservoir = [r for t, r in universe.items() if t not in seen | sample | domain]
    filters = {}
    if bench == "ifbench":
        filters["constraint_count"] = "fills drawn only from tasks with one or two constraints, the range the test set covers"
        reservoir = [r for r in reservoir if r["_n"] in (1, 2)]
    reservoir.sort(key=lambda r: r["task_id"])
    key = lambda r: r["_stratum"]
    T = TARGETS[bench]; pools = {k: set(v) for k, v in fixed.items()}; composition = {}
    for pool in ("taxonomy", "judging"):
        need = T[pool] - len(pools[pool]); assert need >= 0
        drawn, reservoir = stratified_draw(reservoir, key, need, rng)
        pools[pool] |= {r["task_id"] for r in drawn}
        composition[pool] = {"kept_from_existing_splits": len(fixed[pool]), "newly_drawn": len(drawn)}
    if "generalization" in T:
        need = T["generalization"] - len(pools["generalization"]); drawn, reservoir = stratified_draw(reservoir, key, need, rng)
        pools["generalization"] |= {r["task_id"] for r in drawn}
        composition["generalization"] = {"kept_from_existing_splits": len(fixed["generalization"]), "newly_drawn": len(drawn), "left_unassigned": len(reservoir)}
    else:
        pools["generalization"] |= {r["task_id"] for r in reservoir}
        composition["generalization"] = {"kept_from_existing_splits": len(fixed["generalization"]), "newly_drawn": len(reservoir), "left_unassigned": 0}; reservoir = []
    names = list(pools)
    for i, x in enumerate(names):
        for y in names[i + 1:]: assert not pools[x] & pools[y]
    strata = {p: dict(collections.Counter(universe[t]["_stratum"] for t in v)) for p, v in pools.items()}
    split = {"benchmark": bench, "split_id": "pools-1", "purpose": "master partition: every later study draws its tasks from inside one pool and nothing crosses pools",
             "portions": {p: sorted(v) for p, v in pools.items()}, "sizes": {p: len(v) for p, v in pools.items()},
             "seed": SEED, "protocol": "existing split portions keep their roles (gepa-1 -> taxonomy, eval-1 sample -> judging, eval-1 domain -> generalization); remaining sizes filled by a seeded draw from never-run tasks, stratified by " + ("label" if bench == "hover" else "constraint count" if bench == "ifbench" else "level/type"),
             "filters": filters, "composition": composition, "stratum_counts": strata,
             "contains": {"gepa-1": "taxonomy", "eval-1/sample": "judging", "eval-1/domain": "generalization"},
             "rule": "pool sizes are ceilings; a study may use fewer tasks, always drawn from the pool made for its purpose; tasks the optimizer saw are only ever in the taxonomy pool"}
    jdump(split, D / "splits" / "pools-1" / "split.json")
    jdump({"id": "pools-1", "kind": "task split", "benchmark": bench, "created": TODAY,
           "derives_from": [f"data/{bench}/splits/gepa-1", f"data/{bench}/splits/eval-1"] + (["hover-nlp/hover train split, reloaded from the local cache"] if bench == "hover" else [f"IFBench_test.jsonl and IFBench_train.jsonl (gepa-artifact)"] if bench == "ifbench" else ["inputs/hotpotqa_official_snapshot.json"]),
           "produced_by": {"script": SCRIPT, "command": f"python3 {SCRIPT}", "seed": SEED}, "counts": split["sizes"],
           "checks": {"pools_disjoint": True, "existing_portions_contained": True, "optimizer_seen_only_in_taxonomy": True}}, D / "splits" / "pools-1" / "provenance.json")
    # registry: union, existing rows unchanged except hover title dedup, plus pools-1 tags
    fixed_titles = 0; added = 0
    for t in set().union(*pools.values()):
        pool = next(p for p, v in pools.items() if t in v)
        if t in reg:
            row = reg[t]
            if bench == "hover":
                dedup = sorted(set(row["gold"]["supporting_titles"]))
                if dedup != row["gold"]["supporting_titles"]: row["gold"]["supporting_titles"] = dedup; fixed_titles += 1
                assert dedup == universe[t]["gold"]["supporting_titles"]
        else:
            row = {k: v for k, v in universe[t].items() if not k.startswith("_")}; row["splits"] = []; reg[t] = row; added += 1
        row["splits"] = sorted(set(row.get("splits", [])) | {f"pools-1/{pool}"})
    rows = [reg[t] for t in sorted(reg)]
    jsonl_write(rows, D / "tasks" / "tasks.jsonl")
    prov = jload(D / "tasks" / "provenance.json"); prov["counts"]["tasks"] = len(rows)
    prov["counts"]["by_split_tag"] = dict(collections.Counter(t for r in rows for t in r["splits"]))
    prov.setdefault("amendments", []).append({"date": TODAY, "by": SCRIPT, "added_tasks": added, "note": "registry grown to cover pools-1; every row tagged with its pool" + (f"; {fixed_titles} rows had a supporting title listed twice (once per supporting sentence in the source gold files) and were deduplicated, scores unaffected because the metric compares sets" if fixed_titles else "")})
    jdump(prov, D / "tasks" / "provenance.json")
    return split, added, fixed_titles

def main():
    rng = random.Random(SEED); out = {}
    for bench, uni in (("hover", hover_universe), ("ifbench", ifbench_universe), ("hotpotqa", hotpotqa_universe)):
        U = uni(); split, added, fixed = define(bench, U, random.Random(SEED))
        out[bench] = (split, added, fixed, len(U))
        print(f"{bench}: universe {len(U)} | pools {split['sizes']} | composition {json.dumps(split['composition'])} | registry +{added} rows" + (f" | titles deduplicated {fixed}" if fixed else ""))
    json.dump({b: {"sizes": s["sizes"], "composition": s["composition"], "strata": s["stratum_counts"], "universe": n} for b, (s, a, f, n) in out.items()},
              open(REPO / "data" / "scripts" / ".pools-1.summary.json", "w"), indent=1)

if __name__ == "__main__": main()
