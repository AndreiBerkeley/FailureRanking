"""Draw the judged subset of the judging pool: split judging-50-1.

50 tasks from pools-1/judging, seeded within difficulty (16 easy, 17 medium, 17 hard).
Outcome-free: drawn before any candidate ran on the judging pool, so the choice cannot
have looked at gold. Easy gets the short stick because the taxonomy pool showed 39/50
easy tasks solved by every candidate.

    python3 data/livecodebench/scripts/build_judging_subset.py
"""
import json, random, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 2026
PER_TIER = {"easy": 16, "medium": 17, "hard": 17}
SPLIT_ID = "judging-50-1"

master = json.load(open(ROOT / "splits" / "pools-1" / "split.json"))
meta = {json.loads(l)["task_id"]: json.loads(l) for l in open(ROOT / "tasks" / "tasks.jsonl")}
pool = master["portions"]["judging"]

by_tier = defaultdict(list)
for t in pool:
    by_tier[meta[t]["difficulty"]].append(t)
rng = random.Random(SEED)
chosen = []
for tier in ("easy", "medium", "hard"):
    ids = sorted(by_tier[tier]); rng.shuffle(ids)
    chosen += ids[: PER_TIER[tier]]
chosen.sort()
assert len(chosen) == 50 and set(chosen) <= set(pool)

def strata(ids, key): return dict(sorted(Counter(meta[i][key] for i in ids).items()))
split = {
    "benchmark": "livecodebench", "split_id": SPLIT_ID, "seed": SEED,
    "purpose": "the judged subset of the judging pool: candidates run on these, the judge reads those traces",
    "protocol": "16 easy + 17 medium + 17 hard by a seeded draw within difficulty from pools-1/judging; "
                "drawn before any candidate ran on the judging pool",
    "parent": "data/livecodebench/splits/pools-1/split.json#portions.judging",
    "sizes": {"judging": len(chosen)},
    "stratum_counts": {"judging": {"difficulty": strata(chosen, "difficulty"), "platform": strata(chosen, "platform"),
                                   "release": strata(chosen, "release"), "prompt_variant": strata(chosen, "prompt_variant")}},
    "portions": {"judging": chosen},
}
out = ROOT / "splits" / SPLIT_ID; out.mkdir(parents=True, exist_ok=True)
(out / "split.json").write_text(json.dumps(split, indent=2))
(out / "provenance.json").write_text(json.dumps({
    "id": SPLIT_ID, "kind": "split", "benchmark": "livecodebench", "created": "2026-09-11",
    "derives_from": {"split": "data/livecodebench/splits/pools-1/split.json", "portion": "judging",
                     "tasks": "data/livecodebench/tasks/tasks.jsonl"},
    "produced_by": "data/livecodebench/scripts/build_judging_subset.py", "seed": SEED,
    "counts": {"judging": len(chosen), **PER_TIER},
    "checks": {"subset_of_pools-1_judging": True, "outcome_free": "drawn 2026-09-11, before any candidate ran on the judging pool"},
}, indent=2))
s = split["stratum_counts"]["judging"]
(out / "README.md").write_text(f"""# {SPLIT_ID} — the 50 judged tasks of the judging pool

50 tasks drawn from `pools-1/judging` (150), seeded within difficulty, before any candidate
ran on that pool. Easy is under-weighted because the taxonomy pool showed 39 of 50 easy
tasks solved by all nine candidates (no ranking information); medium and hard discriminate.

| difficulty | platform | release | prompt variant |
|---|---|---|---|
| {s['difficulty']} | {s['platform']} | {s['release']} | {s['prompt_variant']} |

Use: `capture.py capture --split {SPLIT_ID} --portion judging ...`. The other 100 judging-pool
tasks stay unused; nothing crosses into taxonomy or generalization.

Built by `scripts/build_judging_subset.py`; the same seed reproduces it exactly.
""")
print("chosen:", len(chosen)); print(json.dumps(s, indent=1))
