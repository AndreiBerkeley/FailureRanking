"""Ten random 50-task subsamples of a judged pool, each scored by run_baselines.py.

    python3 methods/scripts/subsample_50.py --bench livecodebench --pool <pool> --draws 10 <run>

Uniform draws without stratification, random.Random(seed) for seed = 1..draws, from the
tasks the run judged. Each draw is written as a split.json in a scratch directory and
handed to run_baselines.py --tasks; the four-column rows come back unchanged. Free.
"""
import json, random, re, subprocess, sys, tempfile, glob
from pathlib import Path

args = sys.argv[1:]
def opt(name, default=None):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
BENCH = opt("--bench", "livecodebench"); POOL = opt("--pool"); DRAWS = int(opt("--draws", "10")); K = int(opt("--k", "50"))
RUNS = args                                  # one or more judge run dirs, pooled
if BENCH == "hover-pool3" and all(Path(r, "mapping.jsonl").exists() for r in RUNS):
    tasks = sorted({json.loads(l)["task_id"] for r in RUNS for l in open(f"{r}/mapping.jsonl")})
else:                                        # pointjudge runs and their derivations: traces/*.json
    tasks = sorted({json.load(open(f))["task_id"] for r in RUNS for f in glob.glob(f"{r}/traces/*.json")})
print(f"{' + '.join(RUNS)}: {len(tasks)} judged tasks; {DRAWS} uniform draws of {K}\n")
STEPS = True                                  # hover-pool3 steps come from the panel judge_records
METHODS = ["1 gold", "2 amplitude", "3 incidence", "6 combinations"] + (["8 step-amp", "10 containment", "13 last-turn incidence"] if STEPS else [])
rows = []
with tempfile.TemporaryDirectory() as td:
    for seed in range(1, DRAWS + 1):
        draw = sorted(random.Random(seed).sample(tasks, K))
        sp = Path(td) / f"draw{seed}.json"
        sp.write_text(json.dumps({"portions": {"judged": draw}}))
        cmd = [sys.executable, "methods/scripts/run_baselines.py", "--bench", BENCH, "--tasks", str(sp)]
        if POOL: cmd += ["--pool", POOL]
        out = subprocess.run(cmd + RUNS, capture_output=True, text=True).stdout
        got = {}
        for m in METHODS:
            mm = re.search(rf"^\| {re.escape(m)} \| ([+-]?(?:[\d.]+|nan)) \| (yes|no) \|", out, re.M)
            if mm is None: sys.exit(f"draw {seed}: no row for {m}\n" + out[-600:])
            b, top = mm.groups(); got[m] = (b, b, b, top)   # the gold row's value is gold-50 vs gold-gen; nan = every pair tied
        rows.append((seed, got))
short = {"2 amplitude": "amplitude", "3 incidence": "incidence", "6 combinations": "combinations", "8 step-amp": "step-amp", "10 containment": "containment", "13 last-turn incidence": "last-turn"}
cols = METHODS[1:]
print("| draw | gold-50 | " + " | ".join(short[m] for m in cols) + " | top-1 " + " / ".join(short[m][:4] for m in cols) + " |")
print("|---|---:|" + "---:|" * len(cols) + "---|")
acc = {m: [] for m in METHODS}
for seed, g in rows:
    print(f"| {seed} | {g['1 gold'][2]} | " + " | ".join(g[m][1] for m in cols) + " | " + " / ".join(g[m][3] for m in cols) + " |")
    for m in METHODS: acc[m].append((float(g[m][0]), float(g[m][1])))
def mean(xs):
    xs = [x for x in xs if x == x]          # nan (every pair tied) is left out of the mean
    return sum(xs) / len(xs) if xs else float("nan")
print(f"| **mean** | {mean([b for a,b in acc['1 gold']]):+.3f} | " + " | ".join(f"{mean([b for a,b in acc[m]]):+.3f}" for m in cols) + " | |")
beats = {m: sum(1 for (a, b), (_, c3) in zip(acc[m], acc["1 gold"]) if b == b and c3 == c3 and b > c3) for m in cols}
print(f"\ndraws where the method beats gold-50 against gold-gen: " + ", ".join(f"{short[m]} {v}/{DRAWS}" for m, v in beats.items()))
