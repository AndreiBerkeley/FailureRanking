#!/usr/bin/env bash
# Command 2 of 2: fill the TAXONOMY pool of all three benchmarks over OpenRouter, same model.
# Needs OPENROUTER_API_KEY in this shell. Resumable: rerun the same command after any interruption.
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is not set in this shell}"
HOVER_PY=/Users/andreicojocaru/Desktop/GEPA_Experiments/.venv/bin/python
ART_PY=legacy/trials/2026-08-25-gepa-cross-benchmark-candidates/.venv/bin/python
SLUG=google/gemini-3.1-flash-lite
echo "checking that OpenRouter lists $SLUG (free call)"
python3 pipeline/tools/openrouter_probe.py --grep gemini-3.1-flash-lite | grep -q "$SLUG" || { echo "OpenRouter does not list $SLUG; pick the right slug and edit SLUG"; exit 1; }
MODEL=openrouter/$SLUG
mkdir -p data/hover/traces/_incoming data/ifbench/traces/_incoming data/hotpotqa/traces/_incoming
echo "[1/3] hover taxonomy: 12 x 50 x 1 = 600 rollouts"
$HOVER_PY data/hover/scripts/capture_pool.py --split taxonomy --repeats 1 --workers 12 --emit-corpus --task-model $MODEL 2>&1 | tee -a data/hover/traces/_incoming/pools-1-taxonomy.log
echo "[2/3] ifbench taxonomy: 12 x 300 x 1 = 3,600 rollouts"
$ART_PY data/scripts/capture_artifact_pool.py --benchmark ifbench --portion taxonomy --repeats 1 --workers 8 --task-model $MODEL 2>&1 | tee -a data/ifbench/traces/_incoming/pools-1-taxonomy.log
echo "[3/3] hotpotqa taxonomy: 12 x 200 x 1 = 2,400 rollouts"
$ART_PY data/scripts/capture_artifact_pool.py --benchmark hotpotqa --portion taxonomy --repeats 1 --workers 8 --task-model $MODEL 2>&1 | tee -a data/hotpotqa/traces/_incoming/pools-1-taxonomy.log
echo "taxonomy pools captured for all three benchmarks"
