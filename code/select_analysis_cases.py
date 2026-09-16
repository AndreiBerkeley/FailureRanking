"""Select the traces for the model_ranking branch's analysis/ folders and write them out.

    python3 data/scripts/select_analysis_cases.py <worktree-root>

Three folders, one per (benchmark, candidate set). Every case is a trace whose judge
mapping says something about why the trace methods rank well or badly: a point on a passing
trace, a failing trace with no point, a code that fires on winners and losers alike, a
firing at one step that later steps carried or did not. Each folder gets

    README.md              the categories, the per-case table, the observations
    cases.json             machine-readable: trace id, task, candidate, gold, codes, category, note
    traces/<trace_id>.json the trace in the judge's view
    judge/<trace_id>.json  the judge's record for that trace (points with step, evidence, codes)

Selection is data-driven (the categories below), deterministic (sorted, first N), and reads
gold only to pick cases -- the notes say what the gold was, which is the point of the folder.
"""
import gzip, json, shutil, sys
from collections import defaultdict, Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve() / "analysis"


def write_folder(name, title, intro, categories, cases, trace_src, judge_src, extra_readme=""):
    d = OUT / name
    if d.exists():
        shutil.rmtree(d)
    (d / "traces").mkdir(parents=True); (d / "judge").mkdir()
    seen = set(); cases = [c for c in cases if not (c["trace_id"] in seen or seen.add(c["trace_id"]))]   # one row per trace
    for c in cases:
        src = trace_src(c["trace_id"])
        if isinstance(src, dict):
            (d / "traces" / f"{c['trace_id']}.json").write_text(json.dumps(src, indent=1))
        else:
            shutil.copy2(src, d / "traces" / f"{c['trace_id']}.json")
        (d / "judge" / f"{c['trace_id']}.json").write_text(json.dumps(judge_src(c["trace_id"]), indent=1))
    (d / "cases.json").write_text(json.dumps(cases, indent=1))
    lines = [f"# {title}", "", intro, "", "| category | what it shows | cases |", "|---|---|---:|"]
    for key, (label, why) in categories.items():
        lines.append(f"| {key} | {why} | {sum(1 for c in cases if c['category'] == key)} |")
    lines += ["", "## Cases", "", "| # | trace | task | candidate | gold | codes | category | note |", "|---|---|---|---|---|---|---|---|"]
    for i, c in enumerate(cases, 1):
        lines.append(f"| {i} | `{c['trace_id'][:8]}` | {c['task']} | {c['candidate']} | {'pass' if c['gold'] else 'fail'} | "
                     f"{', '.join(c['codes']) or '—'} | {c['category']} | {c['note']} |")
    lines += ["", extra_readme]
    (d / "README.md").write_text("\n".join(lines) + "\n")
    print(f"{name}: {len(cases)} cases")


