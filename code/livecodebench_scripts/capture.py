"""Capture and score one candidate set on one pool of livecodebench.

    capture.py capture --portion taxonomy --out <dir> [--workers 12] [--limit N] [--dry-run]
    capture.py score   --out <dir>

capture: one OpenRouter call per (candidate, task), reasoning off (probed per model:
off -> minimal -> default, like hover's runner), temperature 0, resumable. Writes
<out>/traces/<candidate_id>/<task_id>.json in the judge's shape: trace_id, messages
(system, user, assistant), metadata. Usage and cost are logged per call.

score: runs each trace's first ```python fence against the hidden tests through the
upstream runner and writes <out>/outcomes.jsonl -- a SEPARATE file, never inside the
trace, so traces stay gold-free. Must run under evaluator/.venv/bin/python.

Never launched by the assistant; Andrei runs it.
"""
import argparse, hashlib, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
sys.path.insert(0, str(Path(__file__).parent))
from lcb import SYSTEM, user_prompt, iter_problems, extract_code, score as run_tests

ROOT = Path(__file__).resolve().parents[1]
MODEL_KWARGS = {"openai/gpt-5.4-nano": {"temperature": 1.0}}
LADDER = [("off", {"reasoning": {"enabled": False}}),
          ("minimal", {"reasoning": {"effort": "minimal"}}),
          ("default", None)]
_lock = Lock()
def log(s):
    with _lock: print(time.strftime("[%H:%M:%S] ") + s, flush=True)


