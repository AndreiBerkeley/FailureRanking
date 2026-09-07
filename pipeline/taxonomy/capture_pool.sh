#!/usr/bin/env bash
# Capture a trace pool large enough for the whole taxonomy pipeline.
#
#   ./capture_pool.sh <benchmark> [n_tasks] [source] [offset]
#
# Capture is ~25x cheaper than judging, so capture wide and let the pipeline
# sample down. Ask taxonomy.corpora.requirements(N) for the task count a given
# N needs before paying for this.
set -uo pipefail
REPO="/Users/andreicojocaru/Desktop/FailureRank"
TRIAL="$REPO/legacy/trials/2026-08-25-gepa-cross-benchmark-candidates"
export PYTHONUNBUFFERED=1
set +u; source ~/.zshrc >/dev/null 2>&1; set -u

B="${1:?usage: $0 <benchmark> [n_tasks] [source] [offset]}"
NTASKS="${2:-100}"
SOURCE="${3:-validation}"
OFFSET="${4:-0}"
RAW="$REPO/runs/pipeline/$B/pool_raw"
OUT="$REPO/runs/pipeline/$B/pool"

if [[ -d "$OUT" && -n "$(ls -A "$OUT" 2>/dev/null)" ]]; then
  echo "[$B] pool already exists: $(ls "$OUT" | wc -l | tr -d ' ') traces"; exit 0
fi
mkdir -p "$RAW"
echo "[$B] capturing $NTASKS $SOURCE tasks (offset $OFFSET) x 12 candidates"
cd "$TRIAL"
"$TRIAL/.venv/bin/python" run_measurement.py \
  --benchmark "$B" --mode generation \
  --generation-source "$SOURCE" --generation-offset "$OFFSET" \
  --generation-tasks "$NTASKS" --repeats 1 --workers 4 \
  --run-dir "$RAW" 2>&1 | tee -a "$RAW/capture.log"

echo "[$B] converting to AdaMAST format"
LINK="$TRIAL/runs/${B}_pool_v1"
[[ -e "$LINK" ]] || ln -s "$RAW" "$LINK"
"$TRIAL/.venv/bin/python" convert_traces_for_adamast.py \
  --benchmark "$B" --scope all --repeats 0 \
  --source-run pool_v1 --out-dir "$OUT" 2>&1 | tail -3
echo "[$B] pool ready: $(ls "$OUT" | wc -l | tr -d ' ') traces"