# ------------------------------------------------------------------ livecodebench / models
def lcb():
    P = REPO / "runs/new_pipeline/lcb-models/pool_judging150"; J = REPO / "runs/new_pipeline/lcb-models/pointjudge-2"
    out = json.loads((P / "outcomes.json").read_text())["scores"]
    man = json.loads((P / "pool_manifest.json").read_text())
    cs = json.loads((REPO / "data/livecodebench/candidates/sets/models-1.json").read_text())
    idx2m = {i: cs["solver_models"][c].split("/")[-1] for c, i in man["candidate_index"].items()}
    errs = {}
    for cap in ("models-1-judging50", "models-1-judging100"):
        for l in open(REPO / f"data/livecodebench/traces/_incoming/{cap}/outcomes.jsonl"):
            r = json.loads(l); errs[r["trace_id"]] = r
    recs = {}
    for f in (J / "traces").glob("*.json"):
        d = json.loads(f.read_text()); recs[d["trace_id"]] = d
    def row(tid, cat, note):
        d = recs[tid]; codes = sorted({c for p in d["points"] for c in p["codes"]})
        return dict(trace_id=tid, task=d["task_id"], candidate=idx2m[d["candidate_index"]], gold=out[tid], codes=codes,
                    n_points=len(d["points"]), category=cat, note=note)
    def first_problem(tid):
        for p in recs[tid]["points"]:
            return p["problem"][:160].replace("|", "/")
        return ""
    cases = []
    # A. points on passing traces -- the judge's false positives, or latent defects the tests never reached
    A = sorted([t for t, d in recs.items() if out[t] == 1 and d["points"]], key=lambda t: (recs[t]["task_id"], t))
    for t in A[:6]:
        cases.append(row(t, "A", "judge: " + first_problem(t)))
    # B. failing traces with no point
    B = sorted([t for t, d in recs.items() if out[t] == 0 and not d["points"]], key=lambda t: (recs[t]["task_id"], t))
    b_343 = [t for t in B if recs[t]["task_id"] == "abc343_a"][:2]
    b_other = [t for t in B if recs[t]["task_id"] != "abc343_a"]
    for t in b_343:
        cases.append(row(t, "B", "abc343_a asks for *any* digit ≠ A+B; the checker compares to the sample's digit, so all nine models 'fail' — gold error, judge correctly silent"))
    seen_err = set()
    for t in b_other:
        e = errs[t]; key = (e["error"] or "")[:12]
        if key in seen_err: continue
        seen_err.add(key)
        cases.append(row(t, "B", f"harness: {e['error'][:70]} ({e['tests_passed']}/{e['tests_run']} tests before stop); the judge read the program and saw nothing"))
        if len(seen_err) >= 5: break
    # C. clean hits: one failing trace per code, found by both readers, first in task order
    for code in ("SP_01", "SP_02", "SP_03", "SP_04", "SP_07", "SP_08", "SP_09", "SP_10"):
        cands = sorted([t for t, d in recs.items() if out[t] == 0 and any(code in p["codes"] and p["from_a"] is not None and p["from_b"] is not None for p in d["points"])],
                       key=lambda t: (recs[t]["task_id"], t))
        if cands:
            t = cands[0]; p = next(p for p in recs[t]["points"] if code in p["codes"])
            cases.append(row(t, "C", f"{code}, both readers; harness: {(errs[t]['error'] or '')[:40]}; judge: {p['problem'][:120].replace('|', '/')}"))
    # D. points that fit no code
    for t in sorted([t for t, d in recs.items() if any(p["none_fits"] for p in d["points"])]):
        p = next(p for p in recs[t]["points"] if p["none_fits"])
        cases.append(row(t, "D", "unplaced: " + (p["missing"] or p["problem"])[:150].replace("|", "/")))
    # E. one task, nine models: passers silent, failers coded -- how amplitude separates candidates
    for task in ("3721", "abc340_d"):
        ts = sorted([t for t, d in recs.items() if d["task_id"] == task])
        for t in [x for x in ts if out[x] == 0][:2] + [x for x in ts if out[x] == 1][:2]:
            cases.append(row(t, "E", f"task {task}: {'passes, no point' if out[t] else 'fails; ' + first_problem(t)[:100]}"))
    pm = defaultdict(Counter)
    gg = json.loads((REPO / "runs/new_pipeline/lcb-models/pool_generalization/outcomes.json").read_text())["scores"]
    ggen = defaultdict(list)
    for f in (REPO / "runs/new_pipeline/lcb-models/pool_generalization").glob("*.json"):
        if f.name in ("outcomes.json", "pool_manifest.json"): continue
        d = json.loads(f.read_text()); ggen[idx2m[d["metadata"]["candidate_index"]]].append(gg[d["trace_id"]])
    for t, d in recs.items():
        m = idx2m[d["candidate_index"]]; n = len(d["points"]); g = out[t]
        pm[m]["fails"] += (g == 0); pm[m]["points"] += n
        if g == 0: pm[m]["pts_on_fail"] += n; pm[m]["silent_fail"] += (n == 0)
        else: pm[m]["pts_on_pass"] += n
    per_model_table = ("| model | gold-gen | fails / 150 | points | points per failing trace | silent failures | points on passing traces |\n"
                       "|---|---:|---:|---:|---:|---:|---:|\n")
    for m in sorted(pm, key=lambda m: -sum(ggen[m]) / len(ggen[m])):
        c = pm[m]
        per_model_table += (f"| {m} | {sum(ggen[m]) / len(ggen[m]):.3f} | {c['fails']} | {c['points']} | {c['pts_on_fail'] / max(c['fails'], 1):.2f} | "
                            f"{c['silent_fail']} | {c['pts_on_pass']} |\n")
    categories = {
        "A": ("points on passing traces", "22 of 878 passing traces carry a point (the judge never sees outcomes): mostly complexity warnings (SP_02) and implementation defects the tests did not exercise"),
        "B": ("failing traces with no point", "33 of 472 failing traces have no point: 9 are one task whose checker rejects every valid answer, the rest are runtime/TLE/subtle wrong answers the reader did not catch"),
        "C": ("one clean hit per code", "a failing trace per code where both readers found the same point — what a code looks like when it works"),
        "D": ("points that fit no code", "the 3 of 627 points the decider could place nowhere under tax-2"),
        "E": ("one task across models", "passers silent, failers coded — the per-task pattern that lets amplitude and incidence track gold"),
    }
    intro = ("Nine models, tax-2, judge `pointjudge-2` on the 150 judging tasks. On this benchmark the trace methods track gold "
             "(amplitude +0.889 vs gold-gen on the 150); these cases show the mechanism and its edges. Every trace is one turn: "
             "problem in, program out; the judge's points quote the program.")
    extra = ("## What the cases say\n\n"
             "The judge is outcome-blind and almost never fires on a passing program: 856 of 878 passing traces are silent, "
             "439 of 472 failing traces carry a point. That asymmetry is the whole result — a per-candidate count of points is a "
             "per-candidate count of failures with ~5% noise either way. The A cases are that noise on the passing side: complexity "
             "warnings (a judged O(n²) that the tests never stressed) and implementation defects on paths the tests do not reach. "
             "The B cases are the noise on the failing side, and a third of them are not noise at all: `abc343_a` accepts any digit "
             "≠ A+B and the benchmark's exact-match checker rejects eight of the nine valid answers, so the judge's silence is right "
             "and the gold is wrong. The C cases are the codes doing their job; the E cases show the pattern per task.\n\n"
             "## Why it is still not perfect\n\n"
             "Amplitude reaches +0.889 against gold-gen on the 150 judged tasks, not +1, and a random 50 lands anywhere between "
             "+0.667 and +0.941. The reasons are visible in the cases and in the per-model counts:\n\n"
             + per_model_table +
             "\n1. **Amplitude counts points, not failures, and points per failing trace differ by model** — from 1.00 (minimax) "
             "to 1.54 (seed). glm and deepseek both fail 42 of 150 and are tied on gold-gen (0.694 vs 0.690), but deepseek's "
             "failures draw 55 points to glm's 44: the judge finds more to quote in some models' programs than in others', and "
             "that is not a difference in how often they fail. Incidence removes this and matches amplitude on the 150 (+0.889).\n"
             "2. **Failures the reader cannot see from the program.** Of the 33 silent failures, 9 are the checker's error (B), "
             "and the rest are mostly things a reading cannot settle: a time limit that depends on constant factors (C `1e9fbe53`, "
             "`43032638`), a runtime error on the third hidden test, a module the sandbox does not have (`21d66ec0`), a recursion "
             "depth the language enforces (D `caf5599b`). They are not evenly spread — minimax has 8 silent failures in 53, "
             "mistral 1 in 75 — so they shift candidates relative to each other.\n"
             "3. **Points on passing programs are not evenly spread either** — gpt-5.4-nano and minimax carry 5–6 points on passing "
             "traces, mimo none. Most are complexity warnings (SP_02): the judge predicts a time limit the tests did not enforce.\n"
             "4. **Gold-gen has its own noise.** Two candidate pairs are within 0.004 pass rate on the 755 tasks (mimo / gpt-5.4-nano, "
             "deepseek / glm) — a coin flip for any method, including gold-50 — and 85 of the 755 tasks are failed by all nine "
             "models, 8 of them because the statement allows several answers and the checker accepts one (`arc190_a`, `abc311_c`, "
             "`abc343_e`, …), the same defect as `abc343_a`.\n"
             "5. **Fifty tasks is a small sample of nine models a few passes apart.** Adjacent models differ by 1–3 passes on a "
             "random 50; which side of a pair a draw lands on is the draw, for the trace methods and for gold-50 alike — hence the "
             "spread of the ten draws, and hence gold-50's own +0.657 to +0.941.")
    write_folder("livecodebench_model", "livecodebench / models — cases", intro, categories, cases,
                 lambda tid: P / f"{tid}.json", lambda tid: recs[tid], extra)


