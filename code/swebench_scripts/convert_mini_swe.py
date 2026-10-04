#!/usr/bin/env python3
"""SWE-bench Verified, mini-SWE-agent (bash-only track) runs -> FailureRank judge-view traces, outcomes and registries.

    python3 data/swebench/scripts/convert_mini_swe.py --raw <dir holding bash-only/<run>/trajs> \
        --per-instance <dir holding <run>/per_instance_details.json> --reports <dir holding <run>/<instance>.json> \
        --runs <run>,<run>,... --layout data/swebench [--capture cap-1]

Source: the SWE-bench leaderboard's public submissions (github.com/SWE-bench/experiments,
evaluation/verified/<run>/, and s3://swe-bench-submissions/bash-only/<run>/{trajs,logs}). Every run is
mini-SWE-agent 2.0.0 with one bash tool, the same system and task prompt, one attempt per task. Nothing
is run; the traces are what the leaderboard recorded.

Trajectories come in two message formats: chat messages (role system/user/assistant/tool/exit, with
`tool_calls`, `reasoning_content`) for most models, and OpenAI Responses-API items (`object: response`
with reasoning / message / function_call outputs, then `function_call_output` items) for the GPT runs.
Both render to the same judge view: an ENVIRONMENT block with the system prompt and the task prompt
(issue plus instructions) once; per model step a turn (system = the step's contract, user = the command
output(s) and any harness message it received, assistant = its reasoning, text and bash calls); and a
closing ENVIRONMENT block with the last commands' output, the exit status and the submitted patch.
Gold (resolved, test results) never enters a trace: it goes to outcomes/<capture>.jsonl only.

Outcomes: `resolved` from the run's per_instance_details.json; where that file is missing or broken
(all-false against a published rate of 69.6% for Gemini 3 Pro; absent for GPT-5.2 Codex) it is rebuilt
from the harness's own per-instance report.json files (checked to reproduce Claude 4.6 Opus's published
file exactly, 378/378). A task without a report counts unresolved, as the leaderboard counts it.

Two exclusions, both recorded in the manifest: runs the provider cut short (exit status a provider error such as
ServiceUnavailableError or Timeout) get neither a trace nor an outcome; and the GPT-5.2 Codex submission
(20260219_mini-v2.0.0_gpt-5-2-codex) is not converted at all -- its 500 uploaded trajectories are byte-identical to
GPT-5.2 (high)'s and record gpt-5.2 as the model, while its evaluated patches differ, so its traces are not its own.
"""
from __future__ import annotations
import argparse, datetime, gzip, hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path

STEP_INSTR = ("mini-SWE-agent step. You are given the output of the bash command(s) you ran in your previous step (or, on the "
              "first step, only the task prompt). Answer with your reasoning and one or more bash tool calls. When the fix is done, "
              "write the patch to patch.txt, check it, and submit it with the exact command the task prompt gives. The system prompt "
              "and the task prompt are in the ENVIRONMENT block at the top of this trace; every step is judged against them.\n"
              "Component: agent")
# the "Component:" line is the pipeline's convention (contracts.agent_name): every step is the same agent


INFRA_EXITS = {"ServiceUnavailableError", "Timeout", "APIError", "APIConnectionError", "InternalServerError", "RateLimitError"}
# exit statuses that name a provider failure rather than the agent stopping (Submitted) or hitting its own limits
# (LimitsExceeded); such runs are dropped like tau2-bench's infrastructure errors


def _s(x) -> str:
    if x is None: return ""
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)


def cid_of(run: str) -> str:
    return "swe-" + run.split("_", 2)[2]                    # 20260217_mini-v2.0.0_claude-4-6-opus -> swe-claude-4-6-opus