def call_openrouter(model, messages, max_tokens, temperature, extra, timeout=300, retries=5):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key: raise RuntimeError("OPENROUTER_API_KEY not set")
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if extra: body.update(extra)
    data = json.dumps(body).encode(); delay = 5.0
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                         "HTTP-Referer": "https://github.com/failurerank", "X-OpenRouter-Title": "FailureRank"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode())
            if resp.get("error"):
                e = resp["error"]; msg = str(e.get("message", ""))
                if "reasoning" in msg.lower() and ("not supported" in msg.lower() or "invalid" in msg.lower()):
                    return None, {"refused_reasoning": msg}
                if e.get("code") in (429, 502, 503, 524) or "rate" in msg.lower():
                    time.sleep(delay); delay = min(delay * 2, 60); continue
                return None, {"error": msg[:300]}
            ch = resp["choices"][0]; u = resp.get("usage", {}) or {}
            return {"content": ch["message"].get("content") or "", "finish_reason": ch.get("finish_reason"),
                    "usage": {"prompt": u.get("prompt_tokens"), "completion": u.get("completion_tokens"),
                              "reasoning": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                              "cost": u.get("cost"), "upstream_cost": (u.get("cost_details") or {}).get("upstream_inference_cost"),
                              "is_byok": u.get("is_byok")}, "model": resp.get("model")}, None
        except Exception as ex:                                          # noqa: BLE001
            if attempt == retries: return None, {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
            time.sleep(delay); delay = min(delay * 2, 60)
    return None, {"error": "exhausted retries"}


def probe(model, kw):
    """Walk the ladder with one tiny call; return (label, extra_body)."""
    for label, extra in LADDER:
        got, err = call_openrouter(model, [{"role": "user", "content": "Reply with the single word: ok"}],
                                   16, kw.get("temperature", 0.0), extra, timeout=60, retries=3)
        if got is not None: return label, extra
        if err and "refused_reasoning" in err: continue
        log(f"    probe {model} {label}: {err}"); 
    return "default", None


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--split", default="pools-1"); c.add_argument("--portion", required=True)
    c.add_argument("--set", default="models-1"); c.add_argument("--out", type=Path, required=True)
    c.add_argument("--workers", type=int, default=12); c.add_argument("--max-tokens", type=int, default=16000)
    c.add_argument("--limit", type=int, default=None, help="first N tasks of the portion")
    c.add_argument("--only-model", default=None); c.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("score"); s.add_argument("--out", type=Path, required=True)
    s.add_argument("--workers", type=int, default=4); s.add_argument("--timeout", type=int, default=6)
    a = ap.parse_args()

    if a.cmd == "capture":
        split = json.load(open(ROOT / "splits" / a.split / "split.json"))
        task_ids = split["portions"][a.portion][: a.limit] if a.limit else split["portions"][a.portion]
        cs = json.load(open(ROOT / "candidates" / "sets" / f"{a.set}.json"))
        cands = [(cs["candidate_ids"].index(cid), cid, cs["solver_models"][cid]) for cid in cs["active_candidate_ids"]]
        if a.only_model: cands = [x for x in cands if x[2] == a.only_model]
        want = set(task_ids); probs = {}
        for d in iter_problems():
            if d["question_id"] in want and d["question_id"] not in probs:
                probs[d["question_id"]] = {"prompt": user_prompt(d), "difficulty": d["difficulty"],
                                           "platform": d["platform"], "variant": "starter_code" if d.get("starter_code") else "stdin"}
        missing = want - set(probs)
        if missing: sys.exit(f"{len(missing)} portion tasks not found in raw files: {sorted(missing)[:5]}")
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "manifest.json").write_text(json.dumps({
            "benchmark": "livecodebench", "split": a.split, "portion": a.portion, "candidate_set": a.set,
            "candidate_index": {cid: i for i, cid, _ in cands}, "tasks": len(task_ids),
            "prompt": "program/prompt.md", "prompt_sha256": cs["prompt_sha256"],
            "settings": {"temperature": 0.0, "reasoning": "off where the endpoint allows, else minimal, else default; probed per model",
                         "max_tokens": a.max_tokens, "route": "openrouter", "per_model_overrides": MODEL_KWARGS}}, indent=2))
        jobs = []
        for i, cid, model in cands:
            for t in task_ids:
                p = a.out / "traces" / cid / f"{t}.json"
                if p.exists():
                    try:
                        if json.loads(p.read_text()).get("status") == "ok": continue
                    except Exception: pass
                jobs.append((i, cid, model, t))
        # round-robin over candidates: grouped by model, the pool spends most of the run
        # on the one slowest provider; interleaved, all providers run at once and the
        # wall-clock is the slowest model's own time (generalization: 134 min grouped)
        jobs.sort(key=lambda j: (task_ids.index(j[3]), j[0]))
        log(f"capture: {len(cands)} candidates x {len(task_ids)} tasks = {len(cands)*len(task_ids)}; to do {len(jobs)}")
        if a.dry_run:
            i, cid, model, t = jobs[0]
            print("\n--- example prompt (system) ---\n" + SYSTEM + "\n--- (user) ---\n" + probs[t]["prompt"][:1500])
            print("\ndry run: nothing spent"); return
        settings = {}
        for i, cid, model in cands:
            kw = {**MODEL_KWARGS.get(model, {})}
            label, extra = probe(model, kw); settings[model] = (label, extra, kw)
            log(f"  {model}: reasoning={label}")
        spent = {"openrouter": 0.0, "upstream": 0.0}; done = 0; t0 = time.time()
        def work(job):
            i, cid, model, t = job
            label, extra, kw = settings[model]
            msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": probs[t]["prompt"]}]
            got, err = call_openrouter(model, msgs, a.max_tokens, kw.get("temperature", 0.0), extra)
            tid = hashlib.sha256(f"{cid}|{t}|0".encode()).hexdigest()[:24]
            rec = {"trace_id": tid, "task_id": t, "candidate_id": cid, "candidate_index": i, "repeat": 0,
                   "solver_model": model, "reasoning": label, "status": "ok" if got else "capture_failed",
                   "messages": msgs + ([{"role": "assistant", "content": got["content"]}] if got else []),
                   "metadata": {"difficulty": probs[t]["difficulty"], "platform": probs[t]["platform"],
                                "prompt_variant": probs[t]["variant"], "finish_reason": got and got["finish_reason"],
                                "usage": got and got["usage"], "served_model": got and got["model"], "error": err}}
            p = a.out / "traces" / cid / f"{t}.json"; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(rec, indent=1))
            return rec
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = [ex.submit(work, j) for j in jobs]
            for f in as_completed(futs):
                r = f.result(); done += 1
                u = (r["metadata"].get("usage") or {})
                # OpenRouter reports upstream_inference_cost == cost on ordinary calls; only
                # BYOK calls (cost 0) are billed upstream. Count each call once.
                if u.get("is_byok"): spent["upstream"] += u.get("upstream_cost") or 0
                else: spent["openrouter"] += u.get("cost") or 0
                if r["status"] != "ok": log(f"  [!] {r['solver_model']} {r['task_id']}: {r['metadata']['error']}")
                if done % 50 == 0 or done == len(jobs):
                    log(f"  {done}/{len(jobs)}  ({time.time()-t0:.0f}s)  spent ${spent['openrouter']:.2f} openrouter + ${spent['upstream']:.2f} upstream-billed")
        log(f"done: {done} traces -> {a.out}/traces")

    else:  # score
        outp = a.out / "outcomes.jsonl"
        have = set()
        if outp.exists():
            for line in open(outp): have.add(json.loads(line)["trace_id"])
        recs = [json.loads(p.read_text()) for p in sorted((a.out / "traces").glob("*/*.json"))]
        todo = [r for r in recs if r["trace_id"] not in have and r["status"] == "ok"]
        probs = {}
        want = {r["task_id"] for r in todo}
        for d in iter_problems():
            if d["question_id"] in want and d["question_id"] not in probs: probs[d["question_id"]] = d
        log(f"score: {len(recs)} traces, {len(todo)} to score")
        def one(r):
            code = extract_code(r["messages"][-1]["content"])
            try:
                res = run_tests(probs[r["task_id"]], code, timeout=a.timeout)
            except Exception as e:  # one bad program must not end the run; recorded, auditable
                log(f"  runner exception on {r['trace_id']} ({r['task_id']}): {type(e).__name__}: {e}")
                res = {"all_pass": False, "total": 0, "passed": 0, "error": f"runner exception: {type(e).__name__}: {e}"}
            return {"trace_id": r["trace_id"], "task_id": r["task_id"], "candidate_id": r["candidate_id"],
                    "repeat": 0, "score": 1.0 if res["all_pass"] else 0.0, "tests_run": res["total"],
                    "tests_passed": res["passed"], "error": res["error"], "fence_found": "```" in r["messages"][-1]["content"]}
        n = 0
        with open(outp, "a") as fh, ThreadPoolExecutor(max_workers=a.workers) as ex:
            for o in ex.map(one, todo):
                fh.write(json.dumps(o) + "\n"); fh.flush(); n += 1
                if n % 50 == 0: log(f"  scored {n}/{len(todo)}")
        rows = [json.loads(l) for l in open(outp)]
        by = {}
        for o in rows: by.setdefault(o["candidate_id"], []).append(o["score"])
        cs = json.load(open(ROOT / "candidates" / "sets" / "models-1.json"))
        log(f"pass rate per model ({len(rows)} outcomes):")
        for cid, v in sorted(by.items(), key=lambda x: -sum(x[1])/len(x[1])):
            log(f"  {cs['solver_models'].get(cid, cid):<34} {sum(v)/len(v):.3f}  (n={len(v)})")
        nf = sum(1 for o in rows if not o["fence_found"])
        log(f"replies with no code fence: {nf}")
        rx = [o for o in rows if (o["error"] or "").startswith(("runner exception", "child killed"))]
        if rx: log(f"traces the runner could not finish (scored 0, audit these): {len(rx)}  e.g. {[o['trace_id'] for o in rx[:3]]}")

if __name__ == "__main__":
    main()
