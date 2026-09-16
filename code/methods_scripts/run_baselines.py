"""The BASELINES.md entries on a judged 50, reported in Andrei's four-column format.

    python3 methods/scripts/run_baselines.py [--bench hover|livecodebench] [RUN_DIR]

hover reads gold from data/hover/outcomes/cap-7 (judged) and cap-8 (generalization);
livecodebench reads it from the pools' outcomes.json sidecars. The formulas are the
same code path for both benchmarks.
"""
import json, glob, itertools, sys
from collections import defaultdict

args = sys.argv[1:]
BENCH = "hover"
if "--bench" in args:
    i = args.index("--bench"); BENCH = args[i + 1]; del args[i:i + 2]
SUPPORT_MIN = 5

if BENCH == "hover":
    RUN  = args[0] if args else "runs/new_pipeline/hover-models/pointjudge-1-sp15"
    POOL = "runs/new_pipeline/hover-models/pool_judging"
    CSET = 'data/hover/candidates/sets/models-1.json'
    TAX  = 'data/hover/taxonomies/tax-15/taxonomy.json'
else:
    RUN  = args[0] if args else "runs/new_pipeline/lcb-models/pointjudge-1-tax2"
    POOL = "runs/new_pipeline/lcb-models/pool_judging50"
    GEN  = "runs/new_pipeline/lcb-models/pool_generalization"
    CSET = 'data/livecodebench/candidates/sets/models-1.json'
    TAX  = json.load(open(f"{RUN}/summary.json"))["taxonomy"]

cs = json.load(open(CSET))
sm, ids = cs["solver_models"], cs["candidate_ids"]
mo = {c: (sm[c] if isinstance(sm, dict) else sm[i]) for i, c in enumerate(ids)}
active = sorted(cs["active_candidate_ids"])
pm = json.load(open(f'{POOL}/pool_manifest.json'))
inv = {v: k for k, v in pm["candidate_index"].items()}
CODES = [c["id"] for c in json.load(open(TAX))["codes"]]

# gold
def gold_hover(cap):
    d = defaultdict(dict)
    for line in open(f'data/hover/outcomes/{cap}.jsonl'):
        r = json.loads(line)
        if r["candidate_id"] in active: d[r["candidate_id"]][r["task_id"]] = r["score"]
    return d
def gold_pool(pool):
    """candidate -> task -> score, from the pool's outcomes.json sidecar keyed by trace id."""
    sc = json.load(open(f"{pool}/outcomes.json"))["scores"]; d = defaultdict(dict)
    for p in glob.glob(f"{pool}/*.json"):
        if p.endswith(("outcomes.json", "pool_manifest.json")): continue
        t = json.load(open(p)); m = t["metadata"]; c = m["candidate_id"]
        if c in active: d[c][m["task_source_id"]] = sc[t["trace_id"]]
    return d
if BENCH == "hover":
    GJ, GG = gold_hover('cap-7'), gold_hover('cap-8')
else:
    GJ, GG = gold_pool(POOL), gold_pool(GEN)

# evidence: per candidate per task -> set of codes, and (step,code) pairs
ev = defaultdict(dict); steps = defaultdict(dict); turn_max = defaultdict(dict)
for p in glob.glob(f"{RUN}/traces/*.json"):
    d = json.load(open(p))
    if d.get("status") != "judged": continue
    c = inv[d["candidate_index"]]
    if c not in active: continue
    ev[c][d["task_id"]] = {m for q in d["points"] for m in (q.get("codes") or [])}
    steps[c][d["task_id"]] = {(q["turn"], m) for q in d["points"] for m in (q.get("codes") or [])}
    turn_max[c][d["task_id"]] = [t["turn"] for t in d["turns"]]
T = {c: len(ev[c]) for c in active}
tasks50 = sorted(ev[active[0]])

def rate(c, m): return sum(1 for t in ev[c] if m in ev[c][t]) / T[c]

