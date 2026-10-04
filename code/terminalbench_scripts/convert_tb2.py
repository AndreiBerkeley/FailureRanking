#!/usr/bin/env python3
"""Terminal-Bench 2.0 leaderboard submissions -> FailureRank judge-view traces, outcomes and registries.

    python3 data/terminalbench/scripts/convert_tb2.py --submissions <dir with Terminus2__*/> --tasks <dir with <task>/task.toml> --out <capture dir> [--limit N]

Source: the public dataset harborframework/terminal-bench-2-leaderboard (Apache 2.0). Each trial
directory holds result.json (task, trial, exception, verifier reward), agent/trajectory.json
(ATIF: one user step with the Terminus 2 instructions + task, then agent steps with the model's
analysis/plan text, its command batch, and the terminal output it got back) and verifier/
(reward.txt, ctrf.json). Nothing is run; the traces are exactly what the leaderboard recorded.

The judge view is the shape the pipeline reads ({trace_id, messages, metadata}), rendered by
new_pipeline.generation.render: an ENVIRONMENT block with the task description and the Terminus
instructions once; then per agent step a turn (system = one-paragraph reminder of the step's
contract, user = the terminal output the step received, assistant = the step's analysis, plan and
command batch, with the model's reasoning_content when the trace carries it); the terminal output
after the last batch as a closing ENVIRONMENT block; and, when the harness stopped the run
(timeout), that fact as an ENVIRONMENT line -- it is the run's own record, not the verifier's.
Gold (verifier reward, test results) never enters a trace: it goes to outcomes.jsonl beside them.
"""
from __future__ import annotations
import argparse, hashlib, json, tomllib, re
from pathlib import Path
from collections import Counter, defaultdict

STEP_INSTR = ("Terminus 2 step. You are given the terminal output produced by your previous command batch (or the initial "
              "terminal state). Answer with a JSON object holding `analysis` (what the output shows, what is done, what remains), "
              "`plan` (the next commands and why), `commands` (a batch of {keystrokes, duration} to send to the terminal), and "
              "`task_complete: true` only when the task is finished. The full instructions and the task description are in the "
              "ENVIRONMENT block at the top of this trace; every step is judged against them.\nComponent: terminus")
# the "Component:" line is the pipeline's own convention (contracts.agent_name): it names the
# agent of every step, so a 30-step loop is one agent and not thirty positional ones


def task_registry(tasks_dir: Path) -> dict:
    reg = {}
    for d in sorted(p for p in tasks_dir.iterdir() if p.is_dir() and (p / "task.toml").exists()):
        m = tomllib.load(open(d / "task.toml", "rb"))
        md = m.get("metadata", {})
        reg[d.name] = {"task_id": d.name, "instruction": (d / "instruction.md").read_text() if (d / "instruction.md").exists() else "",
                       "category": md.get("category"), "difficulty": md.get("difficulty"), "tags": md.get("tags", []),
                       "expert_time_estimate_min": md.get("expert_time_estimate_min"), "agent_timeout_sec": (m.get("agent") or {}).get("timeout_sec"),
                       "verifier_timeout_sec": (m.get("verifier") or {}).get("timeout_sec")}
    return reg


def split_first_user(msg: str):
    """The single user step: Terminus instructions, 'Task Description:', then 'Current terminal state:'."""
    i = msg.find("Task Description:"); j = msg.find("Current terminal state:")
    instr = msg[:i].strip() if i >= 0 else msg
    task = msg[i + len("Task Description:"):j].strip() if i >= 0 and j >= 0 else ""
    screen = msg[j + len("Current terminal state:"):].strip() if j >= 0 else ""
    return instr, task, screen


