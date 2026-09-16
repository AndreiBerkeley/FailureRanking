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
POOL_ARG = TASKS_ARG = None
if "--pool" in args:        # the judged pool the run read (default per benchmark)
    i = args.index("--pool"); POOL_ARG = args[i + 1]; del args[i:i + 2]
if "--tasks" in args:       # a split.json; only its portions.judged / portions.judging tasks are scored
    i = args.index("--tasks"); TASKS_ARG = args[i + 1]; del args[i:i + 2]
SUPPORT_MIN = 5

RUNS = args or None      # one or more judge run dirs (disjoint task sets are pooled)
if BENCH == "hover":
    RUN  = " + ".join(args) if args else "runs/new_pipeline/hover-models/pointjudge-1-sp15"
    POOL = "runs/new_pipeline/hover-models/pool_judging"
    CSET = 'data/hover/candidates/sets/models-1.json'
    TAX  = 'data/hover/taxonomies/tax-15/taxonomy.json'
elif BENCH == "hover-pool3":
    # the 12 optimizer candidates: panel-judge mappings (code counts per trace, no steps)
    MAPS = args or ["data/hover/mappings/map-5"]
    RUN  = " + ".join(MAPS)
    CSET = 'data/hover/candidates/sets/pool-3.json'
    TAX  = 'data/hover/taxonomies/tax-10/taxonomy.json'
    GOLD50 = {"map-5": "cap-2", "map-6": "cap-5"}      # the judged tasks' own capture
else:
    RUN  = " + ".join(args) if args else "runs/new_pipeline/lcb-models/pointjudge-1-tax2"
    POOL = POOL_ARG or "runs/new_pipeline/lcb-models/pool_judging50"
    GEN  = "runs/new_pipeline/lcb-models/pool_generalization"
    CSET = 'data/livecodebench/candidates/sets/models-1.json'
    TAX  = json.load(open(f"{(args or [RUN])[0]}/summary.json"))["taxonomy"]

cs = json.load(open(CSET))
if BENCH == "hover-pool3":
    active = sorted(cs["candidate_ids"])                # no active list: all 12 are the set
else:
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
elif BENCH == "hover-pool3":
    GJ = defaultdict(dict)
    for m in MAPS:
        for c, d in gold_hover(GOLD50[m.rstrip('/').split('/')[-1]]).items(): GJ[c].update(d)
    GG = gold_hover('cap-3')                            # eval-1 domain, 500 tasks, disjoint from every judged set
else:
    GJ, GG = gold_pool(POOL), gold_pool(GEN)

# evidence: per candidate per task -> set of codes, and (step,code) pairs
ev = defaultdict(dict); steps = defaultdict(dict); turn_max = defaultdict(dict)
HAS_STEPS = BENCH != "hover-pool3"
if BENCH == "hover-pool3":
    for m in MAPS:
        for line in open(f"{m}/mapping.jsonl"):
            d = json.loads(line)
            if d.get("status") != "judged": continue
            ev[d["candidate_id"]][d["task_id"]] = set(d["codes"])
    T = {c: len(ev[c]) for c in active}
RUN_DIRS = RUNS or [RUN]
for p in ([f for r in RUN_DIRS for f in glob.glob(f"{r}/traces/*.json")] if HAS_STEPS else []):
    d = json.load(open(p))
    if d.get("status") != "judged": continue
    c = inv[d["candidate_index"]]
    if c not in active: continue
    ev[c][d["task_id"]] = {m for q in d["points"] for m in (q.get("codes") or [])}
    steps[c][d["task_id"]] = {(q["turn"], m) for q in d["points"] for m in (q.get("codes") or [])}
    turn_max[c][d["task_id"]] = [t["turn"] for t in d["turns"]]
if TASKS_ARG:
    doc = json.loads(open(TASKS_ARG).read())["portions"]
    keep = set(doc.get("judged") or doc.get("judging"))
    for c in active:
        ev[c] = {t: v for t, v in ev[c].items() if t in keep}
        steps[c] = {t: v for t, v in steps[c].items() if t in keep}
        turn_max[c] = {t: v for t, v in turn_max[c].items() if t in keep}
    missing = keep - set(ev[active[0]])
    assert not missing, f"--tasks names {len(missing)} task(s) the run did not judge, e.g. {sorted(missing)[:3]}"
T = {c: len(ev[c]) for c in active}
tasks50 = sorted(ev[active[0]])
assert all(sorted(ev[c]) == tasks50 for c in active), "candidates judged on different tasks"
assert all(t in GJ[c] for c in active for t in tasks50), "a judged task has no gold-50 row"

def rate(c, m): return sum(1 for t in ev[c] if m in ev[c][t]) / T[c]

M = {}
M["1 gold"]        = {c: sum(GJ[c][t] for t in tasks50)/len(tasks50) for c in active}
M["2 amplitude"]   = {c: sum(len(ev[c][t]) for t in ev[c])/T[c] for c in active}
M["3 incidence"]   = {c: sum(1 for t in ev[c] if ev[c][t])/T[c] for c in active}
M["4 breadth"]     = {c: sum(1 for m in CODES if rate(c, m) > 0) for c in active}
M["5 worst mode"]  = {c: max(rate(c, m) for m in CODES) for c in active}
M["6 combinations"]= {c: sum(2**len(ev[c][t]) - 1 for t in ev[c])/T[c] for c in active}
M["7 patterns"]    = {c: len({frozenset(ev[c][t]) for t in ev[c] if ev[c][t]}) for c in active}
if HAS_STEPS: M["8 step-amp"] = {c: sum(len(steps[c][t]) for t in steps[c])/T[c] for c in active}
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
if HAS_STEPS: M["10 containment"] = {c: con(c) for c in active}

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

print(f"{BENCH}  run={RUN}  taxonomy={TAX}  judged tasks={len(tasks50)}{'  (' + TASKS_ARG + ')' if TASKS_ARG else ''}  gen tasks={len(GG[active[0]])}\n")
# three columns: the gold row's "vs gold-gen" IS gold-50 vs gold-gen, so that constant
# is not repeated as a column of its own
# the gold row's value is gold-50 vs gold-gen, the bar every trace method is read against
print(f"| method | tau vs gold-gen | top-1 |")
print(f"|---|---:|---|")
for name in M:
    r = ranking(name)
    t2 = taub(r, M[name], rgn, ggn)
    print(f"| {name} | {t2:+.3f} | {'yes' if r[0]==rgn[0] else 'no'} |")
print(f"\nlow-support code/candidate cells in method 9 (app_m < {SUPPORT_MIN}): {low_support}")
if not HAS_STEPS: print("methods 8 and 10 need per-step firings; this judge records code counts per trace only")
