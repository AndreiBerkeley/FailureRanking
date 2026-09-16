"""models-1-judged-50-b: a second judged 50 for the models-1 set, drawn at random from the
450 judging-pool tasks not in models-1-judged-50, subject to one condition: the nine
candidates' pass counts on the 50 must be as untied as a random draw allows.

Rule: 500 seeded random 50-task draws (random.Random(2026)); keep the draw with the fewest
candidate pairs tied on gold-50 (cap-7 pass counts), ties broken by larger pass-count
spread, then by seed order. Uses cap-7 (judging-pool gold) only; never the generalization
gold (cap-8), which stays a clean target.

    python3 data/hover/scripts/draw_judged_50_b.py
"""
import json, random, itertools
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED, DRAWS, K = 2026, 500, 50

cs = json.load(open(ROOT / "candidates/sets/models-1.json")); active = sorted(cs["active_candidate_ids"])
pool = json.load(open(ROOT / "splits/models-1/split.json"))["portions"]["judging"]
first = set(json.load(open(ROOT / "splits/models-1-judged-50/split.json"))["portions"]["judged"])
avail = sorted(t for t in pool if t not in first); assert len(avail) == 450
gold = defaultdict(dict)
for line in open(ROOT / "outcomes/cap-7.jsonl"):
    r = json.loads(line)
    if r["candidate_id"] in active and r.get("repeat", 0) == 0: gold[r["candidate_id"]][r["task_id"]] = r["score"]

def stats(tasks):
    pc = {c: sum(gold[c][t] for t in tasks) for c in active}
    tied = sum(1 for a, b in itertools.combinations(active, 2) if pc[a] == pc[b])
    return tied, max(pc.values()) - min(pc.values()), pc

rng = random.Random(SEED); best = None
for i in range(DRAWS):
    draw = sorted(rng.sample(avail, K)); tied, spread, pc = stats(draw)
    key = (tied, -spread, i)
    if best is None or key < best[0]: best = (key, draw, pc)
(tied, nspread, i), draw, pc = best
t1, s1, _ = stats(sorted(first))
print(f"first judged 50: {t1} tied pairs, spread {s1}")
print(f"chosen draw #{i}: {tied} tied pairs, spread {-nspread}  pass counts {sorted(pc.values(), reverse=True)}")
out = ROOT / "splits/models-1-judged-50-b"; out.mkdir(exist_ok=True)
(out / "split.json").write_text(json.dumps({
    "split_id": "models-1-judged-50-b", "benchmark": "hover",
    "purpose": "second judged 50 for the models-1 candidate set: 9 models x these tasks x repeat 0 = 450 traces; disjoint from models-1-judged-50",
    "drawn_from": "data/hover/splits/models-1 portion 'judging' (500 tasks) minus models-1-judged-50 (450 tasks)",
    "draw": f"{DRAWS} seeded random 50-task draws (random.Random({SEED})); kept draw #{i}, the one with the fewest candidate pairs tied on cap-7 pass counts ({tied} of 36; the first judged 50 has {t1}), ties broken by pass-count spread ({-nspread} vs {s1}). Condition uses the judging-pool gold only; cap-8 was not read.",
    "portions": {"judged": draw}, "sizes": {"judged": K},
    "gold50_pass_counts": {cs["solver_models"][c]: pc[c] for c in active}}, indent=2))
(out / "provenance.json").write_text(json.dumps({
    "id": "models-1-judged-50-b", "kind": "split", "benchmark": "hover", "created": "2026-09-16",
    "derives_from": ["data/hover/splits/models-1", "data/hover/splits/models-1-judged-50", "data/hover/outcomes/cap-7.jsonl"],
    "counts": {"drawn": K, "from": 450, "draws_examined": DRAWS, "tied_pairs_on_gold50": tied},
    "checks": {"all_in_models1_judging": all(t in pool for t in draw), "disjoint_from_first_50": not (set(draw) & first), "cap8_not_read": True},
    "produced_by": "data/hover/scripts/draw_judged_50_b.py", "seed": SEED,
    "selection_on_gold": "yes: the condition (fewest tied pairs) reads the judging-pool outcomes, so gold-50 on this set is informative by construction; disclose wherever this set's results are reported"}, indent=2))
(out / "README.md").write_text(f"""# models-1-judged-50-b — second judged 50 for the models-1 set

50 tasks from the models-1 judging pool, disjoint from `models-1-judged-50`, chosen as the
one of {DRAWS} seeded random draws with the fewest candidate pairs tied on judging-pool gold
({tied} of 36 pairs; the first set had {t1}), pass-count spread {-nspread}.

**Selected on gold.** The condition reads `outcomes/cap-7.jsonl` (the judging pool's own
outcomes), so gold-50 on this set separates candidates by construction — the point of the
draw, since a gold-50 with tied candidates cannot be a target for anything. The
generalization outcomes (`cap-8`) were not read. Report this wherever the set is used.

Pass counts on the 50: {sorted(pc.values(), reverse=True)}.

Built by `scripts/draw_judged_50_b.py`; the seed reproduces it.
""")
