#!/usr/bin/env python3
"""Run a HoVer candidate set whose candidates differ by solver model, on a split portion.

    /Users/andreicojocaru/Desktop/GEPA_Experiments/.venv/bin/python data/hover/scripts/capture_models.py --set models-1 --portion judging
    ... --portion judging --limit-tasks 20 --out data/hover/traces/_incoming/models-1-smoke     (smoke)

Every candidate in the set carries its own `solver_model` in the registry (all routed through
OpenRouter); the instructions are the same for all. Tasks come from data/hover/splits/<set>/split.json.
Output has the shape data/hover/scripts/capture_pool.py produces (candidate_map.json, raw/, corpus/,
outcomes.json), so migrate_incoming.py can archive it. Resumable per (candidate, task, repeat).
Candidates run one after another, each under its own model; --workers threads within a candidate.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data" / "hover"
HOVER_SRC = Path("/Users/andreicojocaru/Desktop/GEPA_Experiments/src")
HOVER_DATA = Path("/Users/andreicojocaru/Desktop/GEPA_Experiments/data/hover")
CONVERTER = REPO / "legacy" / "trials" / "2026-08-07-adamast-taxonomy-generation"
T0 = time.time()
# Per-model LM settings. OpenAI's reasoning models reject a temperature other than 1.0 and need a
# large completion budget; dspy's own check does not recognise the 5.x naming behind the OpenRouter
# prefix, so the settings are pinned here. Every other model runs on provider defaults.
MODEL_KWARGS = {"openai/gpt-5.4-nano": {"temperature": 1.0, "max_tokens": 16000}}

# Reasoning is switched OFF for every model, so that the set compares the models themselves rather
# than how much test-time compute each vendor bundles by default. Measured on the first smoke:
# deepseek emitted 957 and qwen 3,245 reasoning tokens per call while gemini, haiku and nano emitted
# none, which is both a cost/latency difference and a difference in condition. OpenRouter's own
# switch is `reasoning: {enabled: false}`; litellm passes an `extra_body` dict through untouched
# (verified offline against its openrouter transformation), and providers that cannot reason ignore
# it. --reasoning keeps a model's default instead.
NO_REASONING = {"reasoning": {"enabled": False}}
# Not every endpoint allows it: z-ai/glm-5.3-flash answers 400 "Reasoning is mandatory for this
# endpoint and cannot be disabled." So each model is probed once with a one-token prompt, and the
# first setting it accepts is used for the whole model, from strongest to weakest:
#   off -> minimal effort -> the provider's default.
# Whatever a model settled on is recorded per candidate in candidate_map.json and outcomes.json,
# so a taxonomy or ranking built on these traces can say which models were reasoning.
REASONING_LADDER = [("off", {"reasoning": {"enabled": False}}),
                    ("minimal", {"reasoning": {"effort": "minimal"}}),
                    ("default", None)]


def probe_reasoning(dspy, model: str, base_kw: dict, log) -> tuple[str, dict | None]:
    """One tiny call per rung until the endpoint accepts it. Returns (label, extra_body).

    Only a refusal of the reasoning setting itself moves down the ladder. A rate limit or a
    provider outage says nothing about whether the setting is allowed, so it is waited out and
    retried on the same rung; qwen's provider rate-limited the probe, which the earlier version
    read as three refusals in a row and then raised, ending a run with five models still to go.
    """
    for label, body in REASONING_LADDER:
        kw = dict(base_kw)
        kw["max_tokens"] = max(16, min(kw.get("max_tokens", 8192), 16000)) if body is None else kw.get("max_tokens", 8192)
        if body is not None: kw["extra_body"] = dict(body)
        for attempt in range(6):
            try:
                lm = dspy.LM(model, cache=False, num_retries=0, **kw)
                lm("Reply with the single word: ok")
                return label, body
            except Exception as e:
                msg = str(e)[:200].replace("\n", " ")
                transient = any(k in msg for k in ("RateLimit", "429", "Timeout", "503", "502", "overloaded", "Provider returned error", "InternalServerError"))
                if transient and attempt < 5:
                    wait = 10 * (attempt + 1)
                    log(f"    probe: {model} unavailable ({msg[:90]}); waiting {wait}s and retrying the same setting")
                    time.sleep(wait); continue
                if label == "default": raise
                log(f"    reasoning={label} refused ({msg[:120]}); trying the next setting")
                break
    return "default", None


def log(msg, head=False):
    el = time.time() - T0
    print((f"\n{'=' * 78}\n[{el:7.1f}s] {msg}\n{'=' * 78}" if head else f"[{el:7.1f}s] {msg}"), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--set", required=True); p.add_argument("--portion", required=True); p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--out", type=Path, default=None, help="default: data/hover/traces/_incoming/<set>-<portion>")
    p.add_argument("--workers", type=int, default=8); p.add_argument("--limit-tasks", type=int, default=None); p.add_argument("--limit-candidates", type=int, default=None)
    p.add_argument("--only-models", default=None, help="comma-separated aliases or model ids to run (default all)")
    p.add_argument("--max-tokens", type=int, default=8192); p.add_argument("--dry-run", action="store_true")
    p.add_argument("--model-attempts", type=int, default=5, help="relaunches per model when a trace fails to parse (default 5)")
    p.add_argument("--reasoning", action="store_true", help="leave each model's default reasoning behaviour on (default: off for every model)")
    a = p.parse_args()
    out = a.out or (DATA / "traces" / "_incoming" / f"{a.set}-{a.portion}")
    spec = json.loads((DATA / "splits" / a.set / "split.json").read_text())
    if a.portion not in spec["portions"]: raise SystemExit(f"{a.portion!r} not in {sorted(spec['portions'])}")
    ids = spec["portions"][a.portion][: a.limit_tasks] if a.limit_tasks else spec["portions"][a.portion]
    others = set().union(*(set(v) for k, v in spec["portions"].items() if k != a.portion)); assert not (set(ids) & others)
    setj = json.loads((DATA / "candidates" / "sets" / f"{a.set}.json").read_text())
    reg = {json.loads(l)["candidate_id"]: json.loads(l) for l in open(DATA / "candidates" / "registry.jsonl")}
    cands = [reg[c] for c in setj["candidate_ids"]]
    if a.only_models:
        keep = set(a.only_models.split(",")); cands = [c for c in cands if c["alias"] in keep or c["solver_model"] in keep]
    if a.limit_candidates: cands = cands[: a.limit_candidates]
    for c in cands: assert c.get("solver_model") and c.get("route") == "openrouter", c["alias"]
    log(f"HoVer {a.set} capture — portion={a.portion}, {len(ids)} tasks, {len(cands)} candidates (models), repeats={a.repeats}", head=True)
    for c in cands: log(f"  {c['alias']} {c['candidate_id']}  {c['solver_model']}")
    n_roll = len(cands) * len(ids) * a.repeats; log(f"  -> {n_roll:,} rollouts")

    sys.path.insert(0, str(HOVER_SRC))
    import dspy
    from hover_gepa_baseline.program import HoverMultiHop
    from hover_gepa_baseline.retrieval import configure_retriever
    from hover_gepa_baseline.evaluation import evaluate_frontier_candidates
    raw = out / "raw"; (raw / "candidate_states").mkdir(parents=True, exist_ok=True)
    records = []
    for i, c in enumerate(cands):
        prog = HoverMultiHop()
        for name, pred in prog.named_predictors(): pred.signature = pred.signature.with_instructions(c["components"][name])
        rel = f"candidate_states/cand_{i:03d}.json"; prog.save(str(raw / rel))
        records.append({"candidate_index": i, "state_file": rel, "component_sha256": c["component_sha256"], "pool_candidate_id": c["alias"],
                        "accepted": True, "solver_model": c["solver_model"], "candidate_id": c["candidate_id"]})
    manifest = {"schema_version": 1, "frontier_candidate_indices": list(range(len(records))), "candidates": records, "candidate_set": a.set,
                "lm_settings": {"reasoning": "each model's default" if a.reasoning else "disabled where the endpoint allows it, else minimal effort, else default; probed per model and recorded in each candidate's 'reasoning' field",
                                "max_tokens": a.max_tokens, "per_model_overrides": MODEL_KWARGS, "route": "openrouter"}}
    (out / "candidate_map.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if a.dry_run: log("  dry run complete — state files and candidate_map written; no model calls."); return
    if not os.environ.get("OPENROUTER_API_KEY"): raise SystemExit("OPENROUTER_API_KEY is not set in this shell; export it and relaunch.")

    log("configuring the BM25 retriever ..."); configure_retriever(HOVER_DATA)
    log("rebuilding examples from the frozen IDs ...")
    from datasets import load_dataset
    ds = load_dataset("hover-nlp/hover", split="train", trust_remote_code=True)
    want, by_id = set(ids), {}
    for i, row in enumerate(ds):
        facts = row.get("supporting_facts") or []; titles = [f[0] if isinstance(f, (list, tuple)) else f.get("key") for f in facts]
        if len({t for t in titles if t}) != 3: continue
        sid = row.get("uid") or row.get("id") or f"train-{i}"
        if sid in want: by_id[sid] = dspy.Example(claim=row["claim"], supporting_facts=row["supporting_facts"], label=row.get("label"), source_index=i, source_id=sid).with_inputs("claim")
    if want - set(by_id): raise SystemExit(f"{len(want - set(by_id))} frozen IDs absent from HoVer")
    examples = [by_id[i] for i in ids]; log(f"  rebuilt {len(examples)} examples")

    for rec in records:
        model = f"openrouter/{rec['solver_model']}"
        log(f"{rec['pool_candidate_id']}  {model}", head=True)
        kw = {"max_tokens": a.max_tokens, **MODEL_KWARGS.get(rec["solver_model"], {})}
        if a.reasoning:
            rec["reasoning"] = "default"
        else:
            label, body = probe_reasoning(dspy, model, kw, log)
            rec["reasoning"] = label
            if body is not None: kw["extra_body"] = dict(body)
        task_lm = dspy.LM(model, cache=False, num_retries=8, **kw)
        log(f"  settings: reasoning={rec['reasoning']}  " + json.dumps(kw))
        (out / "candidate_map.json").write_text(json.dumps(manifest, indent=2) + "\n")
        dspy.configure(lm=task_lm)
        one = {"schema_version": 1, "frontier_candidate_indices": [rec["candidate_index"]], "candidates": records}
        t = time.time()
        # The evaluator records a failed trace and then re-raises, so a single malformed generation
        # aborts the whole capture: qwen returned 30 tokens of unterminated JSON on 1 task in 200 and
        # took nine finished models' worth of run with it. Generation is not deterministic and the
        # failed trace has no gold file, so a relaunch retries exactly that trace. Retry the model a
        # few times, then leave whatever will not parse and move to the next model.
        tdir = raw / "evaluation" / "traces" / f"candidate_{rec['candidate_index']:03d}"
        want = len(examples) * a.repeats
        launch_t = time.time()
        stale = sum(1 for f in tdir.glob("*.json") if json.loads(f.read_text()).get("status") != "ok")
        if stale: log(f"    {stale} trace(s) failed on an earlier launch; retrying them first")
        for attempt in range(1, a.model_attempts + 1):
            # A task the model cannot produce parseable output for is deterministic, not flaky:
            # qwen emitted an unterminated JSON string on one hover claim every single time, and
            # because the evaluator re-raises, each attempt died about twelve traces later without
            # ever reaching the rest. So a task with a recorded failure for this model is dropped
            # from the next attempt; its error trace stays on disk and the migration records it as
            # a capture failure, exactly like a provider-blocked task.
            # Only tasks that failed again during THIS launch are excluded. A task carried over
            # from an earlier launch gets one fresh try first, so re-running the script is the way
            # to retry everything that failed, and a task is dropped only after it fails here too.
            poisoned = set()
            for f in tdir.glob("*.json"):
                if f.stat().st_mtime < launch_t: continue
                t = json.loads(f.read_text())
                if t.get("status") != "ok": poisoned.add(str(t["task"]["source_id"]))
            todo = [e for e in examples if str(e.source_id) not in poisoned] if poisoned else examples
            if poisoned:
                log(f"    excluding {len(poisoned)} task(s) that failed to parse in this launch: {sorted(poisoned)[:3]}")
            try:
                evaluate_frontier_candidates(run_dir=raw, candidate_manifest=one, evaluation_set=todo, task_lm=task_lm, repeats=a.repeats, num_threads=a.workers)
                break
            except Exception as e:
                if any(k in str(e) for k in ("RateLimit", "429", "Provider returned error", "503", "overloaded")):
                    wait = 30 * attempt
                    log(f"  [!] {rec['pool_candidate_id']}: provider unavailable; waiting {wait}s before attempt {attempt + 1}/{a.model_attempts}")
                    time.sleep(wait)
                ok = sum(1 for f in tdir.glob("*.json") if json.loads(f.read_text()).get("status") == "ok")
                if attempt == a.model_attempts:
                    log(f"  [!] {rec['pool_candidate_id']}: still failing after {attempt} attempts ({ok}/{want} traces ok); moving on. Last: {type(e).__name__}: {str(e)[:160]}")
                    rec["incomplete"] = f"{ok}/{want}"
                    rec["unparseable_tasks"] = sorted(poisoned)
                else:
                    log(f"  [!] {rec['pool_candidate_id']}: {type(e).__name__} at {ok}/{want} traces; retrying the rest (attempt {attempt + 1}/{a.model_attempts})")
        ok = sum(1 for f in tdir.glob("*.json") if json.loads(f.read_text()).get("status") == "ok")
        failed = sorted({str(json.loads(f.read_text())["task"]["source_id"]) for f in tdir.glob("*.json") if json.loads(f.read_text()).get("status") != "ok"})
        if failed: rec["unparseable_tasks"] = failed
        log(f"  {rec['pool_candidate_id']}: {ok}/{want} traces ok ({time.time() - t:.0f}s this launch)" + (f"; {len(failed)} task(s) unparseable" if failed else ""))
        (out / "candidate_map.json").write_text(json.dumps(manifest, indent=2) + "\n")

    log("collecting gold outcomes", head=True)
    idx = {r["candidate_index"]: r["pool_candidate_id"] for r in records}; outcomes = {}; n = 0
    for f in sorted((raw / "evaluation" / "gold_do_not_pass_to_judge").rglob("*.json")):
        g = json.loads(f.read_text()); cid = idx[int(g["candidate_index"])]
        outcomes.setdefault(cid, {}).setdefault(str(g["evaluation_repeat"]), {})[str(g["task"]["source_id"])] = float(g["gold_score"]); n += 1
    (out / "outcomes.json").write_text(json.dumps({"benchmark": "hover", "pool": a.set, "split_id": spec["split_id"], "task_model": "per candidate (openrouter/<solver_model> from the registry)",
        "solver_models": {r["pool_candidate_id"]: r["solver_model"] for r in records}, "lm_settings": manifest["lm_settings"], "reasoning_by_candidate": {r["pool_candidate_id"]: r.get("reasoning") for r in records}, "split": a.portion, "repeats": a.repeats, "candidates": len(records), "tasks": len(ids), "records": n, "outcomes": outcomes}, indent=2, sort_keys=True) + "\n")
    inc = {r["pool_candidate_id"]: r["incomplete"] for r in records if r.get("incomplete")}
    if inc: log(f"  INCOMPLETE: {inc} — rerun the same command to retry those traces")
    means = {c: sum(v.values()) / len(v) for c, r in outcomes.items() for v in [r.get("0", {})] if v}
    for c, m in sorted(means.items(), key=lambda kv: -kv[1]): log(f"  {c}: mean gold {m:.4f} over {len(outcomes[c]['0'])} tasks")

    log("converting traces to judge-view corpus", head=True)
    sys.path.insert(0, str(CONVERTER)); from convert_traces import convert
    corpus = out / "corpus"; corpus.mkdir(parents=True, exist_ok=True); k = 0
    for f in sorted((raw / "evaluation" / "traces").rglob("*.json")):
        t = json.loads(f.read_text())
        if t.get("status") != "ok": continue
        c = convert(t); c["metadata"].update({"split": a.portion, "pool": a.set}); (corpus / f"{c['trace_id']}.json").write_text(json.dumps(c, indent=1)); k += 1
    log(f"  wrote {k:,} traces -> {corpus}"); log("complete")


if __name__ == "__main__":
    main()
