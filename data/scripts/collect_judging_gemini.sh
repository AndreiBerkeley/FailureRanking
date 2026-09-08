#!/usr/bin/env bash
# Command 1 of 2: fill the JUDGING pool of all three benchmarks over the direct Gemini route.
# Needs GEMINI_API_KEY in this shell. Resumable: rerun the same command after any interruption.
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${GEMINI_API_KEY:?GEMINI_API_KEY is not set in this shell}"
HOVER_PY=/Users/andreicojocaru/Desktop/GEPA_Experiments/.venv/bin/python
ART_PY=legacy/trials/2026-08-25-gepa-cross-benchmark-candidates/.venv/bin/python
MODEL=gemini/gemini-3.1-flash-lite
mkdir -p data/hover/traces/_incoming data/ifbench/traces/_incoming data/hotpotqa/traces/_incoming
echo "[1/3] hover judging: 12 x 450 x 1 = 5,400 rollouts"
$HOVER_PY data/hover/scripts/capture_pool.py --split judging --repeats 1 --workers 12 --emit-corpus --task-model $MODEL 2>&1 | tee -a data/hover/traces/_incoming/pools-1-judging.log
echo "[2/3] ifbench judging: 12 x 400 x 1 = 4,800 rollouts"
$ART_PY data/scripts/capture_artifact_pool.py --benchmark ifbench --portion judging --repeats 1 --workers 8 --task-model $MODEL 2>&1 | tee -a data/ifbench/traces/_incoming/pools-1-judging.log
echo "[3/3] hotpotqa judging: 12 x 50 x 1 = 600 rollouts"
$ART_PY data/scripts/capture_artifact_pool.py --benchmark hotpotqa --portion judging --repeats 1 --workers 8 --task-model $MODEL 2>&1 | tee -a data/hotpotqa/traces/_incoming/pools-1-judging.log
echo "judging pools captured for all three benchmarks"
