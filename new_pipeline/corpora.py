#!/usr/bin/env python3
"""Split one trace pool into the three disjoint corpora the pipeline needs.

Splitting is BY TASK, never by trace: a task that appears in the generation
corpus must not reappear in the refinement or gate corpora, or the taxonomy
would be certified on the material it was induced from. Task diversity, not
trace count, is the binding constraint (60 tasks at 2 traces each beat 8 tasks
at 12 on the same judging budget), so the splitter allocates tasks first and
fills traces within them.

Sizes follow PIPELINE.md, with N the generation corpus size:
    generation   N traces, 4 candidates per task, so N/4 tasks
    refinement   N/2 traces, 2 per task (one failing, one passing where both
                 exist), over at least twice the generation task count
    gate         60 traces over >= 30 distinct tasks
"""
from __future__ import annotations

import json
import random
import shutil

from new_pipeline import goldfree
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

GATE_TRACES = 60
GATE_MIN_TASKS = 30
# Refinement tasks are already disjoint from generation, so they need only
# enough tasks to supply N/2 traces at REFINE_PER_TASK each. The old 2x
# multiple dated from when generation itself spanned very few tasks.
REFINE_TASK_MULTIPLE = 1
REFINE_PER_TASK = 2
GEN_PER_TASK = 4      # candidates sampled per generation task


@dataclass
class Split:
    generation: list[Path] = field(default_factory=list)
    refinement: list[Path] = field(default_factory=list)
    gate: list[Path] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)


def _score_of(trace: dict, path: Path, scores: dict | None) -> float:
    """Outcome for STRATIFICATION ONLY. Never rendered into a prompt.

    A sidecar is preferred over trace metadata: a corpus whose traces carry no
    outcome at all is structurally gold-free, which is stronger than stripping
    one that does. hover's capture already separates gold this way.
    """
    if scores is not None:
        tid = trace.get("trace_id") or path.stem
        if tid in scores:
            return float(scores[tid])
    md = trace.get("metadata") or {}
    return float(md.get("outcome_score", 1.0))


def load_outcomes(path: Path | None) -> dict | None:
    """trace_id -> score, from a sidecar written beside the pool."""
    if not path:
        return None
    d = json.loads(Path(path).read_text())
    return {k: float(v) for k, v in (d.get("scores") or d).items()}


def _index(pool: Path, scores: dict | None = None):
    """task_id -> {'pass': [path], 'fail': [path]}"""
    by_task = defaultdict(lambda: {"pass": [], "fail": []})
    unscored = 0
    for p in sorted(pool.glob("*.json")):
        trace = json.loads(p.read_text())
        md = trace.get("metadata") or {}
        tid = md.get("task_source_id")
        if not tid:
            continue
        if scores is not None and (trace.get("trace_id") or p.stem) not in scores:
            unscored += 1
        key = "pass" if _score_of(trace, p, scores) >= 1.0 else "fail"
        by_task[tid][key].append(p)
    if scores is not None and unscored:
        # silence here would quietly file every unscored trace as passing
        raise SystemExit(
            f"{unscored} pool traces have no entry in the outcomes sidecar; "
            "refusing to treat them as passing")
    return by_task


