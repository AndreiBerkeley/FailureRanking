"""Ranking agreement as a function of judged-set size: the ten-draw table at every k.

    python3 methods/scripts/size_sweep.py --bench <bench> [--pool P] --ks 10,20,30,50,75,100,150 --draws 20 <run> [<run> ...]

For each k, `draws` uniform draws of k tasks from the run's judged tasks (subsample_50.py),
every method scored on each draw; reported per k: the mean tau vs gold-gen of gold-k and of
each method, and how many draws each method beats gold-k on. When k equals the pool size
there is one draw (the whole set). Draws at large k overlap heavily, so their spread
shrinks for that reason alone.
"""
import re, subprocess, sys
args = sys.argv[1:]
def opt(name, default=None):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
BENCH = opt("--bench", "livecodebench"); POOL = opt("--pool"); KS = [int(x) for x in opt("--ks", "10,20,30,50,75,100,150").split(",")]
DRAWS = int(opt("--draws", "20")); RUNS = args
header = None; rows = []
for k in KS:
    cmd = [sys.executable, "methods/scripts/subsample_50.py", "--bench", BENCH, "--k", str(k), "--draws", str(DRAWS)]
    if POOL: cmd += ["--pool", POOL]
    out = subprocess.run(cmd + RUNS, capture_output=True, text=True)
    if out.returncode != 0:
        if "larger than" in out.stderr or "Sample larger" in out.stderr: break
        sys.exit(out.stderr[-800:])
    n_tasks = int(re.search(r": (\d+) judged tasks", out.stdout).group(1))
    if k > n_tasks: break
    if k == n_tasks:   # one draw: the whole set
        cmd[cmd.index("--draws") + 1] = "1"
        out = subprocess.run(cmd + RUNS, capture_output=True, text=True)
    lines = out.stdout.splitlines()
    head = next(l for l in lines if l.startswith("| draw |"))
    cols = [c.strip() for c in head.strip("|").split("|")][1:-1]     # gold-50, methods...
    mean = next(l for l in lines if l.startswith("| **mean** |"))
    vals = [c.strip() for c in mean.strip("|").split("|")][1:-1]
    beats = next((l for l in lines if l.startswith("draws where")), "")
    b = dict(re.findall(r"([\w-]+) (\d+/\d+)", beats))       # short method names, one token each
    if header is None:
        header = cols
        print(f"{' + '.join(RUNS)}: {n_tasks} judged tasks; {DRAWS} uniform draws per k (1 at k = {n_tasks})\n")
        print("| k | draws | " + " | ".join(("gold-k" if c == "gold-50" else c) for c in cols) + " | beats gold-k |")
        print("|---:|---:|" + "---:|" * len(cols) + "---|")
    print(f"| {k} | {1 if k == n_tasks else DRAWS} | " + " | ".join(vals) + " | " + ", ".join(f"{m} {b.get(m, '')}" for m in cols[1:]) + " |")
