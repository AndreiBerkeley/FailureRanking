# FailureRank

Ranking candidate agent systems from the failure evidence in their execution
traces, without reading any answer key.

## The question

Given several versions of an agent system and a limited number of evaluated
tasks, which version is best? The usual answer is to count how often each one
succeeded. That uses one bit per task and ignores everything the traces record
about how the systems actually behaved.

This package asks whether the failures visible in the traces carry more
information than the outcomes do. A trace judge reads each execution and
records which failure modes occurred, from a fixed taxonomy. A scoring pipeline
turns those findings into a candidate ranking. No answer key is used anywhere
in the scoring path; the answer key is used only afterwards, to check whether
the ranking was right.

## The result

Twelve candidate systems, 50 evaluated tasks of trace evidence each. Ranking
quality is measured against two things the scoring never saw: how the same
candidates rank when re-run on four fresh seeds, and how they rank on 250
unseen tasks. Kendall tau, where +1 is a perfect ordering and 0 is chance.

| ranking built from the same 50 tasks | four fresh seeds | 250 unseen tasks |
| --- | :-: | :-: |
| the evaluator's own success rate | +0.53 | +0.41 |
| failure evidence, simplest useful method | **+0.85** | **+0.73** |

Failure evidence orders the candidates substantially better than outcomes do,
at an identical evidence budget.

## What is in here

| directory | contents |
| --- | --- |
| `dataset/` | the 300 tasks, the evaluator's scores, the split, and what the evaluator measures |
| `setup/` | how the experiment was set up: candidates, judge, taxonomy, what was blind to what |
| `pipeline/` | the program: judge findings in, ranking out |
| `experiments/` | one script that regenerates every number reported here, and the results |
| `traces/` | the 600 judged execution traces, for inspection |
| `METHOD.md` | how ranking quality is measured, and what these numbers can and cannot support |

Start with `setup/SETUP.md` for the experimental design, `pipeline/MODULES.md`
for what the scoring pipeline is made of, and `experiments/RESULTS.md` for the
results with explanations.

## Running it

Score the shipped judge findings and print a ranking:

```bash
cd pipeline
python -m core.run --mapping ../setup/judge_mapping.json --out /tmp/ranking.json
```

Regenerate every reported number, including the full option grid:

```bash
cd experiments
python run_all.py
```

Both are pure offline computation over the shipped files. Python 3.10 or
newer, no third-party dependencies.

## Scope and honesty

Twelve candidates is a small field, and both validation targets are themselves
estimated from a finite number of binary outcomes. The headline comparison is
far larger than that noise; fine distinctions between the better scoring
configurations are not. `METHOD.md` states precisely what the numbers support.

The task claims come from the public HoVer dataset. The judge, the taxonomy and
the recovery analysis are replaceable instruments, not the contribution; the
contribution is the evidence-to-ranking method and its validation.
