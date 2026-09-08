#!/usr/bin/env bash
# Fill the GENERALIZATION pools of hotpotqa (all 400) and ifbench (400 in total) over OpenRouter, same model.
# Needs OPENROUTER_API_KEY in this shell. Resumable: rerun the same command after any interruption.
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is not set in this shell}"
ART_PY=legacy/trials/2026-08-25-gepa-cross-benchmark-candidates/.venv/bin/python
MODEL=openrouter/google/gemini-3.1-flash-lite
mkdir -p data/ifbench/traces/_incoming data/hotpotqa/traces/_incoming
echo "[1/2] hotpotqa generalization: 12 x 400 x 1 = 4,800 rollouts"
$ART_PY data/scripts/capture_artifact_pool.py --benchmark hotpotqa --portion generalization --repeats 1 --workers 8 --task-model $MODEL 2>&1 | tee -a data/hotpotqa/traces/_incoming/pools-1-generalization.log
echo "[2/2] ifbench generalization: 12 x 400 x 1 = 4,800 rollouts"
$ART_PY data/scripts/capture_artifact_pool.py --benchmark ifbench --portion generalization --repeats 1 --workers 8 --task-model $MODEL 2>&1 | tee -a data/ifbench/traces/_incoming/pools-1-generalization.log
echo "generalization pools captured for hotpotqa and ifbench"
