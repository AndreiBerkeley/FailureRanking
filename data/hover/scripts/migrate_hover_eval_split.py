#!/usr/bin/env python3
"""Duplicate the evaluation split and the candidates' traces on it: the 50-task
sample and the 500-task domain portions of benchmarks/hover/splits/split-3,
captured as traces-3/judging and traces-3/generalization. Writes split eval-1,
captures cap-2 and cap-3, their outcomes, and grows the task registry.

Requires migrate_hover_from_benchmarks.py to have run (it needs the candidate
registry). Read-only on benchmarks/. Refuses to overwrite cap-2 or cap-3.
"""
from __future__ import annotations

import datetime
import sys

from hoverlib import (NEW, OLD, TODAY, jdump, jload, load_registry, log, migrate_capture, provenance,
                      split2_records, write_capture_readme, write_outcomes, write_outcomes_readme,
                      write_tasks, write_tasks_readme)

SCRIPT = "data/hover/scripts/migrate_hover_eval_split.py"
SPLIT = "eval-1"
T3 = OLD / "traces" / "traces-3"
PORTIONS = {  # new name: (split-3 name, source dir, capture id, size)
    "sample": ("judging", T3 / "judging", "cap-2", 50),
    "domain": ("generalization", T3 / "generalization", "cap-3", 500),
}


def main() -> None:
    for _, (_, _, cap, _) in PORTIONS.items():
        if (NEW / "traces" / cap).exists():
            sys.exit(f"{cap} already exists; captures are append-only")
    _, by_alias = load_registry()
    rec = split2_records()
    s3 = jload(OLD / "splits" / "split-3" / "split.json")
    gepa = jload(NEW / "splits" / "gepa-1" / "split.json")
    gepa_ids = set(gepa["portions"]["train"]) | set(gepa["portions"]["validation"])

    log("split")
    portions = {new: list(s3["portions"][old]) for new, (old, _, _, _) in PORTIONS.items()}
    ids = {new: set(v) for new, v in portions.items()}
    assert len(ids["sample"]) == 50 and len(ids["domain"]) == 500
    assert not (ids["sample"] & ids["domain"]), "sample and domain overlap"
    assert not ((ids["sample"] | ids["domain"]) & gepa_ids), "eval-1 overlaps the optimizer's split"
    jdump({"benchmark": "hover", "split_id": SPLIT,
           "purpose": "evaluation: a small sample to read closely and a large held-out domain to generalise to",
           "portions": portions, "sizes": {k: len(v) for k, v in portions.items()},
           "seed": s3["seed"], "protocol": s3["protocol"], "source": gepa["source"],
           "disjoint_from": ["gepa-1"],
           "old_names": {"sample": "split-3 'judging'", "domain": "split-3 'generalization'"},
           "note": "both portions were drawn from tasks the optimizer never saw; 350 further unused tasks remain in split-3 'spare'"},
          NEW / "splits" / SPLIT / "split.json")
    jdump(provenance(SPLIT, "task split", ["benchmarks/hover/splits/split-3/split.json"],
                     {"sample": 50, "domain": 500},
                     {"portions_disjoint": True, "disjoint_from_gepa_1": True}, SCRIPT),
          NEW / "splits" / SPLIT / "provenance.json")
    (NEW / "splits" / SPLIT / "README.md").write_text(f"""# {SPLIT} — the evaluation split

Two portions of tasks the optimizer never saw, disjoint from each other and
from `gepa-1`:

| portion | tasks | role |
|---|---:|---|
| `sample` | 50 | the small set a candidate is read closely on: every trace judged |
| `domain` | 500 | the large held-out set the sample is supposed to speak for |

The question the project asks is whether what is read on `sample` holds on
`domain`. Nothing about `domain` may be used to build an instrument or a
formula; it is only ever the target.

Copied without reordering from `benchmarks/hover/splits/split-3`, where the
portions were called `judging` and `generalization`. Same seed and protocol as
that split. A further 350 tasks from the same draw remain unused there.
""")

    all_claims, all_gold, portions_of = {}, {}, {}
    for new, (old, src, cap, size) in PORTIONS.items():
        log(f"traces {cap} ({old} -> {new})")
        captured_on = datetime.date.fromtimestamp((src / "outcomes.json").stat().st_mtime).isoformat()
        r = migrate_capture(src=src, capture_id=cap, split_id=SPLIT, portions=[new],
                            allowed_tasks=ids[new], rec=rec, by_alias=by_alias, expected_tasks=size,
                            captured_on=captured_on,
                            derives_from=[str(src.relative_to(OLD.parent.parent)), "benchmarks/hover/pools/pool-3",
                                          "benchmarks/hover/splits/split-3"],
                            script=SCRIPT, description=f"pool-3 on the {new} portion of {SPLIT}, one run each")
        n_traces = len(r["index_rows"])
        write_capture_readme(cap, f"pool-3 on the {new} portion, one run each", f"""12 candidates (set `pool-3`) × {size} tasks (split `{SPLIT}`, portion `{new}`) × 1
repeat = {n_traces:,} traces. Solver `gemini/gemini-3.1-flash-lite`. Captured
{captured_on} as `benchmarks/hover/traces/traces-3/{old}`; duplicated here on
{TODAY} with every identity re-keyed to the registries and verified by hash.

| file | what it is |
|---|---|
| `manifest.json` | what was run, what was expected, what is present, audit results |
| `index.jsonl` | one row per trace: ids, status, call count, cost, body hash |
| `bodies/<candidate_id>.jsonl.gz` | the traces, one candidate per file, one trace per line |
| `program_states/<candidate_id>.json` | the DSPy program state that ran, as saved by the runner |

A body holds the full run record and, under `judge_view`, the outcome-blind
message list exactly as it was emitted for judging. No gold appears anywhere in
this directory; scores are in `../../outcomes/{cap}.jsonl`.

{"Every trace here has been judged under both taxonomies: see `../../mappings/`." if new == "sample" else "About a third of these traces have been judged under each taxonomy so far: see `../../mappings/`."}
""")
        all_claims.update(r["claims"])
        all_gold.update(r["gold_by_task"])
        portions_of.update({t: [f"{SPLIT}/{new}"] for t in ids[new]})
        write_outcomes(cap, r["outcome_rows"], [f"data/hover/traces/{cap}", "data/hover/tasks/tasks.jsonl"], SCRIPT)

    log("tasks")
    n = write_tasks(all_claims, all_gold, rec, portions_of, SCRIPT,
                    ["benchmarks/hover/splits/split-2/split.json", "benchmarks/hover/traces/traces-3/generation",
                     "benchmarks/hover/traces/traces-3/judging", "benchmarks/hover/traces/traces-3/generalization"])
    write_tasks_readme()
    write_outcomes_readme()
    log(f"done: tasks now {n}")


if __name__ == "__main__":
    main()