def plan(pool: Path, n_generation: int, seed: int = 0,
         outcomes: Path | None = None) -> Split:
    scores = load_outcomes(outcomes)
    by_task = _index(pool, scores)
    tasks = sorted(by_task)
    rng = random.Random(seed)
    rng.shuffle(tasks)

    # Generation needs BOTH axes: different candidates fail differently on one
    # task, and one candidate fails differently across tasks. Taking every
    # candidate on a handful of tasks buys only the first, and a vocabulary
    # induced from 5 tasks overfits to them. Sample GEN_PER_TASK candidates per
    # task across enough tasks to reach N.
    gen_tasks_needed = max(1, -(-n_generation // GEN_PER_TASK))
    # Refinement wants N/2 traces AND 2 traces per task, so it needs N/4 tasks.
    # It also wants at least twice the generation task count for diversity.
    # Whichever is larger governs; satisfying only one starves the other.
    ref_tasks_needed = max(gen_tasks_needed * REFINE_TASK_MULTIPLE,
                           -(-(n_generation // 2) // REFINE_PER_TASK))
    need = gen_tasks_needed + ref_tasks_needed + GATE_MIN_TASKS
    if len(tasks) < need:
        raise SystemExit(
            f"pool has {len(tasks)} tasks; the pipeline needs at least {need} "
            f"({gen_tasks_needed} generation + {ref_tasks_needed} refinement + "
            f"{GATE_MIN_TASKS} gate) so no task is shared between corpora. "
            f"Capture more tasks, or lower --n-generation.")

    gen_t = tasks[:gen_tasks_needed]
    ref_t = tasks[gen_tasks_needed:gen_tasks_needed + ref_tasks_needed]
    gate_t = tasks[gen_tasks_needed + ref_tasks_needed:
                   gen_tasks_needed + ref_tasks_needed + GATE_MIN_TASKS]

    s = Split()
    # generation: GEN_PER_TASK per task, failures first so the corpus carries
    # the failure density the vocabulary is induced from
    for t in gen_t:
        b = by_task[t]
        picks = list(b["fail"])[:GEN_PER_TASK]
        picks += list(b["pass"])[:max(0, GEN_PER_TASK - len(picks))]
        s.generation.extend(picks)
    s.generation = s.generation[:n_generation]

    # refinement: one failing + one passing per task, failures first
    for t in ref_t:
        b = by_task[t]
        chosen = []
        if b["fail"]:
            chosen.append(rng.choice(b["fail"]))
        if b["pass"]:
            chosen.append(rng.choice(b["pass"]))
        pool_t = b["fail"] + b["pass"]
        while len(chosen) < REFINE_PER_TASK and len(chosen) < len(pool_t):
            extra = rng.choice(pool_t)
            if extra not in chosen:
                chosen.append(extra)
        s.refinement.extend(chosen[:REFINE_PER_TASK])
    s.refinement = s.refinement[:max(1, n_generation // 2)]

    # gate: spread evenly across its tasks until GATE_TRACES
    i = 0
    while len(s.gate) < GATE_TRACES and gate_t:
        added = False
        for t in gate_t:
            b = by_task[t]["fail"] + by_task[t]["pass"]
            if i < len(b) and len(s.gate) < GATE_TRACES:
                s.gate.append(b[i])
                added = True
        if not added:
            break
        i += 1

    def failing(paths):
        return sum(1 for p in paths
                   if _score_of(json.loads(p.read_text()), p, scores) < 1.0)

    s.manifest = {
        "seed": seed, "n_generation_requested": n_generation,
        "outcomes_source": str(outcomes) if outcomes else "trace metadata",
        "pool_tasks": len(tasks), "pool_traces": sum(
            len(v["pass"]) + len(v["fail"]) for v in by_task.values()),
        "generation": {"tasks": len(gen_t), "traces": len(s.generation),
                       "failing": failing(s.generation)},
        "refinement": {"tasks": len(ref_t), "traces": len(s.refinement),
                       "failing": failing(s.refinement)},
        "gate": {"tasks": len(gate_t), "traces": len(s.gate),
                 "failing": failing(s.gate)},
        "task_ids": {"generation": gen_t, "refinement": ref_t, "gate": gate_t},
    }
    return s


def materialise(s: Split, out: Path) -> dict[str, Path]:
    dirs = {}
    for name in ("generation", "refinement", "gate"):
        d = out / f"corpus_{name}"
        d.mkdir(parents=True, exist_ok=True)
        for p in getattr(s, name):
            dst = d / p.name
            # gold-free copy, never a verbatim one. Self-healing: a corpus
            # materialised before this rule existed is rewritten on resume.
            if not dst.exists() or goldfree.offending_keys(
                    json.loads(dst.read_text())):
                goldfree.strip_file(p, dst)
        dirs[name] = d
    (out / "split_manifest.json").write_text(json.dumps(s.manifest, indent=2))
    # disjointness is the property the whole pipeline rests on: assert it
    ids = {n: set(s.manifest["task_ids"][n]) for n in ("generation", "refinement", "gate")}
    for a in ids:
        for b in ids:
            if a < b and ids[a] & ids[b]:
                raise SystemExit(f"corpora {a} and {b} share tasks: {ids[a] & ids[b]}")
    return dirs


def requirements(n_generation: int, traces_per_task: int = 12) -> dict:
    """Tasks and traces the pipeline needs for a given N, so a capture can be
    sized before it is paid for."""
    gen_tasks = max(1, -(-n_generation // GEN_PER_TASK))
    ref_tasks = max(gen_tasks * REFINE_TASK_MULTIPLE,
                    -(-(n_generation // 2) // REFINE_PER_TASK))
    return {
        "n_generation": n_generation,
        "tasks": {"generation": gen_tasks, "refinement": ref_tasks,
                  "gate": GATE_MIN_TASKS,
                  "total": gen_tasks + ref_tasks + GATE_MIN_TASKS},
        "traces_judged": {"refinement_per_cycle": n_generation // 2,
                          "worst_case_3_cycles": 3 * (n_generation // 2)},
        "traces_captured_min": (gen_tasks + ref_tasks + GATE_MIN_TASKS) * traces_per_task,
    }
