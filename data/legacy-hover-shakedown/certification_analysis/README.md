# Certification Analysis

`certification_analysis` is a research prototype for taxonomy-grounded,
binary certification of agentic task executions. It does not require a gold
answer or a task-specific evaluator at inference time. Instead, it combines:

1. a structured understanding of the task;
2. the evolution and recovery status of detected failure instances; and
3. an analysis of whether unresolved failures invalidate required task
   conditions.

The result is a binary certificate relative to the supplied failure taxonomy.

## Current scope

The repository implements the three-phase pipeline and its validation rules.
It assumes that an upstream detector has already mapped accurate failure codes
to locations in the trace. A pluggable `Judge` performs the semantic analysis
inside each phase.

The prototype deliberately separates the judge from the certification logic:

- `ScriptedJudge` reads fixed phase responses and makes examples and tests
  reproducible.
- `CommandJudge` invokes any external program that accepts a JSON request on
  standard input and returns a JSON response on standard output.

No model provider is required by the core package.

## Pipeline

### Phase 1: Task understanding

The judge receives only the task. It produces the requested outcome, required
conditions, constraints, deliverables, dependencies, and ambiguities. It must
describe what success requires without prescribing a particular solution path.

### Phase 2: Failure evolution

The judge receives the trace and raw failure mapping. Each failure instance is
classified as either:

- `recovered`: both the direct error and its downstream effects were
  neutralized; or
- `unresolved`: some effect remains at the end of the trace.

The phase records recovery steps, causal parents, propagated effects, residual
effects, and supporting trace evidence. It does not decide whether the task
succeeded.

### Phase 3: Requirement impact and certification

The judge compares unresolved failure instances with the Phase 1 task
conditions. It decides which conditions were invalidated and identifies
unresolved failures that do not affect any required condition.

The application—not the judge—derives the final certificate:

- `failure` if an unresolved failure invalidates at least one required
  condition;
- `success` otherwise.

This makes the final aggregation rule explicit and testable.

## Quick start

The package has no runtime dependencies.

```bash
cd /Users/andreicojocaru/Desktop/certification_analysis
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
certification-analysis analyze \
  --input examples/sample_input.json \
  --responses examples/sample_responses.json
```

The example intentionally contains one recovered implementation failure and
one unresolved solution failure. The unresolved failure invalidates a required
task condition, so the final certificate is `failure`.

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

## Input format

```json
{
  "task": {
    "id": "task-1",
    "description": "Natural-language task description"
  },
  "trace": [
    {
      "step": 1,
      "actor": "agent",
      "action": "What the agent did",
      "observation": "What happened"
    }
  ],
  "failure_events": [
    {
      "id": "failure-1",
      "mode": "taxonomy_failure_code",
      "step": 1,
      "evidence": "Why the upstream detector fired this code"
    }
  ]
}
```

Additional fields are preserved under `metadata` where supported.

## External judge protocol

Pass an external command with `--judge-command`:

```bash
certification-analysis analyze \
  --input path/to/input.json \
  --judge-command "python path/to/judge_adapter.py"
```

For every phase, the command receives one JSON object on standard input:

```json
{
  "phase": "phase1",
  "instructions": "...",
  "payload": {},
  "response_schema": {}
}
```

It must print exactly one JSON object matching `response_schema`. The command
is invoked without a shell.

Use this interface to connect an LLM, a local model, or a human-in-the-loop
annotation tool without changing the certification pipeline.

## Research limitations

- A certificate is only as complete as the taxonomy's coverage.
- The current version treats failure evolution as a deterministic state
  analysis over one trace. Transition probabilities across many traces are a
  future reliability layer.
- Task decomposition, recovery analysis, and requirement impact remain
  judge-dependent research problems.
- The pipeline does not claim formal correctness beyond the supplied taxonomy
  and trace evidence.

## Planned extensions

- model-specific judge adapters with schema-constrained output;
- failure-effect graphs spanning root causes, propagation, and recovery;
- corpus-level transition models over failure-effect states;
- reliability estimates conditioned on task specifications;
- evaluation against tasks with independently established outcome labels.

## HoVer candidate-generation baseline

The plain-GEPA HoVer experiment used to generate candidate programs for the
comparative-evaluation study lives in
[`experiments/hover_gepa_baseline`](experiments/hover_gepa_baseline). It is an
independent environment: GEPA receives the ordinary HoVer retrieval metric and
textual feedback, while no failure taxonomy or failure judge participates in
candidate generation.
