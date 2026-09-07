#!/usr/bin/env bash
# Watch both pool captures. Completion = converted pool directory populated.
R=/Users/andreicojocaru/Desktop/FailureRank
deadline=$(( $(date +%s) + 5400 ))
while :; do
  done_ct=0; rep=""
  alive=$(pgrep -f "run_measurement.py" | wc -l | tr -d ' ')
  for b in livebenchmath hotpotqa; do
    P="$R/runs/pipeline/$b/pool"
    RAW="$R/runs/pipeline/$b/pool_raw"
    n=$(ls "$P" 2>/dev/null | wc -l | tr -d ' '); n=${n:-0}
    if [[ "$n" -gt 0 ]]; then done_ct=$((done_ct+1)); rep+="$b:pool($n) "; continue; fi
    s=$(ls "$RAW/records" 2>/dev/null | wc -l | tr -d ' '); s=${s:-0}
    if grep -q "Traceback" "$RAW/capture.log" 2>/dev/null; then
      echo "POOL WATCHER: $b FAILED"; grep -A5 Traceback "$RAW/capture.log" | tail -12; exit 1; fi
    # Word-bounded so metric digits like 78.4728013094 cannot masquerade as a
    # 429, and grader warnings (LaTeX parse / SymPy simplify) are counted but
    # never treated as failures: those are the scorer struggling, not the run.
    api=$(grep -coiE "\b(503|429)\b|UNAVAILABLE|RESOURCE_EXHAUSTED|rate limit" "$RAW/capture.log" 2>/dev/null | head -1)
    api=${api:-0}
    warn=$(grep -c "couldn't parse\|trouble simplifying" "$RAW/capture.log" 2>/dev/null | head -1)
    warn=${warn:-0}
    if [[ "$api" -ge 5 ]]; then
      echo "POOL WATCHER: $b has $api API errors, escalating"
      grep -inE "\b(503|429)\b|UNAVAILABLE" "$RAW/capture.log" | tail -5; exit 2; fi
    rep+="$b:${s}/12shards(api=$api,graderwarn=$warn) "
  done
  if [[ $done_ct -eq 2 ]]; then
    echo "POOL WATCHER: BOTH POOLS READY"
    /usr/bin/python3 - <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, "/Users/andreicojocaru/Desktop/FailureRank/pipeline")
from taxonomy import corpora
R = Path("/Users/andreicojocaru/Desktop/FailureRank/runs/pipeline")
for b in ("livebenchmath","hotpotqa"):
    pool = R/b/"pool"
    n = len(list(pool.glob("*.json")))
    tasks = {json.loads(p.read_text())["metadata"]["task_source_id"] for p in pool.glob("*.json")}
    fails = sum(1 for p in pool.glob("*.json")
                if json.loads(p.read_text())["metadata"].get("outcome_score", 1.0) < 1.0)
    print(f"\n=== {b}: {n} traces / {len(tasks)} tasks / {fails} failing ({fails/max(n,1):.0%})")
    for N in (200, 120):
        try:
            m = corpora.plan(pool, N).manifest
            print(f"  N={N}: gen {m['generation']['traces']}/{m['generation']['tasks']}t "
                  f"| ref {m['refinement']['traces']}/{m['refinement']['tasks']}t "
                  f"| gate {m['gate']['traces']}/{m['gate']['tasks']}t  OK")
        except SystemExit as e:
            print(f"  N={N}: refused ({str(e).split(';')[0]})")
PY
    exit 0
  fi
  if [[ "$alive" -eq 0 && $done_ct -lt 2 ]]; then
    echo "POOL WATCHER: captures stopped without completing. $rep"; exit 1; fi
  [[ $(date +%s) -gt $deadline ]] && { echo "POOL WATCHER: deadline. $rep"; exit 1; }
  sleep 90
done
