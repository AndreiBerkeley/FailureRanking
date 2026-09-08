#!/usr/bin/env python3
"""Capture the 12 candidates of ifbench or hotpotqa on a portion of
data/<benchmark>/splits/pools-1/fills.json, with full stage records.

    <trial venv python> data/scripts/capture_artifact_pool.py --benchmark ifbench --portion judging
    ... --task-model openrouter/google/gemini-3.1-flash-lite     # OpenRouter route
    ... --dry-run                                                # load everything, no model calls

Adapted from legacy/trials/2026-08-25-gepa-cross-benchmark-candidates/run_measurement.py:
tasks come from an id list instead of the trial manifests, examples are built
from the task sources directly (the artifact loader exposes only 600 IFBench
train rows and the fills reach beyond them), the task model is a flag, and each
record carries the outcome-blind judge view the earlier converter produced, so
no separate conversion step is needed. Shards, resumability and the usage ledger
are the original's. Run with that trial's virtual environment:
    legacy/trials/2026-08-25-gepa-cross-benchmark-candidates/.venv/bin/python
"""
from __future__ import annotations
import argparse, hashlib, json, logging, os, re, signal, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
TRIAL = REPO / "legacy" / "trials" / "2026-08-25-gepa-cross-benchmark-candidates"
sys.path.insert(0, str(TRIAL))
from run_official_gepa import REFLECTION_MODEL, HOTPOTQA_SNAPSHOT_SHA256, example_id, history_usage, load_official_benchmark, write_json, write_usage_ledger  # noqa: E402
from run_measurement import load_candidates, component_resolver, serialize_trace, as_mapping  # noqa: E402
from convert_traces_for_adamast import build_messages, trace_id as corpus_trace_id  # noqa: E402

DEFAULT_TASK_MODEL = "gemini/gemini-3.1-flash-lite"
IFB = TRIAL / "vendor" / "gepa-artifact" / "gepa_artifact" / "benchmarks" / "IFBench" / "data"


def align(batch, examples) -> dict[int, tuple[dict, float]]:
    """Map example index -> (trajectory, score).

    dspy's bootstrap_trace_data DROPS an example whose result it cannot unpack
    (a provider error that survived the LM's own retries, typically) instead of
    scoring it, so a batch can come back one short. Each trajectory carries the
    'example_ind' it was computed for, which restores the alignment; the caller
    re-runs whatever is absent."""
    trajs = batch.trajectories or []
    if len(trajs) != len(batch.scores): raise RuntimeError(f"{len(trajs)} trajectories for {len(batch.scores)} scores")
    out: dict[int, tuple[dict, float]] = {}
    for j, t in enumerate(trajs):
        i = t.get("example_ind") if isinstance(t, dict) else None
        if i is None:
            if len(trajs) != len(examples): raise RuntimeError("trajectories carry no example_ind and the batch is short; cannot align results to tasks")
            i = j
        out[int(i)] = (t or {}, float(batch.scores[j]))
    return out


BLOCK_MARKERS = ("PROHIBITED_CONTENT", "blocked the request", "ContentPolicyViolation", "content_filter")


class ErrorLog(logging.Handler):
    """Keeps the error lines dspy's parallelizer logs when a program raises on an example.
    dspy drops such an example from its results; the logged line is the only record of why."""
    def __init__(self): super().__init__(logging.ERROR); self.messages: list[str] = []
    def emit(self, record): self.messages.append(record.getMessage())


def error_for(example, messages: list[str]) -> str | None:
    """The provider error logged for this example, matched on its first input field."""
    first = str(list(example.inputs().toDict().values())[0])[:50]
    keys = {first, repr(first)[1:-1]}
    for m in reversed(messages):
        if any(k and k in m for k in keys):
            j = m.rfind("): [")
            return m[j + 3:].strip()[:400] if j >= 0 else m[-400:]
    return None


def failed_record(tid: str, reason: str) -> dict[str, Any]:
    """A task for which the provider returned no completion at all. Scored 0.0, the value
    gepa's failure_score gives a format failure, which is how the direct Gemini route records
    the same event (a blocked prompt arrives there as a parse failure with text None)."""
    return {"task_id": tid, "score": 0.0, "trace": [], "prediction": {}, "parse_failed": False, "capture_failed": reason}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--benchmark", choices=("ifbench", "hotpotqa"), required=True)
    p.add_argument("--portion", required=True, help="a portion of the fills file, e.g. taxonomy or judging")
    p.add_argument("--fills-file", type=Path, default=None, help="default: data/<benchmark>/splits/pools-1/fills.json")
    p.add_argument("--run-dir", type=Path, default=None, help="default: data/<benchmark>/traces/_incoming/pools-1-<portion>")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--task-model", default=DEFAULT_TASK_MODEL,
                   help="gemini/<model> uses GEMINI_API_KEY; openrouter/google/<model> uses OPENROUTER_API_KEY")
    p.add_argument("--limit-tasks", type=int, default=None, help="smoke: first N tasks only")
    p.add_argument("--dry-run", action="store_true", help="load benchmark, candidates and tasks; no model calls")
    return p.parse_args()