def steps_of(msgs: list) -> tuple[str, str, list, list, dict | None]:
    """-> (system, task prompt, steps, pending observations after the last step, exit message).
    Each step = {"inputs": [...], "reasoning": str, "text": str, "calls": [str], "raw_calls": [...]}"""
    system = task = ""; steps = []; pending = []; exit_msg = None; seen_task = False
    for m in msgs:
        role, typ = m.get("role"), m.get("type")
        if role == "system" and not steps and not system:
            system = _s(m.get("content")); continue
        if role == "user" and not seen_task:
            task = _s(m.get("content")); seen_task = True; continue
        if role == "exit":
            exit_msg = m; continue
        if role == "tool" or typ == "function_call_output":
            pending.append(_s(m.get("content") if role == "tool" else m.get("output"))); continue
        if role == "user":                                   # harness messages after the task (format errors, limits)
            pending.append("[harness message]\n" + _s(m.get("content"))); continue
        if role == "assistant":
            calls = []
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function") or {}
                args = fn.get("arguments")
                try: args = json.loads(args) if isinstance(args, str) else args
                except Exception: pass
                calls.append(args.get("command") if isinstance(args, dict) and "command" in args and fn.get("name") == "bash" else {fn.get("name"): args})
            reas = _s(m.get("reasoning_content"))
            if not reas and m.get("thinking_blocks"):
                reas = "\n".join(_s(b.get("thinking")) for b in m["thinking_blocks"] if isinstance(b, dict))
            steps.append({"inputs": pending, "reasoning": reas, "text": _s(m.get("content")).strip(), "calls": calls})
            pending = []; continue
        if m.get("object") == "response":                    # OpenAI Responses API
            reas, text, calls = [], [], []
            for it in m.get("output") or []:
                t = it.get("type")
                if t == "reasoning":
                    reas += [_s(s.get("text")) for s in it.get("summary") or [] if isinstance(s, dict)]
                    reas += [_s(c.get("text")) for c in it.get("content") or [] if isinstance(c, dict) and c.get("text")]
                elif t == "message":
                    text += [_s(c.get("text")) for c in it.get("content") or [] if isinstance(c, dict)]
                elif t == "function_call":
                    args = it.get("arguments")
                    try: args = json.loads(args) if isinstance(args, str) else args
                    except Exception: pass
                    calls.append(args.get("command") if isinstance(args, dict) and "command" in args and it.get("name") == "bash" else {it.get("name"): args})
            steps.append({"inputs": pending, "reasoning": "\n".join(r for r in reas if r), "text": "\n".join(text).strip(), "calls": calls})
            pending = []; continue
        pending.append("[unrecognised record]\n" + _s(m)[:2000])
    return system, task, steps, pending, exit_msg


def render_step(st: dict) -> str:
    parts = []
    if st["reasoning"].strip():
        parts.append("[[ ## reasoning (the model's reasoning, as recorded) ## ]]\n" + st["reasoning"].strip())
    if st["text"]:
        parts.append("[[ ## text ## ]]\n" + st["text"])
    parts.append("[[ ## bash calls ## ]]\n" + (json.dumps(st["calls"], ensure_ascii=False, indent=1) if st["calls"] else "(none)"))
    return "\n\n".join(parts)


