"""Agreement against many generalization sets: how much of the gap to +1 is the target's own noise.

    python3 methods/scripts/gen_set_sweep.py --bench hover-pool3 <unrecovered-only pointjudge run>

Scores are computed once on the judged set (gold-50, incidence, last-turn incidence,
unrecovered amplitude); the generalization pool is then resampled: uniform subsets of k tasks
(30 draws per k), ten named draws of 300, and five disjoint parts of 100 from one fixed
shuffle. Reported: tau-b vs each draw (mean ± sd where there are several). Free.
"""
import glob, itertools, json, random, statistics as st, sys
from collections import defaultdict
args = sys.argv[1:]
BENCH = "hover-pool3"
if "--bench" in args:
    i = args.index("--bench"); BENCH = args[i + 1]; del args[i:i + 2]
RUN = args[0]
if BENCH != "hover-pool3":
    raise SystemExit("gen_set_sweep: hover-pool3 only for now (gold in data/hover/outcomes/cap-2 and cap-3)")
sm = json.load(open(f"{RUN}/summary.json")); pool = sm.get("traces") or json.load(open(f"{sm['mapping']}/summary.json"))["traces"]
pm = json.load(open(f"{pool}/pool_manifest.json")); inv = {v: k for k, v in pm["candidate_index"].items()}
gen = defaultdict(dict)
for l in open("data/hover/outcomes/cap-3.jsonl"):
    r = json.loads(l); gen[r["candidate_id"]][r["task_id"]] = r["score"]
G50 = {}
for l in open(f"data/hover/outcomes/{pm['captures'][0]}.jsonl"):
    r = json.loads(l); G50[(r["candidate_id"], r["task_id"])] = r["score"]
n = defaultdict(int); flag = defaultdict(float); g50 = defaultdict(float); amp = defaultdict(float); last = defaultdict(float)
for p in glob.glob(f"{RUN}/traces/*.json"):
    d = json.load(open(p))
    if d.get("status") != "judged": continue
    c = inv[d["candidate_index"]]; n[c] += 1; L = max(t["turn"] for t in d["turns"])
    flag[c] += bool(d["points"]); g50[c] += G50[(c, d["task_id"])]; amp[c] += len(d["points"]); last[c] += any(q["turn"] == L for q in d["points"])
active = sorted(n)
for s in (flag, g50, amp, last):
    for c in active: s[c] /= n[c]
gen_tasks = sorted(gen[active[0]])
def taub(s, g, lower=True):
    C = D = 0
    for a, b in itertools.combinations(active, 2):
        if s[a] == s[b] or g[a] == g[b]: continue
        sg = (s[a] - s[b]) * (g[a] - g[b]); C += (sg < 0) if lower else (sg > 0); D += (sg > 0) if lower else (sg < 0)
    return (C - D) / (C + D) if C + D else float("nan")
def ggen(ts): return {c: sum(gen[c][t] for t in ts) / len(ts) for c in active}
SCORES = [("gold-50", g50, False), ("incidence", flag, True), ("last-turn incidence", last, True), ("unrec. amplitude", amp, True)]
print(f"{RUN}: {len(active)} candidates, {n[active[0]]} judged tasks, {len(gen_tasks)} generalization tasks\n")
print("## uniform subsets of the generalization tasks, 30 draws per size (mean ± sd)\n")
print("| gen-set size | " + " | ".join(name for name, _, _ in SCORES) + " |\n|---:|" + "---:|" * len(SCORES))
for k in (50, 100, 200, 300, len(gen_tasks)):
    rows = []
    for seed in range(30 if k < len(gen_tasks) else 1):
        g = ggen(random.Random(seed).sample(gen_tasks, k) if k < len(gen_tasks) else gen_tasks)
        rows.append([taub(s, g, lower) for _, s, lower in SCORES])
    cells = [f"{st.mean(r[i] for r in rows):+.3f}" + (f" ± {st.pstdev(r[i] for r in rows):.2f}" if len(rows) > 1 else "") for i in range(len(SCORES))]
    print(f"| {k} | " + " | ".join(cells) + " |")
print("\n## ten draws of 300\n")
print("| draw | " + " | ".join(name for name, _, _ in SCORES) + " |\n|---|" + "---:|" * len(SCORES))
rows = []
for seed in range(1, 11):
    g = ggen(random.Random(seed).sample(gen_tasks, 300)); r = [taub(s, g, lower) for _, s, lower in SCORES]; rows.append(r)
    print(f"| {seed} | " + " | ".join(f"{x:+.3f}" for x in r) + " |")
print("| **mean ± sd** | " + " | ".join(f"{st.mean(r[i] for r in rows):+.3f} ± {st.pstdev(r[i] for r in rows):.2f}" for i in range(len(SCORES))) + " |")
print("\ndraws where each score beats gold-50: " + ", ".join(f"{name} {sum(r[i] > r[0] for r in rows)}/10" for i, (name, _, _) in enumerate(SCORES) if i))
print("\n## five disjoint parts of 100 (one fixed shuffle, seed 2026)\n")
shuf = gen_tasks[:]; random.Random(2026).shuffle(shuf); full = ggen(gen_tasks)
print("| part | " + " | ".join(name for name, _, _ in SCORES) + " | full gold-gen |\n|---|" + "---:|" * (len(SCORES) + 1))
for i in range(len(gen_tasks) // 100):
    g = ggen(shuf[i * 100:(i + 1) * 100])
    print(f"| {i + 1} | " + " | ".join(f"{taub(s, g, lower):+.3f}" for _, s, lower in SCORES) + f" | {taub(full, g, lower=False):+.3f} |")
