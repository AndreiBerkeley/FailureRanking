# Plain GEPA on HoVer

This experiment generates a fresh pool of HoVer candidate programs with
ordinary GEPA. It deliberately contains no AdaMAST integration, failure
taxonomy, failure annotation, recovery judge, or failure-based candidate
selection. HoVer's gold supporting-document information is used only by GEPA's
standard optimization metric and is kept separate from the later failure-based
evaluation.

The implementation adapts the three-hop BM25/DSPy HoVer program from the
official MIT-licensed
[`gepa-ai/gepa-artifact`](https://github.com/gepa-ai/gepa-artifact).

## Baseline design

- Three-hop HoVer examples only.
- Deterministic, disjoint split: 100 optimization tasks, 100 Pareto-validation
  tasks, and 300 reserved test tasks by default.
- Plain GEPA with Pareto parent selection and merging disabled.
- Stop when 12 unique candidates occupy at least one per-task validation
  frontier position.
- Safety bounds: at most 8,000 metric calls or 40 candidate proposals.
- Export every accepted candidate, its instructions, parent lineage,
  validation score, and Pareto membership. The reserved test set is not
  evaluated during candidate generation.

The frontier target is the intended stopping condition. The two safety bounds
matter because a stochastic run is not guaranteed to discover twelve accepted
frontier candidates.

## Installation

```bash
cd /Users/andreicojocaru/Desktop/certification_analysis/experiments/hover_gepa_baseline
uv sync
```

The environment is pinned to `gepa==0.1.1`, `dspy==3.3.0`,
`datasets==3.6.0`, `huggingface-hub==0.33.0`, and Python 3.11.
DSPy 3.3.0 requires this GEPA version; it includes the stopping and result APIs
used by this experiment. The Hub pin preserves support for the canonical HoVer
dataset loader used by the official GEPA artifact.

## Prepare retrieval data

```bash
uv run hover-gepa-prepare
```

This downloads the Wikipedia abstracts corpus and builds the deterministic
BM25 index. Based on the previous HoVer setup, allow approximately 24 GB for
the extracted corpus and index and expect indexing to take time. The command
is idempotent and skips completed artifacts.

## Run

The defaults reproduce the selected Bedrock model pair with dated identifiers:

- task rollouts: `bedrock/converse/us.anthropic.claude-haiku-4-5-20251001-v1:0`;
- GEPA reflection: `bedrock/converse/us.anthropic.claude-sonnet-4-5-20250929-v1:0`.

Credentials remain in the environment and are never written to the run
configuration. `GEPA_TASK_MODEL`, `GEPA_REFLECTION_MODEL`, or the corresponding
CLI flags can override the defaults.

```bash
uv run hover-gepa-baseline
```

Important overrides are explicit CLI flags:

```bash
uv run hover-gepa-baseline \
  --target-frontier-candidates 12 \
  --max-metric-calls 8000 \
  --max-proposals 40 \
  --train-size 100 \
  --val-size 100 \
  --test-size 300 \
  --seed 0
```

Each run is written beneath `runs/`. `candidate_manifest.json` is the main
handoff artifact for the later failure annotation and scoring stages. Candidate
program states are JSON files and can be loaded into the same
`HoverMultiHop` architecture without unsafe pickle loading.

## Validation without paid model calls

```bash
uv run python -m unittest discover -s tests -v
uv run hover-gepa-baseline --help
```
