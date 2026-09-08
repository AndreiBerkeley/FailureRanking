# The dataset and its evaluator

## The task

Every task is a three-hop claim verification problem from
[HoVer](https://hover-nlp.github.io/), a multi-hop fact verification dataset
built on Wikipedia. A claim is stated whose verification requires combining
facts from several distinct Wikipedia articles. Example:

> The first year head coach of the 2012-13 Rhode Island Rams men's basketball
> team, is the brother of Robert Matthew Hurley, head coach of Arizona State's
> highest ranked men's basketball team.

Verifying this requires finding three specific articles: *Dan Hurley*,
*Bobby Hurley*, and *2012-13 Rhode Island Rams men's basketball team*. Those
titles are the task's answer key.

The candidate systems are retrieval pipelines. Each performs exactly three
retrieval hops over Wikipedia abstracts and returns everything it retrieved.
The system is not asked to output a verdict; it is asked to find the evidence.

## What the evaluator measures

**A run scores 1.0 if the retrieved documents include every required title,
and 0.0 otherwise.** It is all-or-nothing recall of the required evidence set.
Missing one of three required articles scores the same as missing all three.

This is an objective, deterministic, programmatic check against the dataset's
own answer key. There is no model judgment in it, so the scores are exactly
reproducible and carry no evaluator noise of their own.

Worked example. A run on the claim above retrieves *Dan Hurley*,
*Bobby Hurley*, and eleven other articles, but not the *2012-13 Rhode Island
Rams* article. Two of three required titles are present. The score is **0.0**.

The strictness matters when reading the results: candidate success rates sit
between 0.48 and 0.64 not because the systems are broken, but because
retrieving all three required articles in three hops is genuinely hard, and
partial credit does not exist.

## Files

### `tasks.jsonl`

One line per task, 300 lines.

```json
{"task_id": "001f342b-...", "claim": "The first year head coach ...",
 "required_titles": ["Dan Hurley", "Bobby Hurley", "2012-13 Rhode Island ..."]}
```

`task_id` is the identifier used everywhere else in the package.

### `outcomes.jsonl`

One line per evaluated run, 6,000 lines: 12 candidates times 300 tasks at
repeat 0, plus 12 candidates times 50 tasks at repeats 1 through 4.

```json
{"candidate": 0, "task_id": "001f342b-...", "repeat": 0, "score": 1.0}
```

`repeat` distinguishes independent executions of the same candidate on the
same task. Repeats exist only for the 50 evidence tasks and are what makes the
cross-seed validation target possible.

**These scores are the answer key.** They are used to build the validation
targets, and, for the configurations that declare it, as optional training
feedback on the 50 evidence tasks only. They are never used to build the
validation targets and the score from the same observations: the held-out
target uses 250 tasks that no scoring path touches, and the cross-seed target
uses repeats 1 through 4, while scoring only ever sees repeat 0.

### `splits.json`

The partition actually used: 50 `evidence_tasks` and 250 `heldout_tasks`.
See `../setup/SETUP.md` for why the split is shaped this way.

### `build_dataset.py`

How these three files were produced from the original evaluation run. Shipped
for provenance; you do not need to run it, and it requires the source run,
which is not part of this package.

## Provenance and licence

Claims and required-title answer keys derive from the public HoVer dataset.
The candidate systems, their executions, and the resulting scores were produced
for this work. HoVer is distributed under its own terms; consult the dataset's
own page before redistribution.