def convert(traj_path: Path, cid: str, iid: str):
    d = json.loads(traj_path.read_text())
    info = d.get("info") or {}
    system, task, steps, tail_obs, exit_msg = steps_of(d.get("messages") or [])
    messages = [{"role": "user", "content":
                 f"Task: SWE-bench Verified · {iid}. An agent (mini-SWE-agent 2.0.0, a single bash tool) works in the repository at "
                 f"/testbed. It must resolve the issue described in the task prompt by editing the repository's source files and then "
                 f"submit a git patch of its changes. Hidden tests are then run on the repository with that patch applied.\n\n"
                 f"Agent system prompt (verbatim):\n{system}\n\nTask prompt (verbatim, shown once; the issue and the agent's instructions):\n{task}"}]
    first = True
    for st in steps:
        messages.append({"role": "system", "content": STEP_INSTR})
        inp = "\n\n".join(st["inputs"]) if st["inputs"] else ("(first step: the task prompt above; no command output yet)" if first
                                                              else "(no command output: the previous step made no call)")
        messages.append({"role": "user", "content": inp})
        messages.append({"role": "assistant", "content": render_step(st)})
        first = False
    status = info.get("exit_status") or "unknown"
    submission = _s(info.get("submission")) or (_s(exit_msg.get("content")) if exit_msg else "")
    tail = []
    if tail_obs:
        tail.append("Output of the last step's commands:\n" + "\n\n".join(tail_obs))
    tail.append(f"The run ended with exit status: {status}.")
    tail.append("The submitted patch (the run's output; hidden tests are run on the repository with it applied):\n" + submission
                if submission.strip() else "No patch was submitted.")
    messages.append({"role": "user", "content": "\n\n".join(tail)})
    ms = info.get("model_stats") or {}
    ms = ms if isinstance(ms, dict) else {}
    meta = {"benchmark": "swebench", "task_id": iid, "task_source_id": iid, "candidate_id": cid, "steps": len(steps), "exit_status": status,
            "patch_chars": len(submission), "api_calls": ms.get("api_calls"), "cost_usd": ms.get("instance_cost"),
            "trajectory_format": d.get("trajectory_format"), "source": "SWE-bench/experiments bash-only (mini-SWE-agent 2.0.0)",
            "source_path": "/".join(traj_path.parts[-4:])}
    trace_id = hashlib.sha256(f"swebench|{cid}|{iid}".encode()).hexdigest()[:24]
    return {"trace_id": trace_id, "messages": messages, "metadata": meta}


