"""Build the task registry and the pools-1 split for livecodebench.

Registry: one row per problem, metadata only -- the tests (gold) stay in tasks/raw.
Split: taxonomy 50/50/50 and judging 50/50/50 by difficulty, drawn seeded and
task-disjoint; everything else is generalization.
"""
import json, random, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lcb import iter_problems, RELEASES

ROOT = Path(__file__).resolve().parents[1]
SEED = 2026
PER_TIER = {"taxonomy": 50, "judging": 50}

file_release = {f: v for v, fs in RELEASES.items() for f in fs}
rows = {}
for d in iter_problems():
    if d["question_id"] in rows:
        continue
    rows[d["question_id"]] = {
        "task_id": d["question_id"], "title": d["question_title"], "platform": d["platform"],
        "difficulty": d["difficulty"], "contest_id": d["contest_id"], "contest_date": d["contest_date"],
        "release": file_release[d["_file"]], "has_starter_code": bool(d.get("starter_code")),
        "prompt_variant": "starter_code" if d.get("starter_code") else "stdin",
        "raw_file": d["_file"],
    }
tasks = sorted(rows.values(), key=lambda r: r["task_id"])
(ROOT / "tasks" / "tasks.jsonl").write_text("".join(json.dumps(r) + "\n" for r in tasks))

by_tier = defaultdict(list)
for r in tasks:
    by_tier[r["difficulty"]].append(r["task_id"])
rng = random.Random(SEED)
portions = {"taxonomy": [], "judging": [], "generalization": []}
for tier in ("easy", "medium", "hard"):
    ids = sorted(by_tier[tier]); rng.shuffle(ids)
    k = PER_TIER["taxonomy"]; portions["taxonomy"] += ids[:k]
    j = PER_TIER["judging"]; portions["judging"] += ids[k:k + j]
    portions["generalization"] += ids[k + j:]
for p in portions: portions[p].sort()
assert len(set(portions["taxonomy"]) & set(portions["judging"])) == 0
assert len(set(portions["taxonomy"]) & set(portions["generalization"])) == 0
assert len(set(portions["judging"]) & set(portions["generalization"])) == 0
assert sum(len(v) for v in portions.values()) == len(tasks)

meta = {r["task_id"]: r for r in tasks}
def strata(ids, key): return dict(sorted(Counter(meta[i][key] for i in ids).items()))
split = {
    "benchmark": "livecodebench", "split_id": "pools-1", "seed": SEED,
    "purpose": "master partition: every later study draws its tasks from inside one pool and nothing crosses pools",
    "protocol": "taxonomy and judging each take 50 easy + 50 medium + 50 hard by a seeded draw within "
                "difficulty; every remaining problem is generalization; task-disjoint",
    "rule": "pool sizes are ceilings; a study may use fewer tasks, always drawn from the pool made for its purpose",
    "sizes": {p: len(v) for p, v in portions.items()},
    "stratum_counts": {p: {"difficulty": strata(v, "difficulty"), "platform": strata(v, "platform"),
                           "release": strata(v, "release"), "prompt_variant": strata(v, "prompt_variant")}
                       for p, v in portions.items()},
    "portions": portions,
}
out = ROOT / "splits" / "pools-1"; out.mkdir(parents=True, exist_ok=True)
(out / "split.json").write_text(json.dumps(split, indent=2))
(out / "provenance.json").write_text(json.dumps({
    "id": "pools-1", "kind": "split", "benchmark": "livecodebench", "created": "2026-09-10",
    "derives_from": {"tasks": "data/livecodebench/tasks/tasks.jsonl", "raw": "data/livecodebench/tasks/raw (release_v6)"},
    "produced_by": "data/livecodebench/scripts/build_split.py", "seed": SEED,
    "counts": split["sizes"],
    "checks": {"task_disjoint": True, "covers_all_tasks": True, "per_tier_taxonomy": 50, "per_tier_judging": 50},
}, indent=2))
print(f"tasks.jsonl: {len(tasks)} rows")
print("sizes:", split["sizes"])
for p, v in portions.items():
    s = split["stratum_counts"][p]
    print(f"\n{p:<15} {len(v):>4}  difficulty {s['difficulty']}")
    print(f"{'':<21} platform   {s['platform']}")
    print(f"{'':<21} release    {s['release']}")
    print(f"{'':<21} prompt     {s['prompt_variant']}")