def render_output(step: dict) -> str:
    parts = []
    if step.get("reasoning_content"):
        parts.append("[[ ## reasoning (model's hidden reasoning, as recorded) ## ]]\n" + str(step["reasoning_content"]).strip())
    if step.get("message"):
        parts.append("[[ ## analysis and plan ## ]]\n" + str(step["message"]).strip())
    cmds = []
    for tc in step.get("tool_calls") or []:
        a = tc.get("arguments") or {}
        if tc.get("function_name") == "bash_command":
            cmds.append({"keystrokes": a.get("keystrokes"), "duration": a.get("duration")})
        else:
            cmds.append({tc.get("function_name"): a})
    parts.append("[[ ## commands ## ]]\n" + json.dumps(cmds, ensure_ascii=False, indent=1))
    ex = step.get("extra") or {}
    if ex.get("task_complete") or any(tc.get("function_name") == "mark_task_complete" for tc in step.get("tool_calls") or []) \
            or (step.get("message") and re.search(r'"task_complete"\s*:\s*true', str(step.get("message")))):
        parts.append("[[ ## task_complete ## ]]\ntrue")
    return "\n\n".join(parts)


def observation_text(step: dict) -> str:
    obs = step.get("observation") or {}
    res = obs.get("results") or []
    txt = "\n".join(str(r.get("content", "")) for r in res if isinstance(r, dict))
    return txt.strip() or "(no terminal output recorded)"


