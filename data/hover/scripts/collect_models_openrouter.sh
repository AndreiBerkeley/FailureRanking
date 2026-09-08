#!/usr/bin/env bash
# Capture the models-1 candidate set (one fixed prompt, ten solver models) on every portion of the
# models-1 split: taxonomy 600, judging 500, generalization 500 tasks x 10 models = 16,000 rollouts.
# Reasoning is disabled per model where the endpoint allows it (probed once per model). Resumable:
# a (candidate, task, repeat) already on disk is skipped, so rerunning after an interruption is free.
set -euo pipefail
cd "$(dirname "$0")/../../.."
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is not set in this shell}"
PY=/Users/andreicojocaru/Desktop/GEPA_Experiments/.venv/bin/python
WORKERS="${WORKERS:-12}"
mkdir -p data/hover/traces/_incoming
for portion in taxonomy judging generalization; do
  echo "=== ${portion} ==="
  $PY data/hover/scripts/capture_models.py --set models-1 --portion "$portion" --workers "$WORKERS" 2>&1 \
    | tee -a "data/hover/traces/_incoming/models-1-${portion}.log"
done
echo "models-1 captured on all three portions"
