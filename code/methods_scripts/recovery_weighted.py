"""Recovery-discounted amplitude with (code, step) units, recovery read from the trace.

    python3 methods/scripts/recovery_weighted.py --bench hover|hover-pool3 <recovery run> [<recovery run> ...]

For candidate c and unit u = (code, turn):
    appeared_u(c)   judged tasks on which u fired for c
    recovered_u(c)  those where the recovery pass found the firing recovered
    w_u(c) = 1 - (recovered_u(c) / appeared_u(c)) ** gamma
    A(c)   = (1/T) * sum_u w_u(c) * appeared_u(c)                    lower is better

Two sources for the recovery share: the candidate's own (per-candidate; under SUPPORT_MIN
appearances the candidate's overall share is used, as the 2026-09-08 analysis did), and
pooled over all candidates (the unit's recoverability as a property of the failure mode at
that step, one weight for everyone). gamma in {1, 2, 3}. At gamma = 1 the per-candidate
form equals unrecovered step-amplitude exactly. Reported: tau-b vs gold-gen, gold row = the
judged tasks' own pass rate vs gold-gen.
"""
import glob, itertools, json, sys
from collections import defaultdict

args = sys.argv[1:]
BENCH = "hover"
if "--bench" in args:
    i = args.index("--bench"); BENCH = args[i + 1]; del args[i:i + 2]
RUNS = args
SUPPORT_MIN = 3
RECOVERED = ("corrected", "contained", "made_irrelevant")

if BENCH == "hover":
    cs = json.load(open("data/hover/candidates/sets/models-1.json")); active = sorted(cs["active_candidate_ids"])
    pm = json.load(open("runs/new_pipeline/hover-models/pool_judging/pool_manifest.json")); inv = {v: k for k, v in pm["candidate_index"].items()}
    def cand_of(d): return inv[d["candidate_index"]]
    G50, GGEN = "cap-7", "cap-8"
elif BENCH == "hover-pool3":
    cs = json.load(open("data/hover/candidates/sets/pool-3.json")); active = sorted(cs["candidate_ids"])
    # a pointjudge-derived run carries candidate_index; the pool it was judged on maps it back
    _inv = {}
    for run in RUNS:
        sm = json.load(open(f"{run}/summary.json")); pool = sm.get("traces")
        if pool: _inv.update({v: k for k, v in json.load(open(f"{pool}/pool_manifest.json"))["candidate_index"].items()})
    def cand_of(d): return d.get("candidate_id") or _inv[d["candidate_index"]]
    G50, GGEN = None, "cap-3"
else:
    raise SystemExit("bench must be hover or hover-pool3")

def gold(cap):
    d = defaultdict(dict)
    for line in open(f"data/hover/outcomes/{cap}.jsonl"):
        r = json.loads(line)
        if r["candidate_id"] in active: d[r["candidate_id"]][r["task_id"]] = r["score"]
    return d
GG = gold(GGEN)
if G50:
    GJ = gold(G50)
else:   # pool-3: the judged tasks' gold lives in the capture each mapping was judged on
    GJ = defaultdict(dict)
    for cap in ("cap-2", "cap-5"):
        for c, d in gold(cap).items(): GJ[c].update(d)

# firings: candidate -> task -> {(turn, code): recovered?}
fired = defaultdict(lambda: defaultdict(dict))
for run in RUNS:
    for p in glob.glob(f"{run}/traces/*.json"):
        d = json.load(open(p))
        if d.get("status") != "judged": continue
        c = cand_of(d)
        if c not in active: continue
        t = d["task_id"]; fired[c][t] = fired[c].get(t, {})
        for q in d["points"]:
            rec = q.get("recovery") in RECOVERED
            for code in q.get("codes") or []:
                u = (q["turn"], code)
                # a unit fired on a task is recovered on that task only if every firing of it was
                fired[c][t][u] = fired[c][t].get(u, True) and rec
T = {c: len(fired[c]) for c in active}
tasks = sorted(fired[active[0]])
assert all(sorted(fired[c]) == tasks for c in active), "candidates judged on different tasks"

def counts(c):
    app, rec = defaultdict(int), defaultdict(int)
    for t in fired[c]:
        for u, r in fired[c][t].items():
            app[u] += 1; rec[u] += r
    return app, rec
per = {c: counts(c) for c in active}
pool_app, pool_rec = defaultdict(int), defaultdict(int)
for c in active:
    for u in per[c][0]:
        pool_app[u] += per[c][0][u]; pool_rec[u] += per[c][1][u]
overall = {c: (sum(per[c][1].values()) / max(sum(per[c][0].values()), 1)) for c in active}

def score(c, gamma, pooled):
    app, rec = per[c]; tot = 0.0
    for u, n in app.items():
        if pooled:
            r = pool_rec[u] / pool_app[u]
        else:
            r = rec[u] / n if n >= SUPPORT_MIN else overall[c]
        tot += (1 - r ** gamma) * n
    return tot / T[c]

def taub(s1, s2):
    r1 = sorted(active, key=lambda c: s1[c]); r2 = sorted(active, key=lambda c: -s2[c])
    C = D = 0
    for a, b in itertools.combinations(active, 2):
        if s1[a] == s1[b] or s2[a] == s2[b]: continue
        h1 = a if r1.index(a) < r1.index(b) else b; h2 = a if r2.index(a) < r2.index(b) else b
        C += h1 == h2; D += h1 != h2
    return (C - D) / (C + D) if C + D else float("nan")

ggen = {c: sum(GG[c].values()) / len(GG[c]) for c in active}
g50 = {c: sum(GJ[c][t] for t in tasks) / len(tasks) for c in active}
top = max(active, key=lambda c: ggen[c])
def top1(s): return "yes" if min(active, key=lambda c: s[c]) == top else "no"

print(f"{BENCH}  runs={' + '.join(RUNS)}  judged tasks={len(tasks)}  units={len(pool_app)}  gen tasks={len(GG[active[0]])}\n")
print("| method | tau vs gold-gen | top-1 |")
print("|---|---:|---|")
print(f"| gold | {taub({c: -g50[c] for c in active}, ggen):+.3f} | {'yes' if max(active, key=lambda c: g50[c]) == top else 'no'} |")
for pooled in (False, True):
    for gamma in (1, 2, 3):
        s = {c: score(c, gamma, pooled) for c in active}
        print(f"| recovery-weighted, {'pooled' if pooled else 'per-candidate'}, γ={gamma} | {taub(s, ggen):+.3f} | {top1(s)} |")
print(f"\nunits with pooled appearances >= 10: {sum(1 for u in pool_app if pool_app[u] >= 10)} of {len(pool_app)}; "
      f"per-candidate cells under support {SUPPORT_MIN}: {sum(1 for c in active for u, n in per[c][0].items() if n < SUPPORT_MIN)}")