def build_examples(bench: str, wanted: list[str]):
    import dspy
    rows = {}
    if bench == "ifbench":
        for fname in ("IFBench_test.jsonl", "IFBench_train.jsonl"):
            for line in open(IFB / fname):
                if line.strip():
                    d = json.loads(line); rows[example_id(d, bench)] = d
        make = lambda d: dspy.Example(**d).with_inputs("prompt")
    else:
        snap = TRIAL / "inputs" / "hotpotqa_official_snapshot.json"
        assert hashlib.sha256(snap.read_bytes()).hexdigest() == HOTPOTQA_SNAPSHOT_SHA256, "snapshot hash mismatch"
        payload = json.loads(snap.read_text())
        for part in ("train", "validation", "evaluation"):
            for d in payload[part]: rows[example_id(d, bench)] = d
        make = lambda d: dspy.Example(**d).with_inputs("question")
    missing = [t for t in wanted if t not in rows]
    if missing: raise SystemExit(f"{len(missing)} task ids not found in the {bench} sources, e.g. {missing[:2]}")
    return [make(rows[t]) for t in wanted]


def main() -> None:
    a = parse_args(); b = a.benchmark
    fills = a.fills_file or REPO / "data" / b / "splits" / "pools-1" / "fills.json"
    run_dir = a.run_dir or REPO / "data" / b / "traces" / "_incoming" / f"pools-1-{a.portion}"
    spec = json.loads(fills.read_text())
    if a.portion not in spec["portions"]: raise SystemExit(f"{a.portion!r} not in {fills}; have {sorted(spec['portions'])}")
    wanted = list(spec["portions"][a.portion])
    if a.limit_tasks: wanted = wanted[: a.limit_tasks]
    others = set().union(*(set(v) for k, v in spec["portions"].items() if k != a.portion))
    assert not (set(wanted) & others), "portion overlaps another"
    run_dir.mkdir(parents=True, exist_ok=True); shard_dir = run_dir / "records"; shard_dir.mkdir(exist_ok=True)

    bench_obj, program, metric, feedback_map = load_official_benchmark(b)
    candidates = load_candidates(b, None)
    # identity check against the registry: the 12 candidates must be exactly the registry's
    reg = {json.loads(l)["candidate_id"]: json.loads(l) for l in open(REPO / "data" / b / "candidates" / "registry.jsonl")}
    cids = ["cnd-" + hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()[:12] for c in candidates]
    assert set(cids) == set(reg), "candidates differ from data/<benchmark>/candidates/registry.jsonl"
    examples = build_examples(b, wanted)
    print(f"{b} pools-1/{a.portion}: {len(candidates)} candidates x {len(examples)} tasks x {a.repeats} repeat(s) = {len(candidates)*len(examples)*a.repeats:,} rollouts; model {a.task_model}", flush=True)

    config = {"schema_version": 2, "benchmark": b, "split_id": spec["split_id"], "portion": a.portion,
              "fills_file": str(fills.relative_to(REPO)), "fills_sha256": hashlib.sha256(fills.read_bytes()).hexdigest(),
              "task_count": len(examples), "candidate_count": len(candidates), "candidate_ids": cids, "repeats": a.repeats,
              "repeat_semantics": "independent provider-default samples; not seed-controlled", "capture_traces": True,
              "task_model": a.task_model, "workers": a.workers, "judge_view": "convert_traces_for_adamast.build_messages, outcome-blind",
              "candidates_from": f"runs/{b}_g31lite_g36_seed0_representative_v3"}
    cfg = run_dir / "run_config.json"
    if cfg.exists():
        old = json.loads(cfg.read_text()); old.pop("workers", None); new = dict(config); new.pop("workers", None)
        if old != new: raise RuntimeError("run configuration differs from the one frozen in this run dir; use a fresh --run-dir")
    pending = [(c, r) for c in range(len(candidates)) for r in range(a.repeats) if not (shard_dir / f"cand{c:02d}_repeat{r}.json").exists()]
    print(f"{len(pending)} of {len(candidates)*a.repeats} (candidate, repeat) shards still to run", flush=True)
    if a.dry_run: print("dry run complete: benchmark, candidates and every task id resolved; no model calls; nothing written."); return
    if not cfg.exists(): write_json(cfg, config)   # freeze the configuration only when a real run starts
    if not pending: print("nothing to do"); return
    key = "OPENROUTER_API_KEY" if a.task_model.startswith("openrouter/") else "GEMINI_API_KEY"
    if not os.environ.get(key): raise SystemExit(f"{key} is not set in this shell; export it and relaunch.")

    import dspy
    from gepa.adapters.dspy_adapter.dspy_adapter import DspyAdapter
    task_lm = dspy.LM(a.task_model, max_tokens=4096, cache=False, num_retries=3)
    dspy.configure(lm=task_lm)
    adapter = DspyAdapter(student_module=program, metric_fn=metric, feedback_map=feedback_map, num_threads=a.workers)
    errlog = ErrorLog(); logging.getLogger("dspy.utils.parallelizer").addHandler(errlog)
    blocked_path = run_dir / "blocked_tasks.json"
    blocked: dict[str, Any] = json.loads(blocked_path.read_text()) if blocked_path.exists() else {}
    if blocked: print(f"{len(blocked)} task(s) blocked by the provider on an earlier candidate will not be sent again: {sorted(blocked)}", flush=True)
    launch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + f"-pid{os.getpid()}"
    def on_term(_s, _f): raise KeyboardInterrupt("SIGTERM; preserving usage")
    prev = signal.signal(signal.SIGTERM, on_term)
    try:
        for cidx, rep in pending:
            cand = candidates[cidx]; resolve = component_resolver(cand)
            live = [i for i, tid in enumerate(wanted) if tid not in blocked]   # positions sent to the model
            errlog.messages.clear()
            batch = adapter.evaluate([examples[i] for i in live], cand, capture_traces=True)
            by_ind = {live[j]: v for j, v in align(batch, [examples[i] for i in live]).items()}
            failed: dict[int, str] = {i: f"blocked on candidate {blocked[wanted[i]]['first_candidate']}: {blocked[wanted[i]]['reason']}" for i in range(len(wanted)) if wanted[i] in blocked}
            missing = [i for i in range(len(examples)) if i not in by_ind and i not in failed]
            # A dropped example is one dspy could not unpack: the program raised on it after the LM's own
            # retries. A provider content block is final and is not asked again, for this or any later
            # candidate; anything else is re-run alone once and then recorded as a capture failure.
            for i in list(missing):
                err = error_for(examples[i], errlog.messages) or ""
                if any(mk in err for mk in BLOCK_MARKERS):
                    failed[i] = err; missing.remove(i)
                    blocked[wanted[i]] = {"reason": err, "first_candidate": cidx, "at": datetime.now(timezone.utc).isoformat()}
                    write_json(blocked_path, blocked)
                    print(f"  cand {cidx:02d} repeat {rep}: task {wanted[i]} blocked by the provider; recorded as a capture failure and blocklisted for this run", flush=True)
            if missing:
                print(f"  cand {cidx:02d} repeat {rep}: {len(missing)} task(s) came back without a result; re-running them singly once", flush=True)
                for i in list(missing):
                    errlog.messages.clear()
                    got = align(adapter.evaluate([examples[i]], cand, capture_traces=True), [examples[i]])
                    if 0 in got: by_ind[i] = got[0]; missing.remove(i); continue
                    err = error_for(examples[i], errlog.messages) or "no result from the provider on the batch and on one single re-run; see the run log"
                    failed[i] = err; missing.remove(i)
                    print(f"  cand {cidx:02d} repeat {rep}: task {wanted[i]} still without a result; recorded as a capture failure: {err[:160]}", flush=True)
            assert not missing
            records = []
            for i, tid in enumerate(wanted):
                if i in failed:
                    rec: dict[str, Any] = failed_record(tid, failed[i])
                else:
                    traj, score = by_ind[i]
                    rec = {"task_id": tid, "score": float(score),
                           "trace": serialize_trace(traj.get("trace"), resolve), "prediction": as_mapping(traj.get("prediction") or {})}
                    rec["parse_failed"] = any(s["outputs"].get("_parse_failed") for s in rec["trace"])
                rec["trace_id"] = corpus_trace_id(b, cidx, tid, rep)
                rec["judge_view"] = {"messages": build_messages(b, rec, cand)}
                records.append(rec)
            write_json(shard_dir / f"cand{cidx:02d}_repeat{rep}.json",
                       {"schema_version": 2, "benchmark": b, "portion": a.portion, "split_id": spec["split_id"], "candidate_idx": cidx,
                        "candidate_id": cids[cidx], "repeat": rep, "task_model": a.task_model, "task_count": len(records),
                        "mean_score": sum(r["score"] for r in records) / len(records),
                        "strict_rate": sum(1 for r in records if r["score"] == 1.0) / len(records),
                        "parse_failed_count": sum(1 for r in records if r["parse_failed"]),
                        "capture_failed_count": sum(1 for r in records if r.get("capture_failed")),
                        "dropped_task_policy": "a task dspy dropped is re-run alone once unless the provider blocked its content; a task still without a result is recorded with score 0.0, an empty trace and capture_failed=<reason>; a blocked task is not sent again for later candidates in this run (blocked_tasks.json)",
                        "records": records})
            done = sum(1 for _ in shard_dir.glob("*.json"))
            print(f"  cand {cidx:02d} repeat {rep}: mean {sum(r['score'] for r in records)/len(records):.4f}  [{done}/{len(candidates)*a.repeats}]", flush=True)
    finally:
        signal.signal(signal.SIGTERM, prev)
        write_usage_ledger(run_dir, launch_id, history_usage(task_lm),
                           {"model": REFLECTION_MODEL, "calls": 0, "input_tokens": 0, "output_tokens": 0, "provider_reported_cost_usd": 0.0})
    print("complete")


if __name__ == "__main__":
    main()
