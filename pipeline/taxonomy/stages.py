#!/usr/bin/env python3
"""The four pipeline stages, each resumable and each logging what it does.

generate  -> draft taxonomy from the generation corpus
judge     -> two-pass reflection judge over the refinement corpus
refine    -> 4-reviewer panel, consolidation, cross-code operations
gate      -> 4-annotator interannotation, kappa and coverage

Every stage writes its raw model output BEFORE validating it. A validation
failure must be diagnosable from disk and re-runnable for free, never a reason
to re-spend. Every LLM call retries transient failures with backoff.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path("/Users/andreicojocaru/Desktop/FailureRank")
VENV = Path("/Users/andreicojocaru/Desktop/AdaMAST-private/.venv/bin/python")
TRANSIENT = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "rate limit",
             "overloaded", "timeout", "timed out", "temporarily", "deadline",
             "connection reset", "broken pipe", "502", "504")

# The machine's own network going away is not an LLM error and not a reason to
# give up on a trace: a ten-minute DNS outage once failed 265 of 600 traces
# because these were classified permanent. They get their own budget: retry
# every NETWORK_RETRY_EVERY seconds for up to NETWORK_RETRY_FOR seconds.
NETWORK_ERRORS = ("nodename nor servname", "name or service not known",
                  "temporary failure in name resolution", "remote end closed",
                  "network is unreachable", "connection refused",
                  "no route to host", "[errno 8]", "[errno -2]", "[errno 61]")
NETWORK_RETRY_EVERY = 30.0
NETWORK_RETRY_FOR = 1800.0


def is_network_error(exc) -> bool:
    import http.client
    import socket
    import urllib.error
    reason = getattr(exc, "reason", None)
    # Every http.client.HTTPException is a protocol-level failure of the HTTP
    # conversation itself -- IncompleteRead (a truncated body), BadStatusLine,
    # RemoteDisconnected -- not a refusal by the model. Three IncompleteReads
    # in one second once failed two whole batches as "non-transient".
    if isinstance(exc, (http.client.HTTPException, ConnectionError)):
        return True
    if isinstance(reason, (socket.gaierror, ConnectionError, OSError)) \
            and not isinstance(reason, (socket.timeout, TimeoutError)):
        return True
    m = str(exc).lower()
    return any(k in m for k in NETWORK_ERRORS)


class Transient(Exception):
    """Retryable. Raised explicitly, so retry never depends on the wording of a
    message -- matching TRANSIENT substrings is a fallback for exceptions we do
    not raise ourselves."""


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def openrouter_call(temperature=0.0, retries=5, max_output=16384, timeout=300,
                    thinking=None):
    """Same contract as gemini_call, over OpenRouter's chat completions.

    Model ids are OpenRouter's own ("anthropic/claude-sonnet-4.5",
    "google/gemini-2.5-pro"). The key is OPENROUTER_API_KEY in the
    environment; nothing here ever logs it. JSON output is requested with
    response_format; thinking maps to OpenRouter's unified `reasoning.effort`.
    A finish_reason other than "stop" is logged as a probable cut, and usage
    (prompt, reasoning, answer tokens, cost) is logged on every call.
    """
    import urllib.request
    import urllib.error

    def _call(prompt, model):
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            log("  [!] OPENROUTER_API_KEY not set")
            return None
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_output,
            "response_format": {"type": "json_object"},
        }
        if thinking:
            body["reasoning"] = {"effort": str(thinking).lower()}
        data = json.dumps(body).encode()
        delay = 5.0
        net_wait = {"t": 0.0}
        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/chat/completions", data=data,
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {key}",
                             "HTTP-Referer": "https://github.com/failurerank",
                             "X-OpenRouter-Title": "FailureRank"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    resp = json.loads(r.read().decode())
                if resp.get("error"):
                    e = resp["error"]
                    code = e.get("code")
                    msg = f"openrouter error {code}: {e.get('message')}"
                    if code in (429, 502, 503, 504, 408):
                        raise Transient(msg)
                    log(f"  [!] non-transient LLM error: {msg[:160]}")
                    return None
                ch = (resp.get("choices") or [{}])[0]
                text = ((ch.get("message") or {}).get("content")) or ""
                fr = ch.get("finish_reason")
                u = resp.get("usage") or {}
                det = u.get("completion_tokens_details") or {}
                usage = (f"prompt={u.get('prompt_tokens')} "
                         f"thoughts={det.get('reasoning_tokens')} "
                         f"answer={u.get('completion_tokens')} "
                         f"cost={u.get('cost')} model={resp.get('model')}")
                if not text:
                    raise Transient(f"empty content; finish_reason={fr}")
                if fr and fr != "stop":
                    log(f"  [!] finish_reason={fr} with {len(text):,} chars of "
                        f"text ({usage}); answer is probably cut")
                else:
                    log(f"    usage: {usage}")
                return text
            except urllib.error.HTTPError as exc:
                msg = f"HTTP {exc.code}"
                try:
                    msg += " " + exc.read().decode()[:200]
                except Exception:      # noqa: BLE001
                    pass
                if exc.code in (429, 500, 502, 503, 504, 408) and attempt < retries:
                    log(f"  [!] transient error (attempt {attempt}/{retries}), "
                        f"retry in {delay:.0f}s: {msg[:110]}")
                    time.sleep(delay); delay *= 2
                    continue
                log(f"  [!] non-transient LLM error: {msg[:160]}")
                return None
            except Exception as exc:                       # noqa: BLE001
                import socket
                if is_network_error(exc):
                    waited = net_wait.get("t", 0.0)
                    if waited >= NETWORK_RETRY_FOR:
                        log(f"  [!] network still down after {waited/60:.0f} min; giving up")
                        return None
                    if waited == 0.0:
                        log(f"  [!] network error, will keep retrying for up to "
                            f"{NETWORK_RETRY_FOR/60:.0f} min: {str(exc)[:100]}")
                    time.sleep(NETWORK_RETRY_EVERY)
                    net_wait["t"] = waited + NETWORK_RETRY_EVERY
                    attempt -= 1
                    continue
                transient = isinstance(exc, (Transient, socket.timeout, TimeoutError)) \
                    or any(t.lower() in str(exc).lower() for t in TRANSIENT)
                if not transient:
                    log(f"  [!] non-transient LLM error: {str(exc)[:160]}")
                    return None
                if attempt == retries:
                    log(f"  [!] gave up after {retries} transient failures")
                    return None
                log(f"  [!] transient error (attempt {attempt}/{retries}), "
                    f"retry in {delay:.0f}s: {str(exc)[:110]}")
                time.sleep(delay); delay *= 2
        return None

    return _call


def llm_call(model: str, **kw):
    """Pick the transport from the model id: "openrouter/<vendor>/<model>"
    goes to OpenRouter (prefix stripped), anything else to Gemini."""
    if model.startswith("openrouter/"):
        return openrouter_call(**kw), model[len("openrouter/"):]
    return gemini_call(**kw), model


def gemini_call(temperature=0.0, retries=5, max_output=16384, timeout=300,
                thinking=None):
    """Refiner/judge transport with settable temperature and backoff.

    upstream hardcodes temperature 0.0 and does not retry; a single transient
    503 silently degraded whatever step it landed in.
    """
    import urllib.request

    def _call(prompt, model):
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            log("  [!] GEMINI_API_KEY not set")
            return None
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model.split('/', 1)[-1]}:generateContent?key={key}")
        gen = {"temperature": temperature, "maxOutputTokens": max_output,
               "responseMimeType": "application/json"}
        if thinking:
            # generationConfig.thinkingConfig.thinkingLevel, per the v1beta
            # discovery document: MINIMAL | LOW | MEDIUM | HIGH. The default is
            # model-dependent, and the observation pass was measured spending
            # ~3k thinking tokens on a 12k-token prompt it was asked to
            # re-derive step by step.
            gen["thinkingConfig"] = {"thinkingLevel": str(thinking).upper()}
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen,
        }).encode()
        delay = 5.0
        net_wait = {"t": 0.0}
        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                req = urllib.request.Request(
                    url, data=body, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    data = json.loads(r.read().decode())
                cands = data.get("candidates")
                if not cands:
                    # A 200 with no candidates is almost always a blocked
                    # prompt. Previously this raised KeyError('candidates'),
                    # whose entire message is the word "candidates" -- the least
                    # informative string available -- and was then classified a
                    # non-transient LLM error and given up on without a retry.
                    # It is neither an LLM error nor necessarily permanent.
                    fb = data.get("promptFeedback") or {}
                    reason = fb.get("blockReason")
                    if reason:
                        log(f"  [!] prompt BLOCKED ({reason}); not retryable. "
                            f"ratings={fb.get('safetyRatings')}")
                        return None
                    raise Transient(
                        f"200 with no candidates; response keys={sorted(data)}")
                c0 = cands[0]
                parts = ((c0.get("content") or {}).get("parts")) or []
                if not parts:
                    fr = c0.get("finishReason")
                    if fr == "MAX_TOKENS":
                        log(f"  [!] response hit MAX_TOKENS with no text "
                            f"(max_output={max_output}); not retryable")
                        return None
                    raise Transient(f"candidate carried no parts; finishReason={fr}")
                text = "".join(p.get("text", "") for p in parts)
                # A response can be cut with text present: thinking tokens
                # count against maxOutputTokens, so a long prompt can spend
                # the budget before the answer is finished. Say so, every
                # time, so a truncated answer is diagnosable from the log.
                fr = c0.get("finishReason")
                um = data.get("usageMetadata") or {}
                usage = (f"prompt={um.get('promptTokenCount')} "
                         f"thoughts={um.get('thoughtsTokenCount')} "
                         f"answer={um.get('candidatesTokenCount')}")
                if fr and fr != "STOP":
                    log(f"  [!] finishReason={fr} with {len(text):,} chars of "
                        f"text ({usage}); answer is probably cut")
                else:
                    log(f"    usage: {usage}")
                return text
            except Exception as exc:                       # noqa: BLE001
                msg = str(exc)
                import socket
                if is_network_error(exc):
                    waited = net_wait.get("t", 0.0)
                    if waited >= NETWORK_RETRY_FOR:
                        log(f"  [!] network still down after {waited/60:.0f} min; giving up")
                        return None
                    if waited == 0.0:
                        log(f"  [!] network error, will keep retrying for up to "
                            f"{NETWORK_RETRY_FOR/60:.0f} min: {msg[:100]}")
                    time.sleep(NETWORK_RETRY_EVERY)
                    net_wait["t"] = waited + NETWORK_RETRY_EVERY
                    attempt -= 1            # does not consume a transient retry
                    continue
                transient = (
                    isinstance(exc, (Transient, socket.timeout, TimeoutError))
                    or isinstance(getattr(exc, "reason", None),
                                  (socket.timeout, TimeoutError))
                    or any(t.lower() in msg.lower() for t in TRANSIENT))
                if not transient:
                    log(f"  [!] non-transient LLM error: {msg[:160]}")
                    return None
                if attempt == retries:
                    log(f"  [!] gave up after {retries} transient failures")
                    return None
                log(f"  [!] transient error (attempt {attempt}/{retries}), "
                    f"retry in {delay:.0f}s: {msg[:110]}")
                time.sleep(delay)
                delay *= 2
        return None
    return _call


# ----------------------------------------------------------------- generate
def generate(benchmark, corpus: Path, out: Path, model, structure: Path,
             rounds=5, kappa=0.75, coverage=0.70, agreement=False):
    tax = out / "taxonomy.json"
    if tax.exists():
        log(f"generate: already done ({len(json.loads(tax.read_text())['codes'])} codes)")
        return tax
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(REPO / "pipeline"),
               PYTHONUNBUFFERED="1", ADAMAST_STRUCTURE_FILE=str(structure))
    n = len(list(corpus.glob("*.json")))
    log(f"generate: {n} traces -> {out}")
    cmd = [str(VENV), "-m", "adamast", "generate", "--traces", str(corpus),
           "--output", str(out), "--provider", "google", "--model", model,
           "--max-output-tokens", "8192", "--max-rounds", str(rounds),
           "--kappa-target", str(kappa), "--coverage-floor", str(coverage)]
    # PIPELINE.md: generation emits a draft. Certifying here would spend the
    # measurement on a vocabulary the first refinement round is about to change,
    # and would make generation a hidden refine-and-measure cycle on top of the
    # explicit ones. The cycle gate is the only agreement measurement.
    if not agreement:
        cmd.append("--no-agreement")
    # buffering=1 (line-buffered): without it the log file stays empty until the
    # subprocess exits, which blinds any file-based monitor while the run is live
    with (out / "generate.log").open("a", buffering=1) as lf:
        p = subprocess.Popen(cmd, cwd=str(REPO), env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1)
        for line in p.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            lf.write(line)
            lf.flush()
        p.wait()
    if p.returncode != 0 or not tax.exists():
        raise SystemExit(f"generate failed (rc={p.returncode}); see {out}/generate.log")
    log(f"generate: {len(json.loads(tax.read_text())['codes'])} codes")
    return tax


# ------------------------------------------------------------------- gate
def to_gate_schema(flat: dict, draft: dict) -> dict:
    """flat {codes:[...]} -> the {category_a/b/c} shape the gate loads."""
    cats = {"category_a": {}, "category_b": {}, "category_c": {}}
    for c in flat["codes"]:
        key = f"category_{str(c.get('category', 'A')).lower()[:1]}"
        if key not in cats:
            key = "category_a"
        entry = {"code": c["id"], "name": c["name"],
                 "definition": c.get("description") or c.get("definition", ""),
                 "when_to_use": c.get("when_to_use", ""),
                 "when_not_to_use": c.get("when_not_to_use", "")}
        if c.get("applies_to_role"):
            entry["applies_to_role"] = c["applies_to_role"]
        cats[key][c["id"]] = entry
    return {"metadata": {"strategy": "failurerank-pipeline",
                         "source_schema": "flat-refined"},
            "category_definitions": dict(draft.get("category_definitions") or {}),
            "role_definitions": dict(draft.get("role_definitions") or {}),
            **cats}


def pooled_kappa(out: Path, gate_taxonomy: dict):
    """Fleiss kappa over every round's subjects at once, plus per-code detail.

    Valid ONLY because Config.INTERNAL_REFINEMENT is off. While the gate rewrote
    the taxonomy between rounds, each round measured a different instrument and
    only the last one could be reported -- which is why livebenchmath certified
    on 5 reconciled errors while 37 had been observed. With the taxonomy held
    fixed the rounds measure one instrument and their subjects combine.

    Subject ids are namespaced trace_id + error_id exactly as the per-round
    computation does, and trace ids are unique across rounds, so this is the
    same statistic over more data rather than an average of averages.
    """
    from adamast.learning.pipeline.agreement import MetricsCalculator

    errors, assignments = [], {}
    for f in sorted(out.glob("round_*.json")):
        try:
            r = json.loads(f.read_text())
        except Exception:                                      # noqa: BLE001
            continue
        for tr in r.get("results") or []:
            tid = tr.get("trace_id")
            for e in tr.get("typed_errors") or []:
                errors.append({"error_id": f"{tid}_{e.get('error_id')}"})
            for ann, aa in (tr.get("assignments") or {}).items():
                slot = assignments.setdefault(ann, {})
                for eid, codes in (aa or {}).items():
                    slot[f"{tid}_{eid}"] = codes
    if len(errors) < 2 or len(assignments) < 2:
        return None
    k, per_code = MetricsCalculator.compute_fleiss_kappa(
        assignments, errors, gate_taxonomy)

    # A code no annotator ever assigned still receives a per-code kappa, because
    # everyone agreeing it does not apply reads as agreement. Counting those as
    # "exercised" would claim evidence we do not have, so exercised is measured
    # from the assignments themselves.
    exercised = {c for ann in assignments.values()
                 for codes in ann.values() for c in (codes or [])}
    all_ids = set()
    for cat in ("category_a", "category_b", "category_c"):
        all_ids.update((gate_taxonomy.get(cat) or {}).keys())
    return {"kappa": float(k), "n_subjects": len(errors),
            "per_code_kappa": {c: v for c, v in per_code.items() if c in exercised},
            "per_code_kappa_unexercised": sorted(all_ids - exercised),
            "codes_exercised": sorted(exercised & all_ids)}


def gate(taxonomy_flat: dict, draft: dict, corpus: Path, out: Path, model,
         kappa_target=0.75, coverage_floor=0.70):
    summary_f = out / "gate_summary.json"
    if summary_f.exists():
        s = json.loads(summary_f.read_text())
        log(f"gate: already done (kappa={s.get('final_kappa')})")
        return s
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(REPO / "pipeline"))
    from adamast.learning.pipeline.agreement import (Config, TaxonomyRefinerPipeline)
    from adamast.llm.providers import create_provider

    tax_in = out / "taxonomy.input.json"
    tax_in.write_text(json.dumps(to_gate_schema(taxonomy_flat, draft), indent=2))
    # the gate reads a JSONL of normalised traces
    from adamast.core.trace_formats import load_traces, write_normalized_jsonl
    traces = load_traces(str(corpus))
    norm = out / "traces.normalized.jsonl"
    write_normalized_jsonl(traces, norm)
    log(f"gate: {len(traces)} traces, {len(taxonomy_flat['codes'])} codes "
        f"(consumes {Config.CALIBRATION_TRACES + Config.MAX_ROUNDS * Config.TRACES_PER_ROUND})")

    os.environ.setdefault("ADAMAST_PROVIDER", "google")
    os.environ.setdefault("ADAMAST_MODEL", model)
    client = create_provider("google", model)
    pipeline = TaxonomyRefinerPipeline(tax_in, norm, out, client=client)
    summary = pipeline.run()
    if not isinstance(summary, dict):
        raise SystemExit("gate returned no summary")

    # The codebook -- deliberated disambiguation rules and anchor examples -- is
    # produced BY this agreement run, and the kappa reported below was reached
    # with it in every annotator's context. Generation no longer runs an
    # agreement pass, so this is the only place it comes from; a judge applying
    # the taxonomy without it works under easier-to-confuse conditions than the
    # ones measured. It was previously computed and discarded here.
    from adamast.learning.api import build_codebook
    codebook = build_codebook(getattr(pipeline, "shared_kb", None))
    if codebook:
        summary["codebook"] = codebook
        log(f"gate: codebook captured "
            f"({len(codebook.get('learned_rules') or [])} rules, "
            f"{len(codebook.get('anchor_examples') or [])} anchors)")
    last = float(summary.get("final_kappa") or 0.0)
    c = float(summary.get("final_coverage") or 0.0)

    # Certify on the pooled estimate, not the last round. The last round is the
    # smallest sample the run produces and reporting it alone discards most of
    # the evidence that was paid for.
    pooled = pooled_kappa(out, json.loads(tax_in.read_text()))
    if pooled:
        summary["pooled"] = pooled
        k = pooled["kappa"]
        log(f"gate: pooled kappa={k:.3f} over {pooled['n_subjects']} subjects "
            f"({len(pooled['codes_exercised'])} of {len(taxonomy_flat['codes'])} "
            f"codes exercised); last round was {last:.3f} over "
            f"{summary.get('final_kappa_n_subjects')}")
        summary["certified_on"] = "pooled"
    else:
        k = last
        summary["certified_on"] = "final_round"
        log(f"gate: pooling unavailable, falling back to last round {k:.3f}")

    summary["certifying_kappa"] = k
    summary["passed"] = k >= kappa_target and c >= coverage_floor
    summary_f.write_text(json.dumps(summary, indent=2, default=str))
    log(f"gate: kappa={k:.3f} coverage={c:.3f} -> "
        f"{'PASSED' if summary['passed'] else 'NOT PASSED'}")
    return summary


# ------------------------------------------------------------------ judge
def judge(taxonomy_flat: dict, corpus: Path, out: Path, model, workers=4,
          weak_threshold=0.65):
    """Two-pass reflection judge over the refinement corpus."""
    diag_f = out / "diagnoses.json"
    if diag_f.exists():
        d = json.loads(diag_f.read_text())
        log(f"judge: already done ({d['n_traces']} traces)")
        return d
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(REPO / "pipeline"))
    from adamast.core.trace_formats import load_traces
    from adamast.core.taxonomy_data import CostMeter, Taxonomy
    from adamast.judges.reflection_judge import AdaMASTReflectionJudge
    from adamast.learning import reflection_refinement as rr

    taxonomy = Taxonomy.from_flat(taxonomy_flat)
    traces = load_traces(str(corpus))
    pool = [rr._judge_input(rr.outcome_blind_trace(t)) for t in traces]
    pool = [p for p in pool if p.get("trace")]
    log(f"judge: {len(pool)} traces, {len(taxonomy.codes)} codes, {workers} workers")

    judge_obj = AdaMASTReflectionJudge(
        taxonomy, judge_model=model, meter=CostMeter(), mode="two_call",
        weak_mapping_threshold=weak_threshold, llm_call=None)
    results, warnings = rr._run_judge_parallel(judge_obj, pool, workers)
    n_fp = sum(len(r.get("failure_points") or []) for r in results)
    silent = sum(1 for r in results if not (r.get("failure_points") or []))
    log(f"judge: {len(results)} judged, {n_fp} failure points, {silent} silent, "
        f"{len(warnings)} warnings")
    d = {"n_traces": len(results), "results": results, "warnings": warnings[:50]}
    diag_f.write_text(json.dumps(d, indent=2, default=str))
    return d


# ----------------------------------------------------------------- refine
def refine(taxonomy_flat: dict, diagnoses: dict, corpus: Path, structure: dict,
           out: Path, model, panel=4, temperature=0.0):
    """Panel -> agreement -> consolidation -> cross-code operations."""
    final_f = out / "taxonomy_refined.json"
    if final_f.exists():
        log("refine: already done")
        return json.loads(final_f.read_text())
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(REPO / "pipeline"))
    from adamast.core.taxonomy_data import Taxonomy
    from adamast.llm.learning_calls import refine_json
    from .import _refine_parts as P

    taxonomy = Taxonomy.from_flat(taxonomy_flat)
    results = diagnoses["results"]
    traces = {}
    for p in corpus.glob("*.json"):
        msgs = json.loads(p.read_text()).get("messages") or []
        traces[p.stem] = "\n\n".join(m.get("content") or "" for m in msgs
                                     if m.get("role") == "assistant")
    weak, unmapped, fired, util = P.gather(results, traces)
    roles = list(structure["discovered_agents"]["role_details"])
    n_fp = sum(len(r.get("failure_points") or []) for r in results)
    silent = sum(1 for r in results if not (r.get("failure_points") or []))
    header = (f"{P.STYLE}\n## ARCHITECTURE\nroles that exist: {roles}\n"
              f"topology: {structure['architecture']['topology']}\n"
              f"\n## EVIDENCE BASE\n{len(results)} traces judged, {n_fp} failure "
              f"points found, {silent} traces had none.\n"
              f"\n## TAXONOMY, CODE BY CODE\n")
    body = "\n".join(P.code_block(c, util, fired, weak, roles) for c in taxonomy.codes)
    p1 = header + body + "\n" + P.PASS1
    (out / "pass1_prompt.txt").write_text(p1)

    REQUIRED = ("subject", "observable", "style", "category", "role",
                "adequacy", "granularity", "reason")
    FIX = ("name", "definition", "when_to_use", "when_not_to_use")

    def norm(rv):
        if not isinstance(rv, dict) or not isinstance(rv.get("checks"), list):
            return None
        d = {(x.get("code") or x.get("id")): x
             for x in rv["checks"] if isinstance(x, dict)}
        d.pop(None, None)
        for c in taxonomy.codes:
            x = d.get(c.code)
            if x is not None and not x.get("role"):
                x["role"] = "n/a" if c.category != "B" else ""
        return d

    call = gemini_call(temperature)
    pdir = out / "panel"
    pdir.mkdir(exist_ok=True)
    reviewers = []
    for i in range(panel):
        f = pdir / f"reviewer_{i+1}.json"
        if f.exists():
            rv = json.loads(f.read_text())
        else:
            rv = refine_json(p1, model=model, call=call)
            f.write_text(json.dumps(rv, indent=2, default=str))
        d = norm(rv)
        if d is None:
            log(f"  reviewer {i+1}/{panel}: unparseable, dropped")
            continue
        reviewers.append(d)
        log(f"  reviewer {i+1}/{panel}: {len(d)} codes")
    dropped = panel - len(reviewers)
    if dropped:
        # Agreement over a shrunken panel reads HIGHER: fewer voices, fewer
        # ways to disagree. Losing one of four silently would flatter the
        # measurement, so a panel below three is refused rather than reported.
        log(f"  [!] {dropped} of {panel} reviewers dropped -- agreement over a "
            f"shrunken panel is not comparable to a full one")
    if len(reviewers) < min(3, panel):
        raise SystemExit(
            f"only {len(reviewers)} of {panel} reviewers produced a checklist; "
            f"refusing to refine on a panel this thin. Re-run to resume: the "
            f"reviewers that succeeded are cached in {pdir}")

    FIELDS = ("subject", "observable", "style", "category", "adequacy", "granularity")
    split = {}
    for c in (x.code for x in taxonomy.codes):
        s = {f: dict(Counter(r[c].get(f) for r in reviewers if c in r and r[c].get(f)))
             for f in FIELDS}
        s = {f: v for f, v in s.items() if len(v) > 1}
        if s:
            split[c] = s
    log(f"  panel agreement: {len(taxonomy.codes)-len(split)}/{len(taxonomy.codes)} "
        f"unanimous, {len(split)} split")
    for c, s in split.items():
        log(f"    split {c}: {s}")
    (out / "panel_agreement.json").write_text(json.dumps(
        {"n_reviewers": len(reviewers), "temperature": temperature,
         "split": split}, indent=2))

    if len(reviewers) == 1:
        merged = list(reviewers[0].values())
    else:
        rows = []
        for c in (x.code for x in taxonomy.codes):
            rows.append(f"\n### {c}")
            for i, r in enumerate(reviewers, 1):
                x = r.get(c, {})
                rows.append("  reviewer %d: " % i + " ".join(
                    f"{f}={x.get(f)}" for f in FIELDS)
                    + f" :: {(x.get('reason') or '')[:150]}")
        pc = (header + body + f"\n\n## PANEL VERDICTS ({len(reviewers)} reviewers)\n"
              + "\n".join(rows) + "\n" + P.CONSOLIDATE)
        (out / "consolidation_prompt.txt").write_text(pc)
        cf = out / "consolidation_raw.json"
        if cf.exists():
            cr = json.loads(cf.read_text())
        else:
            cr = refine_json(pc, model=model, call=gemini_call(0.0))
            cf.write_text(json.dumps(cr, indent=2, default=str))
        cons = norm(cr) or {}
        merged = []
        for c in taxonomy.codes:
            base = {}
            for f in REQUIRED:
                votes = Counter(r[c.code].get(f) for r in reviewers
                                if c.code in r and r[c.code].get(f))
                if votes:
                    base[f] = votes.most_common(1)[0][0]
            for f in FIX:
                for r in reviewers:
                    v = r.get(c.code, {}).get(f)
                    if v:
                        base[f] = v
                        break
            base.update({k: v for k, v in (cons.get(c.code) or {}).items() if v})
            base["code"] = c.code
            merged.append(base)

    checks = {x["code"]: x for x in merged}
    missing = [c.code for c in taxonomy.codes if c.code not in checks]
    if missing:
        raise SystemExit(f"consolidation omitted {missing}; see {out}")

    def derive(x):
        if x.get("subject") == "environment" or x.get("observable") == "no":
            return "retire"
        if x.get("adequacy") == "covers_two":
            return "split"
        if (x.get("adequacy") in ("too_narrow", "too_broad")
                or x.get("style") == "violates" or x.get("category") != "ok"
                or x.get("granularity") != "ok"):
            return "edit"
        return "keep"

    for x in checks.values():
        x["verdict"] = derive(x)
    log(f"  verdicts: {dict(Counter(x['verdict'] for x in checks.values()))}")

    # cross-code pass
    csum = "\n".join(f"{c}: verdict={x['verdict']} " + " ".join(
        f"{f}={x.get(f)}" for f in FIELDS) for c, x in checks.items())
    um = ["\n## UNMAPPED FAILURE POINTS (ADD signal)\n"] or []
    if not unmapped:
        um.append("None.")
    for s in sorted(unmapped.values(), key=lambda s: -s["support"]):
        um.append(f"\n### {s['name']} (support {s['support']})")
        for e in s["evidence"][:2]:
            um.append(f"- {e['summary']}\n  EVIDENCE: {e['evidence']}")
    p2 = (header + body + "\n\n## PER-CODE CHECKLIST\n" + csum + "\n"
          + "\n".join(um) + "\n" + P.PASS2)
    (out / "pass2_prompt.txt").write_text(p2)
    of = out / "pass2_raw.json"
    if of.exists():
        ops = json.loads(of.read_text())
    else:
        ops = refine_json(p2, model=model, call=gemini_call(0.0))
        of.write_text(json.dumps(ops, indent=2, default=str))
    ops = ops if isinstance(ops, dict) else {}

    idx = {c.code: c for c in taxonomy.codes}
    snap = lambda c, why, how: {
        "id": c.code, "name": c.name, "category": c.category,
        "definition": c.definition, "when_to_use": c.when_to_use,
        "when_not_to_use": c.when_not_to_use, "applies_to_role": c.applies_to_role,
        "times_mapped": util.get(c.code, {}).get("n", 0),
        "removed_by": how, "reason": why}
    retired, applied = [], {k: [] for k in ("merge", "retire", "edit", "split", "add")}

    for mg in (ops.get("merge") or []):
        srcs = [idx.get(x) for x in (mg.get("codes") or [])]
        srcs = [c for c in srcs if c is not None and taxonomy.by_uid(c.uid)]
        if len(srcs) < 2 or not mg.get("name"):
            continue
        cat = mg.get("category") if mg.get("category") in ("A", "B", "C") else srcs[0].category
        uid = taxonomy.add(cat, dict(mg))
        for s in srcs:
            retired.append(snap(s, mg.get("reason", ""), "merge"))
            taxonomy.retire(s.uid)
        new = taxonomy.by_uid(uid)
        applied["merge"].append(f"{'+'.join(s.code for s in srcs)} -> "
                                f"{new.code if new else '?'} {mg['name']}")
    for code, x in checks.items():
        if x["verdict"] != "retire":
            continue
        c = idx.get(code)
        if c and taxonomy.by_uid(c.uid):
            why = "environment" if x.get("subject") == "environment" else "unobservable"
            retired.append(snap(c, f"[{why}] {x.get('reason','')}", "retire"))
            taxonomy.retire(c.uid)
            applied["retire"].append(f"{code} {c.name} [{why}]")
    for code, x in checks.items():
        if x["verdict"] != "edit":
            continue
        c = idx.get(code)
        if not c or not taxonomy.by_uid(c.uid):
            continue
        fields = {k: x.get(k) for k in FIX}
        if x.get("category") in ("A", "B", "C") and x["category"] != c.category:
            fields["category"] = x["category"]
        taxonomy.edit(c.uid, **fields)
        applied["edit"].append(f"{code}: adequacy={x.get('adequacy')} "
                               f"style={x.get('style')}")
    for sp in (ops.get("split") or []):
        c = idx.get(sp.get("code")) if isinstance(sp, dict) else None
        kids = sp.get("into") or []
        if c and taxonomy.by_uid(c.uid) and len(kids) >= 2:
            taxonomy.split(c.uid, kids)
            applied["split"].append(f"{c.code} -> {len(kids)}")
    for ad in (ops.get("add") or []):
        if ad.get("category") in ("A", "B", "C") and ad.get("name"):
            taxonomy.add(ad["category"], dict(ad))
            applied["add"].append(f"{ad['category']}: {ad['name']}")

    flat = {"repo": taxonomy_flat.get("repo", ""),
            "domain": taxonomy_flat.get("domain", ""),
            "codes": [{"id": c.code, "name": c.name, "description": c.definition,
                       "category": c.category, "when_to_use": c.when_to_use,
                       "when_not_to_use": c.when_not_to_use,
                       **({"applies_to_role": c.applies_to_role}
                          if c.category == "B" and c.applies_to_role else {})}
                      for c in taxonomy.codes]}
    final_f.write_text(json.dumps(flat, indent=2))
    (out / "retired").mkdir(exist_ok=True)
    (out / "retired/retired_codes.json").write_text(json.dumps(
        {"n_retired": len(retired), "codes": retired,
         "note": "removed from the active taxonomy, preserved for analysis; "
                 "ids are never reused"}, indent=2))
    (out / "refine_report.json").write_text(json.dumps(
        {"codes_before": len(taxonomy_flat["codes"]), "codes_after": len(flat["codes"]),
         "panel_split": split, "applied": applied,
         "checklist": {c: {**{k: x.get(k) for k in REQUIRED},
                           "verdict": x["verdict"]} for c, x in checks.items()}},
        indent=2))
    log(f"refine: {len(taxonomy_flat['codes'])} -> {len(flat['codes'])} codes, "
        f"retired {len(retired)}")
    for k, v in applied.items():
        for x in v:
            log(f"    {k.upper()}: {x}")
    return flat
