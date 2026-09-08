# The program

One command turns judge findings into a candidate ranking.

```bash
cd pipeline
python -m core.run --mapping ../setup/judge_mapping.json --out ranking.json
```

```
benchmark: hover-adapter15   scenario-1: False   (higher score = better)
  rank  1.0  candidate    2  score -1.0400
  rank  2.0  candidate    9  score -1.2400
  ...
```

## Input

A **mapping**: candidates, their tasks, and the failure records the judge found
on each. Only `code` is required per record; anything else is carried through
untouched for modules that use it.

```json
{
  "schema_version": 1,
  "benchmark": "any label you like",
  "candidates": {
    "candidate_id": {
      "task_id": [
        {"code": "B.6", "severity": "moderate", "outcome_link": "direct"},
        {"code": "A.8", "severity": "critical", "outcome_link": "likely"}
      ]
    }
  }
}
```

Candidate and task identifiers are opaque strings. Nothing in the pipeline is
specific to this benchmark, this judge, or this taxonomy.

To convert a judge artifact in the original internal format instead:

```bash
python -m core.run --adapter15 <stage1.json> --traces <traces dir> \
                   --save-mapping mapping.json --out ranking.json
```

## Output

```json
{"benchmark": "...", "config": {...}, "scenario_1": false,
 "ranking_convention": {"direction": "higher_is_better", "ties": "average_rank"},
 "scores": {"2": -1.04, "9": -1.24},
 "ranking": [{"candidate": "2", "score": -1.04, "rank": 1.0}]}
```

**Higher score is better**, so scores read in the same direction as success
rates. Exact ties share their average rank. `scenario_1` records whether the
configuration consumed training outcomes; when it is false, nothing but the
judge findings entered the score.

Scores can be negative. That is not an error: the default configuration adds up
failure evidence without a ceiling, so a task carrying three failure modes
scores below zero on the quality scale. Orderings are unaffected, and the
negative values are a visible reminder that the default applies no within-task
cap. Configurations that use a bounded formula produce scores inside 0 to 1.

## Choosing modules

Every stage of the pipeline is a replaceable module. List what is available:

```bash
python -m core.run --list-options
```

Select them with a small JSON file:

```json
{"counting": "unique", "relationships": "none",
 "trust": "ol_gate_likely", "formula": "uncapped_sum"}
```

```bash
python -m core.run --mapping ../setup/judge_mapping.json \
                   --config myconfig.json --out ranking.json
```

`trust` and `feedback` are optional; omit either to skip that stage. The
remaining three are required. `MODULES.md` explains what each one does and when
to choose it.

## Using training outcomes

Some feedback modules learn from evaluated outcomes on the evidence tasks. Pass
them explicitly:

```bash
python -m core.run --mapping ../setup/judge_mapping.json --config myconfig.json \
                   --gold ../dataset/training_outcomes.json --out ranking.json
```

The file maps candidate to task to outcome. Without it, any configuration
requesting a gold module is **skipped rather than silently downgraded**, and the
output records `scenario_1: true` whenever such a module was used, so a
gold-free claim can never be made by accident.

## Optional preprocessing

```bash
--resolution categories   # collapse codes to their A/B/C family before scoring
--resolution severity     # replace codes by the judge's severity label
```

Both rewrite the mapping before the pipeline runs, so they compose with every
module without enlarging the option space.

## Requirements

Python 3.10 or newer. No third-party packages. All computation is offline over
local files; no network access and no model calls.

Run the test suites from the `pipeline` directory:

```bash
python -m core.test_core && python -m core.test_options && \
python -m core.test_run  && python -m core.test_trust && python -m core.test_feedback
```