# ------------------------------------------------------------------ hover / models
def hover_models():
    cs = json.loads((REPO / "data/hover/candidates/sets/models-1.json").read_text())
    pm = json.loads((REPO / "runs/new_pipeline/hover-models/pool_judging/pool_manifest.json").read_text()); inv = {v: k for k, v in pm["candidate_index"].items()}
    gold = {}
    for l in open(REPO / "data/hover/outcomes/cap-7.jsonl"):
        r = json.loads(l); gold[(r["candidate_id"], r["task_id"])] = r["score"]
    tasks = {json.loads(l)["task_id"]: json.loads(l) for l in open(REPO / "data/hover/tasks/tasks.jsonl")}
    recs = {}; run_of = {}
    for run in ("pointjudge-1-sp15", "pointjudge-3"):
        for f in (REPO / f"runs/new_pipeline/hover-models/{run}/traces").glob("*.json"):
            d = json.loads(f.read_text()); recs[d["trace_id"]] = d; run_of[d["trace_id"]] = run
    # retrieved titles per trace, from the capture bodies, to say which gold title was missed
    retrieved = {}
    for b in (REPO / "data/hover/traces/cap-7/bodies").glob("*.jsonl.gz"):
        with gzip.open(b, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                if r["trace_id"] in recs:
                    docs = r["prediction"].get("retrieved_docs") or []
                    retrieved[r["trace_id"]] = {x.split(" | ")[0] for x in docs}
    def missed(tid):
        d = recs[tid]; g = tasks[d["task_id"]]["gold"]["supporting_titles"]
        return [t for t in g if t not in retrieved.get(tid, set())]
    def row(tid, cat, note):
        d = recs[tid]; c = inv[d["candidate_index"]]; codes = Counter(cc for p in d["points"] for cc in p["codes"])
        return dict(trace_id=tid, task=d["task_id"], candidate=cs["solver_models"][c].split("/")[-1], gold=gold[(c, d["task_id"])],
                    codes=[f"{k}×{v}" if v > 1 else k for k, v in sorted(codes.items())], n_points=len(d["points"]), category=cat, note=note, judge_run=run_of[tid])
    def cand(tid): return inv[recs[tid]["candidate_index"]]
    def g(tid): return gold[(cand(tid), recs[tid]["task_id"])]
    cases = []
    # A. passing traces with many points: the codes fire on successes
    A = sorted([t for t in recs if g(t) == 1 and len(recs[t]["points"]) >= 6], key=lambda t: -len(recs[t]["points"]))
    for t in A[:6]:
        top = Counter(cc for p in recs[t]["points"] for cc in p["codes"]).most_common(2)
        cases.append(row(t, "A", f"{len(recs[t]['points'])} points on a passing run; all three gold titles retrieved; heaviest codes {', '.join(f'{k}×{v}' for k, v in top)}"))
    # B. failing traces with 0-1 points
    B = sorted([t for t in recs if g(t) == 0 and len(recs[t]["points"]) <= 1], key=lambda t: (len(recs[t]["points"]), t))
    per_model = Counter(); B = [t for t in B if per_model[cand(t)] < 2 and not per_model.update([cand(t)])]   # at most two per model
    for t in B[:6]:
        m = missed(t)
        cases.append(row(t, "B", f"{len(recs[t]['points'])} point(s); missed gold title(s): {', '.join(m) if m else '?'} — the retrieval miss leaves no mark the reader can quote"))
    # C. SP_15 on failing traces (the one code with a failure skew)
    C = sorted([t for t in recs if g(t) == 0 and any("SP_15" in p["codes"] for p in recs[t]["points"])])
    for t in C[:4]:
        p = next(p for p in recs[t]["points"] if "SP_15" in p["codes"])
        cases.append(row(t, "C", f"SP_15 at turn {p['turn']} ({p['agent']}): {p['problem'][:120].replace('|', '/')}; missed {', '.join(missed(t))}"))
    # D. deepseek (most points, mid gold) vs haiku (fewest points, second-best gold) on the same tasks
    ds = [c for c in cs["active_candidate_ids"] if "deepseek" in cs["solver_models"][c]][0]
    hk = [c for c in cs["active_candidate_ids"] if "haiku" in cs["solver_models"][c]][0]
    by_task = defaultdict(dict)
    for t in recs: by_task[recs[t]["task_id"]][cand(t)] = t
    used = {c["trace_id"] for c in cases}
    pairs = sorted([(tk, v[ds], v[hk]) for tk, v in by_task.items() if ds in v and hk in v and g(v[ds]) == 1 and g(v[hk]) == 1
                    and v[ds] not in used and v[hk] not in used],
                   key=lambda x: -(len(recs[x[1]]["points"]) - len(recs[x[2]]["points"])))
    for tk, tds, thk in pairs[:2]:
        for t, who in ((tds, "deepseek"), (thk, "haiku")):
            top = Counter(cc for p in recs[t]["points"] for cc in p["codes"]).most_common(2)
            cases.append(row(t, "D", f"same task, both pass; {who} carries {len(recs[t]['points'])} points ({', '.join(f'{k}×{v}' for k, v in top) or 'none'}) — deepseek's per-trace point count is the highest of the nine, its gold mid-table"))
    # E. containment: a firing at turn 1 or 2 with every later turn clean, on a passing and on a failing trace
    def contained_early(t):
        turns = [p["turn"] for p in recs[t]["points"]]
        return turns and max(turns) <= 2 and len(recs[t]["points"]) >= 2
    E = sorted([t for t in recs if contained_early(t)], key=lambda t: (g(t), t))
    e_fail = [t for t in E if g(t) == 0][:2]; e_pass = [t for t in E if g(t) == 1][:2]
    for t in e_fail + e_pass:
        cases.append(row(t, "E", f"all {len(recs[t]['points'])} points at turns ≤ 2, turns 3–4 clean → every firing is 'contained'; outcome {'pass' if g(t) else 'fail (missed ' + ', '.join(missed(t)) + ')'} — containment reads clean later turns as recovery, but a clean query can still retrieve nothing"))
    categories = {
        "A": ("passing traces with many points", "the judge finds 6–10 points on runs that retrieved every gold title: the codes describe how the modules write, not whether they find the entities"),
        "B": ("failing traces with ≤ 1 point", "runs that missed a gold title with nothing to quote: the miss happens inside the harness's retrieval, not in a module's text"),
        "C": ("SP_15 on failing traces", "the hand-authored 'conclusion unlicensed by the evidence' code, the only one skewed to failures (80 fail / 47 pass)"),
        "D": ("deepseek vs haiku, same task, both pass", "the candidate with the most points per trace (5.35) sits mid-table on gold; the one with the fewest (2.60) is second — amplitude ranks them backwards"),
        "E": ("early firings, clean later turns", "what containment sees: a clean hop-2/hop-3 query after a bad summary, on a run that passed and on one that failed anyway"),
    }
    intro = ("Nine models, tax-15, judge pointjudge (set a `pointjudge-1-sp15`, set b `pointjudge-3`), 100 judged tasks. Here no trace "
             "method tracks gold (amplitude +0.056, incidence +0.200 vs gold-gen on the 100). A trace is four module turns; gold is "
             "whether the three supporting Wikipedia titles came back from the harness's three retrievals.")
    extra = ("## What the cases say\n\n"
             "Points land on passing and failing runs alike: 403 of 407 passing traces carry a point, mean 3.5 points on a pass "
             "vs 4.0 on a fail. Two codes — SP_05 (redundant next-hop query) and SP_06 (meta/evaluative query) — account for the "
             "bulk and fire on 271/305 (pass/fail) and 196/271 traces: they describe the *form* of the query text, and a query in "
             "bad form retrieves the right page as often as not. What decides gold is whether a title the claim never names gets "
             "retrieved, and that happens in the harness, between turns, where nothing is quotable (B). The one code with a failure "
             "skew, SP_15, is the hand-authored one (C). D shows the ranking consequence: deepseek writes verbose, marker-heavy "
             "output that draws the most points of any model while sitting mid-table on gold. E shows why containment cannot "
             "rescue it: a clean later turn is not a recovered retrieval.")
    write_folder("model_hover", "hover / models — cases", intro, categories, cases,
                 lambda tid: REPO / f"runs/new_pipeline/hover-models/pool_judging/{tid}.json", lambda tid: recs[tid], extra)


# ------------------------------------------------------------------ hover / GEPA_candidates
def hover_gepa():
    cs = json.loads((REPO / "data/hover/candidates/sets/pool-3.json").read_text())
    reg = {json.loads(l)["candidate_id"]: json.loads(l) for l in open(REPO / "data/hover/candidates/registry.jsonl")}
    alias = {c: reg[c]["alias"] for c in cs["candidate_ids"]}
    gold = {}
    for cap in ("cap-2", "cap-5"):
        for l in open(REPO / f"data/hover/outcomes/{cap}.jsonl"):
            r = json.loads(l); gold[r["trace_id"]] = r["score"]
    gg = defaultdict(list)
    for l in open(REPO / "data/hover/outcomes/cap-3.jsonl"):
        r = json.loads(l); gg[r["candidate_id"]].append(r["score"])
    ggen = {c: sum(v) / len(v) for c, v in gg.items()}
    tasks = {json.loads(l)["task_id"]: json.loads(l) for l in open(REPO / "data/hover/tasks/tasks.jsonl")}
    maps = {}; recs = {}; cap_of = {}
    for m, cap in (("map-5", "cap-2"), ("map-6", "cap-5")):
        for l in open(REPO / f"data/hover/mappings/{m}/mapping.jsonl"):
            d = json.loads(l); maps[d["trace_id"]] = d; cap_of[d["trace_id"]] = cap
        for b in (REPO / f"data/hover/mappings/{m}/judge_records").glob("*.jsonl.gz"):
            with gzip.open(b, "rt") as fh:
                for line in fh:
                    r = json.loads(line); recs[r["trace_id"]] = r
    retrieved = {}
    for cap in ("cap-2", "cap-5"):
        for b in (REPO / f"data/hover/traces/{cap}/bodies").glob("*.jsonl.gz"):
            with gzip.open(b, "rt") as fh:
                for line in fh:
                    r = json.loads(line)
                    if r["trace_id"] in maps:
                        retrieved[r["trace_id"]] = {x.split(" | ")[0] for x in (r["prediction"].get("retrieved_docs") or [])}
    def missed(tid):
        g = tasks[maps[tid]["task_id"]]["gold"]["supporting_titles"]; return [t for t in g if t not in retrieved.get(tid, set())]
    def steps(tid):
        r = recs[tid]; counted = set(maps[tid]["codes"]); at = {x["agent"]: x["turn"] for x in r["turns"]}; fired = set()
        for key, votes in (r.get("votes_by_turn") or {}).items():
            for code in votes:
                if code in counted: fired.add((int(key.split(":")[0]), code))
        for det in ((r.get("open") or {}).get("details") or []):
            turn = at.get(det.get("agent"))
            for cc in det.get("codes") or []:
                if turn and cc.get("fitness", 0) >= 80 and cc["code"] in counted: fired.add((turn, cc["code"]))
        return fired
    def row(tid, cat, note):
        d = maps[tid]
        return dict(trace_id=tid, task=d["task_id"], candidate=alias[d["candidate_id"]], gold=gold[tid],
                    codes=sorted(d["codes"]), sources={k: v for k, v in d["source"].items()}, category=cat, note=note, mapping=("map-5" if cap_of[tid] == "cap-2" else "map-6"))
    def trace_view(tid):
        cap = cap_of[tid]
        for b in (REPO / f"data/hover/traces/{cap}/bodies").glob("*.jsonl.gz"):
            with gzip.open(b, "rt") as fh:
                for line in fh:
                    r = json.loads(line)
                    if r["trace_id"] == tid:
                        jv = r["judge_view"]; return {"trace_id": tid, "messages": jv["messages"], "metadata": {**{k: v for k, v in jv["metadata"].items() if k != "origin"}, "task_id": r["task_id"], "candidate_id": r["candidate_id"], "capture": cap}}
        raise KeyError(tid)
    def judge_view(tid):
        return {"mapping": maps[tid], "record": recs[tid], "step_firings": sorted(steps(tid))}
    cases = []
    top3 = sorted(cs["candidate_ids"], key=lambda c: -ggen[c])[:3]
    # A. top candidates passing with 3+ codes
    A = sorted([t for t in maps if maps[t]["candidate_id"] in top3 and gold[t] == 1 and len(maps[t]["codes"]) >= 3], key=lambda t: (-len(maps[t]["codes"]), t))
    for t in A[:6]:
        cases.append(row(t, "A", f"{alias[maps[t]['candidate_id']]} (gold-gen {ggen[maps[t]['candidate_id']]:.2f}, top 3) passes with {len(maps[t]['codes'])} codes: {', '.join(sorted(maps[t]['codes']))}"))
    # B. cand-019 (bare docstrings): silent traces, pass and fail
    c019 = [c for c in cs["candidate_ids"] if alias[c] == "cand-019"][0]
    B = sorted([t for t in maps if maps[t]["candidate_id"] == c019 and not maps[t]["codes"]], key=lambda t: (gold[t], t))
    for t in [x for x in B if gold[x] == 0][:3] + [x for x in B if gold[x] == 1][:3]:
        cases.append(row(t, "B", f"cand-019 (bare one-line docstrings; gold-gen {ggen[c019]:.2f}, 10th of 12) — no code fired; {'passed' if gold[t] else 'failed, missed ' + ', '.join(missed(t))}. Its incidence is 0.78 against 0.92–1.00 for the rest, which is why incidence ranks it first"))
    # C. open reader adds beyond the panel
    C = sorted([t for t in maps if any(v == ["open"] for v in maps[t]["source"].values()) and len(maps[t]["codes"]) >= 2], key=lambda t: t)
    for t in C[:4]:
        only_open = [k for k, v in maps[t]["source"].items() if v == ["open"]]
        cases.append(row(t, "C", f"open reader alone supplies {', '.join(only_open)}; panel agreed on {', '.join(k for k, v in maps[t]['source'].items() if 'panel' in v) or 'nothing'}; {'pass' if gold[t] else 'fail'}"))
    # D. failing, silent
    D = sorted([t for t in maps if gold[t] == 0 and not maps[t]["codes"] and maps[t]["candidate_id"] != c019])
    for t in D[:4]:
        cases.append(row(t, "D", f"{alias[maps[t]['candidate_id']]} fails with no code; missed {', '.join(missed(t))}"))
    # E. contained firings: all firings at turns <= 2, later turns clean
    def contained(t):
        s = steps(t); return s and max(x for x, _ in s) <= 2
    E = sorted([t for t in maps if contained(t) and len(maps[t]["codes"]) >= 2], key=lambda t: (gold[t], t))
    for t in [x for x in E if gold[x] == 0][:2] + [x for x in E if gold[x] == 1][:2]:
        cases.append(row(t, "E", f"firings only at turns {sorted({x for x, _ in steps(t)})}, hop-2/hop-3 queries clean → contained; {'pass' if gold[t] else 'fail, missed ' + ', '.join(missed(t))}"))
    categories = {
        "A": ("top candidates, passing, 3+ codes", "the three best instruction sets by gold-gen carry three or more codes on runs that retrieved every gold title"),
        "B": ("cand-019, no code", "the bare-docstring candidate: fewest form violations, 10th of 12 on gold — the candidate that makes incidence negative"),
        "C": ("open reader alone", "codes the taxonomy-holding panel did not agree on but the blind reader's problem mapped to"),
        "D": ("failing, no code", "runs that missed a gold title with nothing the judge could name"),
        "E": ("contained firings", "everything fired at turns 1–2 with hop-2/hop-3 clean, on a pass and on a fail — what containment credits as recovery"),
    }
    intro = ("Twelve optimizer-proposed instruction sets, tax-10, panel judge (`map-5`, `map-6`), 100 judged tasks, gold-gen on the 500-task "
             "domain. No trace method tracks gold here (amplitude −0.091, incidence −0.345, containment +0.323 vs gold-gen on the 100).")
    extra = ("## What the cases say\n\n"
             "Something fires on 1,149 of 1,200 traces (583 of 615 passing ones), so incidence is 0.92–1.00 for eleven candidates and "
             "cannot order them; the twelfth, cand-019, runs the bare one-line docstrings the optimizer started from, breaks the fewest "
             "output-form expectations (incidence 0.78) and is 10th of 12 on gold — hence incidence's negative tau (B). The A cases show "
             "the other side: the best instruction sets are long and prescriptive, and their runs carry three to five codes while "
             "retrieving every title. The codes (output form breach, missing required part, missing closing marker, work state "
             "misjudged) describe how the module writes; gold is decided by which pages the harness returns. C shows the blind reader "
             "adding codes the panel did not agree on; D the failures with nothing to quote; E what containment credits.")
    write_folder("gepa-candidates_hover", "hover / GEPA_candidates — cases", intro, categories, cases, trace_view, judge_view, extra)


lcb(); hover_models(); hover_gepa()
(OUT / "README.md").write_text("""# analysis — traces worth reading

Three folders, one per (benchmark, candidate set). Each holds 20–30 traces chosen because the
judge's reading of them says something about why the trace methods rank the candidates well
(livecodebench) or not at all (hover): points on passing runs, failing runs with no point,
codes that fire on winners and losers alike, firings that later steps carried or did not.

| folder | benchmark · candidates | judge | what to look for |
|---|---|---|---|
| `livecodebench_model/` | livecodebench · 9 models | pointjudge-2, tax-2 | the pass/fail asymmetry that makes amplitude work, and its edges |
| `model_hover/` | hover · 9 models | pointjudge-1-sp15 + pointjudge-3, tax-15 | form codes on passing runs; retrieval misses with nothing to quote |
| `gepa-candidates_hover/` | hover · 12 instruction sets | map-5 + map-6, tax-10 | near-universal firing; the one clean candidate ranking backwards |

Each folder: `README.md` (categories, one row per case with the observation), `cases.json`
(the same, machine-readable), `traces/<trace_id>.json` (the trace as the judge saw it),
`judge/<trace_id>.json` (the judge's record for it — points with step, evidence and codes, or
the panel's votes by turn and the open reader's problems). Selection is deterministic and is
reproduced by `code/select_analysis_cases.py`; it reads gold only to choose cases, which is the
point of the folder.
""")
print("done")
