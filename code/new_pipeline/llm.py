#!/usr/bin/env python3
"""Model-call transports shared by every stage: Gemini direct, OpenRouter and
Arena, with retries, backoff and a plain log(). Lifted from pipeline/taxonomy/stages.py
(2026-09-06); nothing here depends on the earlier pipeline.

    call, model = llm_call("openrouter/google/gemini-3.6-flash", temperature=0.0)
    raw = call(prompt, model)
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
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
                cd = u.get("cost_details") or {}
                # a BYOK call (the Anthropic decider) reports cost=0 on OpenRouter and is
                # billed upstream; log that figure too so the run's spend can be summed
                usage = (f"prompt={u.get('prompt_tokens')} "
                         f"thoughts={det.get('reasoning_tokens')} "
                         f"answer={u.get('completion_tokens')} "
                         f"cost={u.get('cost')} upstream={cd.get('upstream_inference_cost')} "
                         f"byok={u.get('is_byok')} model={resp.get('model')}")
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


# Arena (api.preview.arena.ai), probed 2026-09-23. Its chat-completions endpoint is
# OpenAI-compatible with three differences that matter here: the gpt-5.x models reject
# `temperature`; Claude models reject `response_format: json_object` (Arena turns it into
# an Anthropic structured-output schema, which then needs a schema), so they are sent the
# prompt's own JSON instruction only -- every parser in this package already finds fenced
# or prefixed JSON; and the Cloudflare front refuses Python-urllib's default User-Agent
# (error 1010), so the OpenAI SDK's own header is sent. Usage carries tokens, reasoning
# tokens and the upstream cost, like OpenRouter's.
ARENA_URL = "https://api.preview.arena.ai/v1/chat/completions"
RATE_LIMIT_WAIT_FOR = 1200.0     # seconds a call waits out HTTP 429 in total before counting it as a failure
RATE_LIMIT_MAX_DELAY = 120.0     # longest single wait: 10, 20, 40, 80, 120, 120, ... s, plus up to 5 s jitter
ARENA_NO_TEMPERATURE = ("gpt-5", "o1", "o3", "o4")
ARENA_NO_JSON_MODE = ("claude",)


def arena_call(temperature=0.0, retries=5, max_output=16384, timeout=300,
               thinking=None):
    """Same contract as openrouter_call, over Arena's chat completions.

    Model ids are Arena's own ("claude-sonnet-5", "gpt-5.6-sol", "gemini-3.8-flash";
    GET /v1/models lists what the key may use). The key is ARENA_API_KEY in the
    environment; nothing here ever logs it. thinking maps to `reasoning_effort`
    (low / medium / high; MINIMAL is sent as low, which is the lowest Arena accepts).
    """
    import urllib.request
    import urllib.error

    def _call(prompt, model):
        key = os.environ.get("ARENA_API_KEY")
        if not key:
            log("  [!] ARENA_API_KEY not set")
            return None
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_output,
        }
        if not model.startswith(ARENA_NO_TEMPERATURE):
            body["temperature"] = temperature
        if not model.startswith(ARENA_NO_JSON_MODE):
            body["response_format"] = {"type": "json_object"}
        if thinking:
            # low / medium / high everywhere; "minimal" is refused even by the gpt models
            effort = str(thinking).lower()
            body["reasoning_effort"] = "low" if effort == "minimal" else effort
        data = json.dumps(body).encode()
        delay = 5.0
        net_wait = {"t": 0.0}
        rate_wait = {"t": 0.0, "n": 0}
        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                req = urllib.request.Request(
                    ARENA_URL, data=data,
                    headers={"Content-Type": "application/json",
                             "Accept": "application/json",
                             "Authorization": f"Bearer {key}",
                             "User-Agent": "OpenAI/Python 1.109.1"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    resp = json.loads(r.read().decode())
                if resp.get("error"):
                    e = resp["error"]
                    code = e.get("code")
                    msg = f"arena error {code}: {e.get('message')}"
                    if code in (429, 502, 503, 504, 408):
                        raise Transient(msg)
                    log(f"  [!] non-transient LLM error: {msg[:160]}")
                    return None
                ch = (resp.get("choices") or [{}])[0]
                text = ((ch.get("message") or {}).get("content")) or ""
                fr = ch.get("finish_reason")
                u = resp.get("usage") or {}
                det = u.get("completion_tokens_details") or {}
                cd = u.get("cost_details") or {}
                usage = (f"prompt={u.get('prompt_tokens')} "
                         f"thoughts={det.get('reasoning_tokens')} "
                         f"answer={u.get('completion_tokens')} "
                         f"cost={u.get('cost')} upstream={cd.get('upstream_inference_cost')} "
                         f"model={resp.get('model')}")
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
                if exc.code == 429 and rate_wait["t"] < RATE_LIMIT_WAIT_FOR:
                    # A rate limit is the key's quota refilling, not a failed call: wait it out
                    # on its own budget instead of spending the call's retries (seen 2026-09-24:
                    # three concurrent runs exhausted 5 attempts / 75 s and stopped a stage).
                    w = min(RATE_LIMIT_MAX_DELAY, 10.0 * 2 ** rate_wait["n"]) + random.uniform(0, 5)
                    rate_wait["n"] += 1; rate_wait["t"] += w
                    log(f"  [!] rate limited (wait {rate_wait['n']}, {rate_wait['t']/60:.1f} of "
                        f"{RATE_LIMIT_WAIT_FOR/60:.0f} min), retry in {w:.0f}s: {msg[:90]}")
                    time.sleep(w)
                    attempt -= 1
                    continue
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
    goes to OpenRouter, "arena/<model>" to Arena (prefix stripped either way),
    anything else to Gemini."""
    if model.startswith("openrouter/"):
        return openrouter_call(**kw), model[len("openrouter/"):]
    if model.startswith("arena/"):
        return arena_call(**kw), model[len("arena/"):]
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