M = {}
M["1 gold"]        = {c: sum(GJ[c][t] for t in tasks50)/len(tasks50) for c in active}
M["2 amplitude"]   = {c: sum(len(ev[c][t]) for t in ev[c])/T[c] for c in active}
M["3 incidence"]   = {c: sum(1 for t in ev[c] if ev[c][t])/T[c] for c in active}
M["4 breadth"]     = {c: sum(1 for m in CODES if rate(c, m) > 0) for c in active}
M["5 worst mode"]  = {c: max(rate(c, m) for m in CODES) for c in active}
M["6 combinations"]= {c: sum(2**len(ev[c][t]) - 1 for t in ev[c])/T[c] for c in active}
M["7 patterns"]    = {c: len({frozenset(ev[c][t]) for t in ev[c] if ev[c][t]}) for c in active}
M["8 step-amp"]    = {c: sum(len(steps[c][t]) for t in steps[c])/T[c] for c in active}
low_support = 0
def rec(c):
    tot = 0.0
    global low_support
    for m in CODES:
        app = [t for t in ev[c] if m in ev[c][t]]
        if not app: continue
        if len(app) < SUPPORT_MIN: low_support += 1
        w = 1 - sum(1 for t in app if GJ[c][t] > 0)/len(app)
        tot += w * (len(app)/T[c])
    return tot
M["9 recovery"]    = {c: rec(c) for c in active}

# 10. containment: down(s) = every later turn in that trace (the program is a linear
# pipeline, confirmed from the traces: each turn consumes the previous turn's output,
# directly or through a harness retrieval). A firing at s is contained when a later
# turn exists and no code fired at any later turn. The last turn is never contained.
def con(c):
    tot = 0
    for t in steps[c]:
        fired = steps[c][t]
        if not fired: continue
        turns_here = {s for s, _ in fired}
        last = max(turn_max[c][t])
        for s, m in fired:
            downstream_failed = any(s2 > s for s2 in turns_here)
            terminal = (s == last)
            if terminal or downstream_failed:
                tot += 1
    return tot / T[c]
M["10 containment"] = {c: con(c) for c in active}

HIGHER_BETTER = {"1 gold"}
def ranking(name):
    s = M[name]
    return sorted(active, key=lambda c: -s[c] if name in HIGHER_BETTER else s[c])

def taub(r1, s1, r2, s2):
    c = d = 0
    for a, b in itertools.combinations(active, 2):
        if s1[a] == s1[b] or s2[a] == s2[b]: continue
        h1 = a if r1.index(a) < r1.index(b) else b
        h2 = a if r2.index(a) < r2.index(b) else b
        c += h1 == h2; d += h1 != h2
    return (c - d)/(c + d) if c + d else float('nan')

g50 = {c: sum(GJ[c][t] for t in tasks50)/len(tasks50) for c in active}
ggn = {c: sum(GG[c].values())/len(GG[c]) for c in active}
r50 = sorted(active, key=lambda c: -g50[c]); rgn = sorted(active, key=lambda c: -ggn[c])
C3 = taub(r50, g50, rgn, ggn)

print(f"{BENCH}  run={RUN}  taxonomy={TAX}  judged tasks={len(tasks50)}  gen tasks={len(GG[active[0]])}\n")
print(f"| method | tau judge vs gold-50 | tau judge vs gold-gen | tau gold-50 vs gold-gen | top-1 |")
print(f"|---|---:|---:|---:|---|")
for name in M:
    r = ranking(name)
    t1 = taub(r, M[name], r50, g50)
    t2 = taub(r, M[name], rgn, ggn)
    print(f"| {name} | {t1:+.3f} | {t2:+.3f} | {C3:+.3f} | "
          f"{'yes' if r[0]==rgn[0] else 'no'} |")
print(f"\nlow-support code/candidate cells in method 9 (app_m < {SUPPORT_MIN}): {low_support}")