def resolved_of(d: dict, iid: str) -> float:
    if isinstance(d, dict) and iid in d and isinstance(d[iid], dict):
        d = d[iid]
    return 1.0 if d.get("resolved") is True else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, required=True); ap.add_argument("--per-instance", type=Path, required=True)
    ap.add_argument("--reports", type=Path, required=True); ap.add_argument("--runs", required=True)
    ap.add_argument("--layout", type=Path, required=True); ap.add_argument("--capture", default="cap-1")
    a = ap.parse_args()
    lay = a.layout; cap = lay / "traces" / a.capture
    for d in (cap, lay / "outcomes", lay / "candidates" / "sets"): d.mkdir(parents=True, exist_ok=True)
    ids = [json.loads(l)["instance_id"] if "instance_id" in json.loads(l) else json.loads(l)["task_id"] for l in open(lay / "tasks" / "tasks.jsonl")]
    runs = a.runs.split(","); today = datetime.date.today().isoformat()
    outcomes, cands, bodies, stats, oc_source = [], {}, {}, defaultdict(Counter), {}
    for run in runs:
        cid = cid_of(run)
        meta_yaml = (a.per_instance / run / "metadata.yaml").read_text() if (a.per_instance / run / "metadata.yaml").exists() else ""
        name = (re.search(r"^\s*name:\s*(.+)$", meta_yaml, re.M) or [None, run])[1].strip()
        pub = (re.search(r"^\s*resolved:\s*([\d.]+)", meta_yaml, re.M) or [None, None])[1]
        pi = a.per_instance / run / "per_instance_details.json"
        res = None
        try:
            j = json.loads(pi.read_text())
            if isinstance(j, dict) and j and sum(1 for v in j.values() if v.get("resolved")) > 0:
                res = {k: 1.0 if v.get("resolved") else 0.0 for k, v in j.items()}; oc_source[cid] = "per_instance_details.json"
        except Exception:
            pass
        if res is None:
            res = {}
            for i in ids:
                p = a.reports / run / f"{i}.json"
                res[i] = resolved_of(json.loads(p.read_text()), i) if p.exists() else 0.0
            oc_source[cid] = "rebuilt from logs/<instance>/report.json (per_instance_details.json missing or all-false)"
        cands[cid] = {"candidate_id": cid, "model_name": name, "run": run, "agent": "mini-SWE-agent", "agent_version": "2.0.0",
                      "published_resolved_pct": float(pub) if pub else None, "source": "github.com/SWE-bench/experiments evaluation/verified/" + run}
        body = cap / f"{cid}.jsonl.gz"
        with gzip.open(body, "wt", encoding="utf-8") as fh:
            for iid in ids:
                tp = a.raw / "bash-only" / run / "trajs" / iid / f"{iid}.traj.json"
                if not tp.exists():
                    stats[cid]["no_trajectory"] += 1; continue
                tr = convert(tp, cid, iid)
                if tr["metadata"]["exit_status"] in INFRA_EXITS:
                    # the provider cut the run (outage, timeout): not the agent's doing, so neither a trace nor an outcome
                    stats[cid]["infrastructure_exit_skipped"] += 1; continue
                fh.write(json.dumps({"trace_id": tr["trace_id"], "task_id": iid, "candidate_id": cid, "repeat": 0, "status": "ok",
                                     "judge_view": {"messages": tr["messages"]}, "metadata": tr["metadata"]}, ensure_ascii=False) + "\n")
                outcomes.append({"trace_id": tr["trace_id"], "candidate_id": cid, "task_id": iid, "score": res.get(iid, 0.0), "repeat": 0, "capture": a.capture})
                s = stats[cid]; s["traces"] += 1; s["steps"] += tr["metadata"]["steps"]; s["chars"] += sum(len(m["content"]) for m in tr["messages"])
                s["exit_" + tr["metadata"]["exit_status"]] += 1
        bodies[cid] = {"file": body.name, "traces": stats[cid]["traces"]}
        n = stats[cid]["traces"] or 1
        print(f"{cid}: {stats[cid]['traces']} traces, resolved {sum(res.get(i, 0) for i in ids)/len(ids):.3f} (published {pub}), "
              f"mean steps {stats[cid]['steps']/n:.0f}, mean chars {stats[cid]['chars']/n:,.0f}, no trajectory {stats[cid]['no_trajectory']}, "
              f"exits {dict((k[5:], v) for k, v in stats[cid].items() if k.startswith('exit_'))}")
    src = "SWE-bench/experiments (evaluation/verified, bash-only track) + s3://swe-bench-submissions/bash-only"
    (cap / "manifest.json").write_text(json.dumps({"capture": a.capture, "benchmark": "swebench", "created": today, "source": src,
        "agent": "mini-SWE-agent 2.0.0 (bash only), one attempt per task", "candidate_ids": sorted(cands), "bodies": bodies, "repeats": [0],
        "converter": "data/swebench/scripts/convert_mini_swe.py", "stats": {k: dict(v) for k, v in stats.items()},
        "excluded": {"20260219_mini-v2.0.0_gpt-5-2-codex": "uploaded trajectories are byte-identical to 20260217_mini-v2.0.0_gpt-5-2-high's (500/500 files) and record gpt-5.2 as the model; its evaluated patches differ",
                     "provider-cut runs": "exit status in " + str(sorted(INFRA_EXITS)) + ": no trace, no outcome"},
        "note": "traces are the leaderboard's recorded trajectories, converted; nothing was run. Gold is in outcomes/<capture>.jsonl only."}, indent=1))
    (lay / "outcomes" / f"{a.capture}.jsonl").write_text("".join(json.dumps(o) + "\n" for o in outcomes))
    (lay / "outcomes" / f"{a.capture}.provenance.json").write_text(json.dumps({"capture": a.capture, "source": src, "created": today,
        "score": "1.0 if the SWE-bench harness marked the instance resolved (FAIL_TO_PASS and PASS_TO_PASS tests pass with the submitted patch), else 0.0; a task with no trajectory has no outcome line",
        "outcome_source_per_candidate": oc_source}, indent=2))
    (lay / "candidates" / "registry.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cands.values()))
    (lay / "candidates" / "sets" / "mini-v2-1.json").write_text(json.dumps({"set": "mini-v2-1", "benchmark": "swebench",
        "rule": "every SWE-bench Verified bash-only submission run with mini-SWE-agent 2.0.0 (the Feb 2026 batch): same agent version, system and task prompt, one attempt; GPT-5.2 Codex excluded (its uploaded trajectories are GPT-5.2 high's)",
        "candidate_ids": sorted(cands), "active_candidate_ids": sorted(cands), "solver_models": {c: cands[c]["model_name"] for c in sorted(cands)}, "created": today}, indent=2))


if __name__ == "__main__":
    main()