def convert_trial(trial_dir: Path, model_id: str, reg: dict):
    res = json.loads((trial_dir / "result.json").read_text())
    tj = trial_dir / "agent" / "trajectory.json"
    if not tj.exists(): return None, None
    traj = json.loads(tj.read_text())
    steps = traj.get("steps") or []
    task = res["task_name"]; trial = res["trial_name"]
    trace_id = hashlib.sha256(f"tb2|{model_id}|{trial}".encode()).hexdigest()[:24]
    user0 = next((s for s in steps if s.get("source") == "user"), None)
    instr, task_desc, screen = split_first_user(user0["message"]) if user0 else ("", reg.get(task, {}).get("instruction", ""), "")
    messages = [{"role": "user", "content": f"Task: Terminal-Bench 2.0 · {task}. An agent (Terminus 2) solves a task in a Linux container by "
                                            f"sending batches of shell commands and reading the terminal; hidden tests then check the container's final state.\n\n"
                                            f"Task Description:\n{task_desc or reg.get(task, {}).get('instruction', '')}\n\nTerminus 2 instructions (verbatim, shown once):\n{instr}"}]
    prev_obs = f"Current terminal state:\n{screen}" if screen else "(initial terminal state not recorded)"
    agent_steps = [s for s in steps if s.get("source") == "agent"]
    for s in agent_steps:
        messages.append({"role": "system", "content": STEP_INSTR})
        messages.append({"role": "user", "content": prev_obs})
        messages.append({"role": "assistant", "content": render_output(s)})
        prev_obs = observation_text(s)
    # what the terminal showed after the last batch, and how the run ended
    tail = [f"Terminal output after the last command batch:\n{prev_obs}"]
    exc = res.get("exception_info") or {}
    if exc.get("exception_type"):
        tail.append(f"The harness stopped the run: {exc['exception_type']} — {str(exc.get('exception_message',''))[:200]}")
    else:
        tail.append("The agent ended the run (task_complete) or exhausted its steps; the verifier then ran its tests on the container.")
    messages.append({"role": "user", "content": "\n\n".join(tail)})
    ar = res.get("agent_result") or {}
    meta = {"benchmark": "terminalbench", "task_id": task, "task_source_id": task, "candidate_id": model_id, "trial_name": trial,
            "trial_id": res.get("id"), "steps": len(agent_steps), "exception": exc.get("exception_type"), "started_at": res.get("started_at"),
            "tokens": {"input": ar.get("n_input_tokens"), "output": ar.get("n_output_tokens"), "cache": ar.get("n_cache_tokens")}, "cost_usd": ar.get("cost_usd"),
            "task_category": reg.get(task, {}).get("category"), "task_difficulty": reg.get(task, {}).get("difficulty"),
            "source": "harborframework/terminal-bench-2-leaderboard", "source_path": str(trial_dir.relative_to(trial_dir.parents[3]))}
    reward = ((res.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    # the leaderboard counts a trial without a verifier reward (verifier timeout, missing reward file) as unresolved: score 0, flagged
    outcome = {"trace_id": trace_id, "candidate_id": model_id, "task_id": task, "trial_name": trial, "score": float(reward) if reward is not None else 0.0,
               "reward_missing": reward is None, "exception": exc.get("exception_type")}
    return {"trace_id": trace_id, "messages": messages, "metadata": meta}, outcome


def repeat_index(trials):
    """Per task, trials ordered by started_at: the earliest is repeat 0, the next repeat 1, ..."""
    by_task = defaultdict(list)
    for t in trials:
        r = json.loads((t / "result.json").read_text()); by_task[r["task_name"]].append((r.get("started_at") or "", t))
    return {t: i for ts in by_task.values() for i, (_, t) in enumerate(sorted(ts))}


def main():
    import gzip, datetime
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submissions", type=Path, required=True); ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None, help="flat smoke output: traces/*.json + outcomes.jsonl")
    ap.add_argument("--layout", type=Path, default=None, help="write the benchmark layout under this data dir (traces/cap-1 bodies, outcomes, tasks, candidates)")
    ap.add_argument("--capture", default="cap-1"); ap.add_argument("--repeats", default="0", help="comma-separated repeat numbers to convert (earliest trial per task = 0); 'all' for every trial")
    ap.add_argument("--limit", type=int, default=None, help="trials per submission (smoke)")
    ap.add_argument("--only-tasks", default=None, help="<split.json>:<portion> -- convert only that portion's tasks (e.g. the judged tasks' reruns for the generator)")
    a = ap.parse_args(); reg = task_registry(a.tasks); keep = None if a.repeats == "all" else {int(x) for x in a.repeats.split(",")}
    only = None
    if a.only_tasks:
        sp, por = a.only_tasks.rsplit(":", 1); only = set(json.loads(Path(sp).read_text())["portions"][por])
    if not a.out and not a.layout: raise SystemExit("give --out (flat) or --layout (benchmark data dir)")
    flat = a.out; lay = a.layout
    if flat: (flat / "traces").mkdir(parents=True, exist_ok=True)
    if lay:
        for d in ("traces/" + a.capture, "outcomes", "tasks", "candidates/sets", "program"): (lay / d).mkdir(parents=True, exist_ok=True)
    outcomes = []; cands = {}; stats = defaultdict(Counter); bodies = {}
    for sub in sorted(p for p in a.submissions.iterdir() if p.is_dir()):
        meta = sub / "metadata.yaml"
        m = re.search(r'model_name:\s*"?([^"\n]+)"?', meta.read_text()) if meta.exists() else None
        model = m.group(1).strip() if m else sub.name.split("__", 1)[-1]          # the directory name when metadata.yaml is absent
        model_id = "tb2-" + re.sub(r"[^a-z0-9.]+", "-", model.lower()).strip("-")
        cands[model_id] = {"candidate_id": model_id, "model_name": model, "submission": sub.name, "agent": "Terminus 2", "agent_version": "2.0.0",
                           "program": "terminus-2 (harbor)", "source": "harborframework/terminal-bench-2-leaderboard"}
        trials = sorted(t for job in sub.iterdir() if job.is_dir() for t in job.iterdir() if t.is_dir() and (t / "result.json").exists())
        rep = repeat_index(trials)
        if a.limit: trials = trials[:a.limit]
        body_path = lay / "traces" / a.capture / f"{model_id}.jsonl.gz" if lay else None
        fh = gzip.open(body_path, "wt", encoding="utf-8") if lay else None
        for t in trials:
            if keep is not None and rep[t] not in keep: continue
            if only is not None and json.loads((t / "result.json").read_text())["task_name"] not in only: continue
            tr, oc = convert_trial(t, model_id, reg)
            if tr is None: stats[model_id]["no_trajectory"] += 1; continue
            tr["metadata"]["repeat"] = rep[t]; oc["repeat"] = rep[t]; oc["capture"] = a.capture
            if flat: (flat / "traces" / f"{tr['trace_id']}.json").write_text(json.dumps(tr, ensure_ascii=False))
            if fh: fh.write(json.dumps({"trace_id": tr["trace_id"], "task_id": tr["metadata"]["task_id"], "candidate_id": model_id, "repeat": rep[t], "status": "ok",
                                        "judge_view": {"messages": tr["messages"]}, "metadata": tr["metadata"]}, ensure_ascii=False) + "\n")
            outcomes.append(oc); stats[model_id]["traces"] += 1; stats[model_id]["chars"] += sum(len(x["content"]) for x in tr["messages"]); stats[model_id]["steps"] += tr["metadata"]["steps"]
            if oc["exception"]: stats[model_id]["exceptions"] += 1
            if oc["reward_missing"]: stats[model_id]["no_reward"] += 1
        if fh: fh.close(); bodies[model_id] = {"file": body_path.name, "traces": stats[model_id]["traces"]}
    today = datetime.date.today().isoformat(); src = "harborframework/terminal-bench-2-leaderboard (Hugging Face, Apache 2.0)"
    if flat:
        (flat / "outcomes.jsonl").write_text("".join(json.dumps(o) + "\n" for o in outcomes))
        (flat / "manifest.json").write_text(json.dumps({"source": src, "tasks": len(reg), "candidates": list(cands), "stats": {k: dict(v) for k, v in stats.items()}}, indent=2))
    if lay:
        cap = lay / "traces" / a.capture
        (cap / "manifest.json").write_text(json.dumps({"capture": a.capture, "benchmark": "terminalbench", "created": today, "source": src, "agent": "Terminus 2 (harbor terminus-2 2.0.0)",
            "candidate_ids": sorted(cands), "bodies": bodies, "repeats": sorted(keep) if keep else "all", "only_tasks": a.only_tasks, "repeat_rule": "per task and model, trials ordered by started_at; the earliest is repeat 0",
            "converter": "data/terminalbench/scripts/convert_tb2.py", "stats": {k: dict(v) for k, v in stats.items()},
            "note": "traces are the leaderboard's recorded trajectories, converted; nothing was run. Gold (verifier reward) is in outcomes/<capture>.jsonl only."}, indent=1))
        (lay / "outcomes" / f"{a.capture}.jsonl").write_text("".join(json.dumps(o) + "\n" for o in outcomes))
        (lay / "outcomes" / f"{a.capture}.provenance.json").write_text(json.dumps({"capture": a.capture, "source": src, "score": "verifier_result.rewards.reward from each trial's result.json (0/1); a trial with no reward (verifier timeout, missing reward file) scores 0 and carries reward_missing: true, as the leaderboard counts it", "created": today}, indent=2))
        (lay / "tasks" / "tasks.jsonl").write_text("".join(json.dumps(r) + "\n" for r in reg.values()))
        (lay / "tasks" / "provenance.json").write_text(json.dumps({"source": "harborframework/terminal-bench-2.0 (task definitions: instruction.md, task.toml)", "tasks": len(reg), "created": today,
            "fields": "task_id, instruction (verbatim), category, difficulty, tags, time estimates, timeouts -- the benchmark's own labels"}, indent=2))
        (lay / "candidates" / "registry.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cands.values()))
        (lay / "candidates" / "sets" / "terminus2-1.json").write_text(json.dumps({"set": "terminus2-1", "benchmark": "terminalbench", "rule": "every model run under the Terminal-Bench reference agent Terminus 2 on the 2.0 leaderboard with five trials per task",
            "candidate_ids": sorted(cands), "active_candidate_ids": sorted(cands), "solver_models": {c: cands[c]["model_name"] for c in sorted(cands)}, "created": today}, indent=2))
    for k, v in stats.items():
        n = v["traces"] or 1
        print(f"{k}: traces {v['traces']}, mean steps {v['steps']/n:.1f}, mean chars {v['chars']/n:,.0f}, exceptions {v['exceptions']}, no reward {v['no_reward']}, no trajectory {v['no_trajectory']}")


if __name__ == "__main__":
    main()
