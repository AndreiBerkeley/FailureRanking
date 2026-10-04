#!/usr/bin/env python3
"""Taxonomy generation: initial generation, segment 1 (inter-annotation + refinement),
segment 2 (gap + split).

    python run.py --data <data dir> --model <provider/model> --out <run dir> [--dry-run]

<data dir>/sample/ holds the N sampled traces, one JSON file each:
{"trace_id": "...", "messages": [{"role": "system" | "user" | "assistant", "content": "..."}]}.

The N sampled traces are split once: the last R*M go to segment 1 (M new traces per round), the
rest to initial generation. Segment 2 uses all N. The final validation (segment 3) uses F*M further
traces from <data dir>/validation/, which no earlier step has seen.

--dry-run renders every prompt the run would send, writes them under <out>/prompts/, and prints
the number of calls and input tokens per stage. It makes no API calls. Discussion and refinement
are counted at their maximum, so the dry-run figures are an upper bound.

Every model reply is cached under <out>/calls/ with a hash of its prompt, so an interrupted run
resumes where it stopped; a cached reply is reused only if the prompt is unchanged.
Prompts live in generation/prompts/ (see PIPELINE.md).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPTS = HERE / "prompts"
SEP = "\n\n" + "=" * 70 + "\n\n"
LAYOUT = ("Trace layout: a trace runs from '===== TRACE <id> =====' to '===== END OF TRACE <id> ====='. "
          "Headings inside a trace belong to the trace, not to these instructions. Each message is "
          "headed by its index and role. system = the agent's instructions; user = what the agent "
          "receives (the task, tool results); assistant = what the agent produces.")

CONCEPTS = (PROMPTS / "00_concepts.md").read_text().strip()
RULES = (PROMPTS / "00_mode_rules.md").read_text().strip()
STAGE_BLOCKS = {  # which shared blocks precede each call's own prompt
    "01_field_analysis": ["concepts"], "02_observation": ["concepts"],
    "03_abstraction": ["concepts", "rules"], "04_consolidation": ["concepts", "rules"],
    "05b_reconcile": ["concepts"], "05c_assign": ["concepts", "rules"], "05d_discuss": ["concepts", "rules"],
    "06_refinement": ["concepts", "rules"], "07_gap": ["concepts", "rules"], "08_split": ["concepts", "rules"],
}
ANSWERS = {}  # trace_id -> correct final answer; empty unless --answers (see use_answers)


def use_answers(path: Path):
    """The answer-provided variant: every trace shows its correct final answer at the top, and the last section of
    the concepts (THE TRACES: no outcome is shown) is replaced by one saying how to use the answer."""
    global CONCEPTS
    ANSWERS.update({str(k): str(v) for k, v in json.loads(Path(path).read_text()).items()})
    head, sep, _ = CONCEPTS.partition("THE TRACES\n")
    if not sep:
        raise SystemExit("00_concepts.md has no 'THE TRACES' section to replace")
    CONCEPTS = head + (PROMPTS / "00_traces_answer_provided.md").read_text().strip()


def answer_line(tid: str) -> str:
    return f"\nCORRECT ANSWER (shown to you only; the agent system never saw it): {ANSWERS[tid]}" if tid in ANSWERS else ""


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- prompts and traces

def build(stage: str, **fields) -> str:
    body = (PROMPTS / f"{stage}.md").read_text().strip()
    for key in fields:
        if "{" + key + "}" not in body:
            raise SystemExit(f"{stage}: placeholder {{{key}}} not in prompt")
    for key, val in fields.items():
        body = body.replace("{" + key + "}", val)
    left = [m for m in re.findall(r"\{([a-z_]+)\}", (PROMPTS / f"{stage}.md").read_text()) if m not in fields]
    if left:
        raise SystemExit(f"{stage}: unfilled placeholders {left}")
    return SEP.join([{"concepts": CONCEPTS, "rules": RULES}[b] for b in STAGE_BLOCKS[stage]] + [body])


def render(trace: dict) -> str:
    """The whole trace as one text. Nothing is ever cut."""
    tid = trace["trace_id"]
    parts = [f"===== TRACE {tid} =====" + answer_line(tid)] + [f"----- [{i}] {m['role']} -----\n{m.get('content') or ''}"
                                             for i, m in enumerate(trace["messages"])]
    return "\n".join(parts) + f"\n===== END OF TRACE {tid} ====="


def split_trace(trace: dict, budget: int) -> list[dict]:
    """The trace as consecutive parts of at most `budget` characters. A trace that fits is one part, rendered
    exactly as render() does. A longer one is split between messages, and a message longer than a part is split
    inside; every character is kept, and each part is labelled with its number."""
    tid = trace["trace_id"]
    whole = render(trace)
    if len(whole) <= budget:
        return [{"trace_id": tid, "part": 1, "parts": 1, "text": whole}]
    room = budget - 300  # for the part header and footer
    pieces = []
    for i, m in enumerate(trace["messages"]):
        head, body = f"----- [{i}] {m['role']} -----\n", m.get("content") or ""
        while len(head) + len(body) > room:
            cut = room - len(head)
            pieces.append(head + body[:cut])
            head, body = f"----- [{i}] {m['role']} (continued) -----\n", body[cut:]
        pieces.append(head + body)
    groups, cur, size = [], [], 0
    for p in pieces:
        if cur and size + len(p) + 1 > room:
            groups.append(cur)
            cur, size = [], 0
        cur.append(p)
        size += len(p) + 1
    groups.append(cur)
    n = len(groups)
    return [{"trace_id": tid, "part": k, "parts": n,
             "text": f"===== TRACE {tid}, PART {k} OF {n}: the trace is too long for one call, so the other "
                     f"parts may not be shown here =====" + answer_line(tid) + "\n" + "\n".join(g) + f"\n===== END OF TRACE {tid}, PART {k} OF {n} ====="}
            for k, g in enumerate(groups, 1)]


def ukey(u) -> str:
    """A trace that fits in one part keeps its plain id, so its call names and prompts match an unsplit run."""
    return u["trace_id"] if u["parts"] == 1 else f"{u['trace_id']}_p{u['part']}"


def block(units) -> str:
    return LAYOUT + "\n\n" + "\n\n".join(u["text"] for u in units)


def canon(s: str) -> str:
    """Compare quotes on text, not escaping: models often copy '\\n' literally."""
    s = (s or "").replace("\\n", " ").replace("\\t", " ").replace('\\"', '"').replace("\\'", "'")
    return re.sub(r"\s+", " ", s).strip()


VARIANT = ""  # set by --variant: suffix for every file and new reply this run writes, so it sits beside the original


def vx(name: str) -> str:
    """A call or file name with the variant suffix: final_taxonomy.json -> final_taxonomy_<variant>.json."""
    if not VARIANT:
        return name
    for ext in (".jsonl", ".json", ".txt"):
        if name.endswith(ext):
            return name[: -len(ext)] + f"_{VARIANT}{ext}"
    return f"{name}_{VARIANT}"


def dump(obj) -> str:
    return json.dumps(obj, indent=2)


# ---------------------------------------------------------------- model calls

class Runner:
    def __init__(self, a):
        self.a, self.out = a, a.out
        self.calls_dir = a.out / "calls"; self.calls_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_dir = a.out / "prompts"; self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.stats = defaultdict(lambda: {"calls": 0, "input_tokens_est": 0})
        self.call = None
        self.units = {}  # trace_id -> its parts (see split_trace)
        self.call_log = a.out / vx("call_log.jsonl")  # one line per call attempt; read by call_report.py
        self.log_lock = threading.Lock()
        if not a.dry_run:
            sys.path.insert(0, str(HERE))
            from llm import llm_call
            self.call, self.model = llm_call(a.model, temperature=a.temperature, max_output=a.max_output)

    def parts(self, traces):
        return [u for t in traces for u in self.units[t["trace_id"]]]

    def ask(self, name: str, stage: str, prompt: str, temperature=None) -> dict | None:
        if len(prompt) > self.a.prompt_chars:
            raise SystemExit(f"{name}: prompt is {len(prompt):,} characters, over the {self.a.prompt_chars:,} that fit "
                             f"the context; raise --reserve-chars so traces are split into smaller parts")
        self.stats[stage]["calls"] += 1
        self.stats[stage]["input_tokens_est"] += len(prompt) // 4
        base, name = name, vx(name)  # a variant never writes over the original run's files
        (self.prompt_dir / f"{name}.txt").write_text(prompt)
        if self.a.dry_run:
            return None
        sha = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        for cand in dict.fromkeys([base, name]):  # the original run's reply first, then this variant's
            path = self.calls_dir / f"{cand}.json"
            if path.exists():
                cached = json.loads(path.read_text())
                if cached.get("prompt_sha") == sha:
                    return cached["parsed"]
        cache = self.calls_dir / f"{name}.json"
        if cache.exists():
            log(f"  {name}: cached reply was for a different prompt; calling again")
        call = self.call
        if temperature is not None and temperature != self.a.temperature:
            from llm import llm_call
            call, _ = llm_call(self.a.model, temperature=temperature, max_output=self.a.max_output)
        import llm
        last = None
        for attempt in range(3):
            raw = call(prompt if attempt == 0 else prompt + "\n\nReturn ONLY valid JSON, nothing else.", self.model)
            meta = dict(getattr(llm.LAST, "meta", {}))
            try:
                parsed = parse_json(raw)
                cache.write_text(json.dumps({"prompt_sha": sha, "parsed": parsed, "raw": raw, "meta": meta}))
                self.record(name, stage, attempt, raw, meta, None)
                return parsed
            except ValueError as e:
                last = e
                (self.calls_dir / f"{name}.failed_attempt{attempt + 1}.txt").write_text(raw or "")
                self.record(name, stage, attempt, raw, meta, str(e))
                log(f"  {name}: unparseable reply (attempt {attempt + 1}, {len(raw or '')} chars): {e}")
        raise SystemExit(f"{name}: no parseable JSON after 3 attempts: {last}")

    def record(self, name, stage, attempt, raw, meta, error):
        line = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "call": name, "stage": stage, "attempt": attempt + 1,
                "ok": error is None, "reply_chars": len(raw or ""), "max_output": self.a.max_output,
                **meta, "parse_error": error}
        with self.log_lock, self.call_log.open("a") as fh:
            fh.write(json.dumps(line) + "\n")

    def many(self, jobs):
        """jobs: list of (name, stage, prompt, temperature). Runs in parallel, returns results in order."""
        with cf.ThreadPoolExecutor(max_workers=self.a.workers) as ex:
            return list(ex.map(lambda j: self.ask(*j), jobs))


def parse_json(raw: str):
    s = (raw or "").strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        i, j = s.find("{"), s.rfind("}")
        if i < 0 or j <= i:
            raise ValueError("no JSON object found")
        try:
            return json.loads(s[i:j + 1])
        except json.JSONDecodeError as e:
            raise ValueError(str(e))


# ---------------------------------------------------------------- stub data for --dry-run

def stub_taxonomy(n=25):
    return [{"id": f"FM-{i:02d}", "name": "x" * 30, "definition": "x" * 200, "when_to_use": "x" * 200,
             "when_not_to_use": "x" * 200, "origin": "observed",
             "instances": [{"instance_id": f"I{i}", "trace_id": "t", "quote": "x" * 80, "missing": None,
                            "what_went_wrong": "x" * 80}] * 4, "possible_at": []} for i in range(1, n + 1)]


def stub_failures(n=8):
    return [{"failure_id": f"F{i}", "quote": "x" * 80, "missing": None, "what_went_wrong": "x" * 80} for i in range(1, n + 1)]


def with_examples(taxonomy, n=2, chars=300):
    """The taxonomy as the gap step sees it: each mode's text plus its first n instances as examples."""
    return [dict({f: m.get(f) for f in ("id", "name", "definition", "when_to_use", "when_not_to_use")},
                 examples=[{"quote": (i.get("quote") or "")[:chars] or None, "missing": i.get("missing"),
                            "what_went_wrong": i.get("what_went_wrong")} for i in m.get("instances", [])[:n]])
            for m in taxonomy]


def slim(taxonomy):
    """The taxonomy as annotators see it: no instances."""
    return [{k: m.get(k) for k in ("id", "name", "definition", "when_to_use", "when_not_to_use")} for m in taxonomy]


# ---------------------------------------------------------------- checks and statistics

def check_quotes(items, trace_text_by_id):
    bad = 0
    for x in items:
        q = x.get("quote")
        ok = q is None or canon(q) in canon(trace_text_by_id.get(x.get("trace_id"), ""))
        x["quote_valid"] = ok
        bad += not ok
    return bad


def account(modes, ids, extra_ids=()):
    seen = Counter(i["instance_id"] for m in modes for i in m.get("instances", []))
    seen.update(extra_ids)
    missing = [i for i in ids if seen[i] == 0]
    dup = [i for i, c in seen.items() if c > 1]
    return missing, dup


def fleiss(counts, k):
    """Binary Fleiss kappa. counts: per item, the number of annotators (of k) marking it."""
    n = len(counts)
    if n == 0 or k < 2:
        return None
    p_yes = sum(counts) / (n * k)
    pe = p_yes ** 2 + (1 - p_yes) ** 2
    P = [(c * (c - 1) + (k - c) * (k - c - 1)) / (k * (k - 1)) for c in counts]
    po = sum(P) / n
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def cohen(x, y):
    n = len(x)
    if n == 0:
        return None
    po = sum(a == b for a, b in zip(x, y)) / n
    cx, cy = Counter(x), Counter(y)
    pe = sum(cx[c] * cy[c] for c in cx) / (n * n)
    if pe == 1:
        return 1.0 if po == 1 else None
    return (po - pe) / (1 - pe)


def mean_pairwise_kappa(rows):
    """rows: one label list per annotator, over the same failures. Mean of pairwise Cohen's kappa."""
    ks = [cohen(rows[i], rows[j]) for i, j in combinations(range(len(rows)), 2)]
    ks = [k for k in ks if k is not None]
    return round(sum(ks) / len(ks), 3) if ks else None


def norm_mode(m):
    m = str(m or "NONE").strip()
    return "NONE" if m.upper() == "NONE" else m


def agreement(labels, fids, mode_ids):
    """labels[k][fid] = {"mode", "why"}."""
    K = len(labels)
    rows = [[labels[k][f]["mode"] for f in fids] for k in range(K)]
    per_mode = {}
    for mid in mode_ids:
        counts = [sum(rows[k][i] == mid for k in range(K)) for i in range(len(fids))]
        if any(counts):
            per_mode[mid] = {"kappa": fleiss(counts, K), "failures_any": sum(c > 0 for c in counts),
                             "failures_all": sum(c == K for c in counts)}
    n_labels = K * len(fids)
    n_none = sum(m == "NONE" for row in rows for m in row)
    return {"annotators": K, "failures": len(fids), "kappa": mean_pairwise_kappa(rows),
            "coverage": round(1 - n_none / n_labels, 3) if n_labels else None,
            "none_labels": n_none, "labels": n_labels, "per_mode": per_mode}


def as_instance(x, instance_id):
    return {"instance_id": instance_id, "trace_id": x.get("trace_id"), "quote": x.get("quote"),
            "missing": x.get("missing"), "what_went_wrong": x.get("what_went_wrong")}


# ---------------------------------------------------------------- editing a taxonomy in place

EDIT_FIELDS = ("name", "definition", "when_to_use", "when_not_to_use")


def next_free(modes) -> int:
    return 1 + max((int(re.sub(r"\D", "", m["id"]) or 0) for m in modes if str(m["id"]).startswith("FM-")), default=0)


def apply_edits(modes, edits, stamp=None):
    """Apply a reply of merges and rewrites to `modes`, instead of having the model write the taxonomy out again.
    A mode the reply does not mention is unchanged. A merged mode keeps every instance of its members and the id
    of its first FM member. `stamp` (e.g. {"round": 1}) marks each mode the edits touch, under "refinement".
    Returns (modes, log)."""
    modes = [json.loads(json.dumps(m)) for m in modes]
    by_id, pos = {m["id"]: m for m in modes}, {m["id"]: i for i, m in enumerate(modes)}
    gone, log = set(), []

    def mark(m, change, why, **extra):
        if stamp is not None:
            m.setdefault("refinement", []).append(dict(stamp, change=change, why=why, **extra))

    for g in (edits or {}).get("merges") or []:
        ids = [i for i in dict.fromkeys(g.get("ids") or []) if i in by_id and i not in gone]
        if len(ids) < 2:
            log.append({"change": "merge skipped", "ids": g.get("ids"), "why": "fewer than two known modes"})
            continue
        ids.sort(key=lambda i: (not str(i).startswith("FM-"), pos[i]))
        keep = by_id[ids[0]]
        for i in ids[1:]:
            keep["instances"] = keep.get("instances", []) + by_id[i].get("instances", [])
            keep["possible_at"] = keep.get("possible_at", []) + by_id[i].get("possible_at", [])
            gone.add(i)
        if any(by_id[i].get("origin") == "observed" for i in ids):
            keep["origin"] = "observed"
        for f in EDIT_FIELDS:
            if g.get(f):
                keep[f] = g[f]
        keep["merged_from"] = keep.get("merged_from", []) + ids
        mark(keep, "merged", g.get("why"), merged=ids)
        log.append({"change": "merged", "ids": ids, "into": ids[0], "why": g.get("why")})
    for w in (edits or {}).get("rewrites") or []:
        m = by_id.get(w.get("id"))
        if m is None or m["id"] in gone:
            log.append({"change": "rewrite skipped", "id": w.get("id"), "why": "unknown or merged-away mode"})
            continue
        fields = [f for f in EDIT_FIELDS if w.get(f)]
        for f in fields:
            m[f] = w[f]
        change = w.get("change") or "rewritten"
        mark(m, change, w.get("why"), fields=fields)
        log.append({"change": change, "id": m["id"], "fields": fields, "why": w.get("why")})
    return [m for m in modes if m["id"] not in gone], log


def assign_ids(modes):
    """Give every mode that is not yet an FM mode (a gap proposal P-...) the next free FM id.
    Returns (modes, {old id: new id})."""
    n, mapping = next_free(modes), {}
    for m in modes:
        if not str(m["id"]).startswith("FM-"):
            mapping[m["id"]] = f"FM-{n:02d}"
            m["proposed_as"], m["id"] = m["id"], mapping[m["id"]]
            n += 1
    return modes, mapping


def merged_into(log):
    """{id of a merged-away mode: id of the mode it was merged into}, from an apply_edits log."""
    return {i: c["into"] for c in log if c.get("change") == "merged" for i in c["ids"] if i != c["into"]}


def rename_refs(modes, mapping):
    """Rewrite mode ids that the text fields mention, after modes were merged or given new ids, so a
    when_not_to_use never points at an id that no longer exists."""
    mapping = {k: v for k, v in mapping.items() if k != v}
    if mapping:
        pat = re.compile(r"\b(" + "|".join(sorted(map(re.escape, mapping), key=len, reverse=True)) + r")\b")
        for m in modes:
            for f in EDIT_FIELDS:
                if isinstance(m.get(f), str):
                    m[f] = pat.sub(lambda x: mapping[x.group(1)], m[f])
    return modes


def resolve(merges, renames):
    """Old id -> final id, following a merge first and then a new id."""
    ids = set(merges) | set(renames) | set(merges.values())
    return {i: renames.get(merges.get(i, i), merges.get(i, i)) for i in ids}


def apply_refinement(taxonomy, edits, rnd, unfitted):
    """Refinement edits: rewrites (which may also take unfitted instances), merges, and added modes. Every mode they
    touch carries a "refinement" entry: round, change, why."""
    tax, log = apply_edits(taxonomy, edits, stamp={"round": rnd})
    tax = rename_refs(tax, merged_into(log))
    by_id, unf = {m["id"]: m for m in tax}, {u["instance_id"]: u for u in unfitted}
    for w in (edits or {}).get("rewrites") or []:
        m = by_id.get(w.get("id"))
        got = [unf[i] for i in w.get("instance_ids") or [] if i in unf]
        if m is not None and got:
            m["instances"] = m.get("instances", []) + got
    n = next_free(tax)
    for x in (edits or {}).get("added") or []:
        got = [unf[i] for i in x.get("instance_ids") or [] if i in unf]
        if not got:
            log.append({"change": "add skipped", "name": x.get("name"), "why": "no known unfitted instance"})
            continue
        tax.append({"id": f"FM-{n:02d}", **{f: x.get(f) for f in EDIT_FIELDS}, "origin": "observed",
                    "instances": got, "possible_at": [],
                    "refinement": [{"round": rnd, "change": "added", "why": x.get("why")}]})
        log.append({"change": "added", "id": f"FM-{n:02d}", "why": x.get("why")})
        n += 1
    return tax, log


# ---------------------------------------------------------------- initial generation

def initial_generation(r: Runner, traces, text_by_id):
    a = r.a
    parts = r.parts(traces)
    calls, cur, size = [], [], 0  # as many whole parts per call as fit
    for u in parts:
        if cur and size + len(u["text"]) + 2 > a.trace_budget:
            calls.append(cur)
            cur, size = [], 0
        cur.append(u)
        size += len(u["text"]) + 2
    calls.append(cur)
    log(f"initial generation: call 1 field analysis over {len(traces)} full traces"
        + (f", in {len(calls)} calls because they do not fit in one" if len(calls) > 1 else ""))
    fas = r.many([("01_field_analysis" if len(calls) == 1 else f"01_field_analysis_c{i + 1}", "01_field_analysis",
                   build("01_field_analysis", traces=block(c)), None) for i, c in enumerate(calls)])
    fa = fas[0] if len(fas) == 1 else fas
    if not a.dry_run:
        (r.out / vx("01_field_analysis.json")).write_text(dump(fa))
    fa_text = dump(fa if not a.dry_run else {"field": "x" * 3000})

    log(f"initial generation: call 2 observation over {len(traces)} traces"
        + (f" ({len(parts)} parts)" if len(parts) > len(traces) else ""))
    groups = [parts[i:i + a.traces_per_call] for i in range(0, len(parts), a.traces_per_call)]
    obs = r.many([(f"02_observation_{ukey(g[0])}" if len(g) == 1 else f"02_observation_g{gi:02d}",
                   "02_observation", build("02_observation", field_analysis=fa_text, traces=block(g)), None)
                  for gi, g in enumerate(groups)])
    instances = []
    if not a.dry_run:
        for res, g in zip(obs, groups):
            for t in res.get("traces", []):
                for x in t.get("instances", []):
                    x["trace_id"] = g[0]["trace_id"] if len(g) == 1 else t.get("trace_id")
                    instances.append(x)
        for n, x in enumerate(instances, 1):
            x["instance_id"] = f"I{n}"
        bad = check_quotes(instances, text_by_id)
        log(f"  {len(instances)} instances; {bad} quotes not found verbatim in their trace")
        (r.out / vx("02_instances.json")).write_text(dump(instances))

    log("initial generation: call 3 abstraction")
    inst_text = dump(instances if not a.dry_run else [{"instance_id": f"I{i}", "trace_id": "t", "quote": "x" * 80,
                                                       "what_went_wrong": "x" * 80, "should_have": "x" * 80}
                                                      for i in range(1, 5 * len(traces))])
    ab = r.ask("03_abstraction", "03_abstraction", build("03_abstraction", field_analysis=fa_text, instances=inst_text))
    if not a.dry_run:
        by_id = {x["instance_id"]: x for x in instances}
        unknown = []
        for m in ab.get("modes", []):  # the reply names instances by id; their records come from observation
            ids = m.pop("instance_ids", [])
            unknown += [i for i in ids if i not in by_id]
            m["instances"] = [{k: by_id[i].get(k) for k in ("instance_id", "trace_id", "quote", "missing", "what_went_wrong")}
                              for i in ids if i in by_id]
        if unknown:
            log(f"  abstraction named {len(unknown)} instance ids that observation did not produce: {unknown[:10]}")
        missing, dup = account(ab.get("modes", []), [x["instance_id"] for x in instances],
                               [u.get("instance_id") for u in ab.get("unplaced", [])])
        log(f"  {len(ab.get('modes', []))} draft modes; {len(ab.get('unplaced', []))} unplaced; "
            f"{len(missing)} instances unaccounted; {len(dup)} in more than one mode")
        ab["_accounting"] = {"missing": missing, "duplicated": dup, "unknown_ids": unknown}
        (r.out / vx("03_draft_modes.json")).write_text(dump(ab))

    log("initial generation: call 4 consolidation")
    modes = ab.get("modes", []) if ab else stub_taxonomy()
    co = r.ask("04_consolidation", "04_consolidation", build("04_consolidation", modes=dump(modes)))
    tax = stub_taxonomy()
    if not a.dry_run:
        tax, changes = apply_edits(modes, co)
        tax, renames = assign_ids(tax)
        tax = rename_refs(tax, resolve(merged_into(changes), renames))
        in_draft = {i["instance_id"] for m in modes for i in m.get("instances", [])}
        missing, dup = account(tax, sorted(in_draft))
        log(f"  {len(tax)} modes; {len(changes)} edits; {len(missing)} draft instances lost; {len(dup)} duplicated")
        (r.out / vx("04_taxonomy_initial.json")).write_text(dump({"taxonomy": tax, "changes": changes, "edits": co,
                                                             "_accounting": {"missing": missing, "duplicated": dup}}))
    return tax, fa_text


# ---------------------------------------------------------------- segment 1: inter-annotation + refinement

def discover(r: Runner, traces, fa_text, tag):
    """Phase 1: each of K annotators finds failure instances in each trace (or trace part) on its own."""
    a = r.a
    parts = r.parts(traces)
    res = r.many([(f"05a_{tag}_discover_a{k + 1}_{ukey(u)}", "05a_discovery",
                   build("02_observation", field_analysis=fa_text, traces=block([u])),
                   a.annotator_temperature) for k in range(a.annotators) for u in parts])
    if a.dry_run:
        return None
    found, it = defaultdict(dict), iter(res)  # found[part key][annotator] = instances
    for k in range(a.annotators):
        for u in parts:
            got = next(it) or {}
            found[ukey(u)][f"A{k + 1}"] = [
                {f: x.get(f) for f in ("step", "quote", "missing", "what_went_wrong")}
                for tr in got.get("traces", []) for x in tr.get("instances", [])]
    return found


def reconcile(r: Runner, traces, found, tag, pre, text_by_id):
    """Phase 2: match the annotators' findings per trace (or part); keep failures found by at least Q annotators."""
    a = r.a
    parts = r.parts(traces)
    res = r.many([(f"05b_{tag}_reconcile_{ukey(u)}", "05b_reconcile",
                   build("05b_reconcile", traces=block([u]),
                         findings=dump(found[ukey(u)] if found else
                                       {f"A{k + 1}": stub_failures(8) for k in range(a.annotators)})),
                   None) for u in parts])
    if a.dry_run:
        return None
    failures, dropped, n = defaultdict(list), 0, 0  # failures[part key] = kept failures
    for u, rec in zip(parts, res):
        for x in (rec or {}).get("failures", []):
            by = sorted({str(b).strip() for b in x.get("found_by", [])})
            if len(by) < a.quorum:
                dropped += 1
                continue
            n += 1
            failures[ukey(u)].append({"failure_id": f"{pre}F{n}", "trace_id": u["trace_id"], "found_by": by,
                                            "quote": x.get("quote"), "missing": x.get("missing"),
                                            "what_went_wrong": x.get("what_went_wrong")})
    kept = [f for v in failures.values() for f in v]
    bad = check_quotes(kept, text_by_id)
    log(f"  reconciliation: {n} failures kept (found by at least {a.quorum} annotators), {dropped} dropped; "
        f"{bad} quotes not verbatim")
    return failures


def label_items(res, keys):
    """res: a model reply with "labels"; keys: the failure ids asked about. Missing labels become NONE."""
    got = {str(x.get("failure_id")): x for x in (res or {}).get("labels", [])}
    out, missing = {}, 0
    for fid in keys:
        x = got.get(fid)
        missing += x is None
        out[fid] = {"mode": norm_mode(x.get("mode") if x else None), "why": (x or {}).get("why")}
    return out, missing


def public(f):
    return {k: f.get(k) for k in ("failure_id", "quote", "missing", "what_went_wrong")}


def assign(r: Runner, taxonomy, traces, failures, tag):
    """Phase 3: each annotator assigns every kept failure one mode, or NONE."""
    a = r.a
    tax_text = dump(slim(taxonomy))
    jobs, keys = [], []
    for k in range(a.annotators):
        for u in r.parts(traces):
            fs = failures.get(ukey(u), []) if failures is not None else stub_failures(8)
            if not fs:
                continue
            jobs.append((f"05c_{tag}_assign_a{k + 1}_{ukey(u)}", "05c_assign",
                         build("05c_assign", taxonomy=tax_text, traces=block([u]),
                               failures=dump([public(f) for f in fs])), a.annotator_temperature))
            keys.append((k, [f["failure_id"] for f in fs]))
    res = r.many(jobs)
    if a.dry_run:
        return None
    labels, missing = [dict() for _ in range(a.annotators)], 0
    for (k, fids), rep in zip(keys, res):
        got, m = label_items(rep, fids)
        labels[k].update(got)
        missing += m
    if missing:
        log(f"  assignment: {missing} labels missing from replies, counted as NONE")
    return labels


def discuss(r: Runner, taxonomy, traces, failures, labels, tag):
    """Phase 4: up to D rounds; on each failure the annotators disagree on, each sees the others'
    labels and reasons and gives a final label."""
    a = r.a
    tax_text = dump(slim(taxonomy))
    parts = r.parts(traces)
    for d in range(1, a.discussion_rounds + 1):
        if a.dry_run:
            disputed = {ukey(u): stub_failures(4) for u in parts}
        else:
            disputed = {ukey(u): [f for f in failures.get(ukey(u), [])
                                  if len({labels[k][f["failure_id"]]["mode"] for k in range(a.annotators)}) > 1]
                        for u in parts}
            n = sum(len(v) for v in disputed.values())
            log(f"  discussion round {d}: {n} failures without a unanimous label")
            if n == 0:
                break
        jobs, keys = [], []
        for k in range(a.annotators):
            for u in parts:
                fs = disputed[ukey(u)]
                if not fs:
                    continue
                items = fs if a.dry_run else [
                    dict(public(f), your_label=labels[k][f["failure_id"]],
                         other_annotators=[labels[j][f["failure_id"]] for j in range(a.annotators) if j != k])
                    for f in fs]
                jobs.append((f"05d_{tag}_discuss{d}_a{k + 1}_{ukey(u)}", "05d_discuss",
                             build("05d_discuss", taxonomy=tax_text, traces=block([u]),
                                   disagreements=dump(items)), a.annotator_temperature))
                keys.append((k, [f["failure_id"] for f in fs]))
        res = r.many(jobs)
        if a.dry_run:
            continue
        for (k, fids), rep in zip(keys, res):
            got = {str(x.get("failure_id")): x for x in (rep or {}).get("labels", [])}
            for fid in fids:
                if fid in got:  # a failure the reply skipped keeps its earlier label
                    labels[k][fid] = {"mode": norm_mode(got[fid].get("mode")), "why": got[fid].get("why")}
    return labels


VALIDATION = {  # the inter-annotation + refinement protocol, run as segment 1 and as the final segment
    "seg1": {"title": "segment 1", "files": "05", "ref_files": "06", "pre": "R", "after": "06_taxonomy_after_seg1.json"},
    "seg3": {"title": "final validation", "files": "09", "ref_files": "10", "pre": "V", "after": "10_taxonomy_after_seg3.json"},
}


def validation(r: Runner, taxonomy, rounds, fa_text, text_by_id, seg="seg1"):
    a, cfg = r.a, VALIDATION[seg]
    for rnd, traces in enumerate(rounds, 1):
        tag, pre = f"{seg}_r{rnd}", f"{cfg['pre']}{rnd}"
        label = rnd if seg == "seg1" else f"final {rnd}"
        log(f"{cfg['title']} round {rnd}: {a.annotators} annotators x {len(traces)} new traces")
        found = discover(r, traces, fa_text, tag)
        failures = reconcile(r, traces, found, tag, pre, text_by_id)
        labels = assign(r, taxonomy, traces, failures, tag)
        before = None
        if not a.dry_run:
            fids = [f["failure_id"] for v in failures.values() for f in v]
            before = agreement(labels, fids, [m["id"] for m in taxonomy])
            labels_before = json.loads(json.dumps(labels))
        labels = discuss(r, taxonomy, traces, failures, labels, tag)

        if a.dry_run:
            agr_text, dis_text, unf_text = "x" * 3000, "x" * 12000, "x" * 8000
            perfect, unf = False, []
        else:
            by_id = {f["failure_id"]: f for v in failures.values() for f in v}
            agr = agreement(labels, fids, [m["id"] for m in taxonomy])
            agr["before_discussion"] = {"kappa": before["kappa"], "coverage": before["coverage"]}
            K = a.annotators
            dis = [dict(public(by_id[f]), trace_id=by_id[f]["trace_id"], labels=[labels[k][f] for k in range(K)])
                   for f in fids if len({labels[k][f]["mode"] for k in range(K)}) > 1]
            unf = [as_instance(by_id[f], f"{pre}U{n}") for n, f in enumerate(
                [f for f in fids if sum(labels[k][f]["mode"] == "NONE" for k in range(K)) * 2 >= K], 1)]
            met = (agr["kappa"] is not None and agr["kappa"] >= a.kappa_target
                   and agr["coverage"] is not None and agr["coverage"] >= a.coverage_target)  # reported only
            perfect = not dis and agr["none_labels"] == 0  # every failure got one mode, the same from everyone
            log(f"  kappa {agr['kappa']} (before discussion {before['kappa']}); coverage {agr['coverage']} "
                f"({agr['none_labels']} of {agr['labels']} labels NONE); {len(dis)} still disputed; "
                f"{len(unf)} failures unfitted; targets {'met' if met else 'missed'}")
            fp = cfg["files"]
            (r.out / vx(f"{fp}_{tag}_findings.json")).write_text(dump(found))
            (r.out / vx(f"{fp}_{tag}_failures.json")).write_text(dump(failures))
            (r.out / vx(f"{fp}_{tag}_labels.json")).write_text(dump({"before_discussion": labels_before, "final": labels}))
            (r.out / vx(f"{fp}_{tag}_agreement.json")).write_text(dump(agr))
            agr_text, dis_text, unf_text = dump(agr), dump(dis), dump(unf)

        if perfect:
            log(f"{cfg['title']} round {rnd}: every failure got the same mode from all annotators, none NONE; nothing to refine")
            continue
        log(f"{cfg['title']} round {rnd}: refinement")
        ref = r.ask(f"06_refinement_r{rnd}" if seg == "seg1" else f"{cfg['ref_files']}_refinement_{tag}", "06_refinement",
                    build("06_refinement", taxonomy=dump(taxonomy), agreement=agr_text,
                          disagreements=dis_text, unfitted=unf_text))
        if not a.dry_run:
            taxonomy, changes = apply_refinement(taxonomy, ref, label, unf)
            log(f"  {len(taxonomy)} modes after refinement; {len(changes)} changes")
            name = f"06_taxonomy_r{rnd}.json" if seg == "seg1" else f"{cfg['ref_files']}_taxonomy_{tag}.json"
            (r.out / vx(name)).write_text(dump({"taxonomy": taxonomy, "changes": changes, "edits": ref}))
    if not a.dry_run:
        (r.out / vx(cfg["after"])).write_text(dump({"taxonomy": taxonomy}))
    return taxonomy


# ---------------------------------------------------------------- segment 2: gap + split

def segment2(r: Runner, taxonomy, traces, text_by_id):
    a = r.a
    log(f"segment 2: gap over {len(traces)} traces")
    taxonomy = json.loads(json.dumps(taxonomy))
    tax_text = dump(with_examples(taxonomy))
    parts = r.parts(traces)
    gaps = r.many([(f"07_gap_{ukey(u)}", "07_gap", build("07_gap", taxonomy=tax_text, traces=block([u])), None)
                   for u in parts])
    proposed, covered = [], []
    if not a.dry_run:
        by_id, n = {m["id"]: m for m in taxonomy}, 0
        for t, g in zip(parts, gaps):
            for x in (g or {}).get("gaps", []):
                n += 1
                pm = x.get("proposed_mode") or {}
                actual = x.get("kind") == "actual"
                mode = norm_mode(x.get("mode"))
                entry = {"instance_id": f"G{n}", "trace_id": t["trace_id"], "quote": x.get("quote"),
                         "missing": None, "what_went_wrong": x.get("what")}
                if mode in by_id:  # an existing mode covers it: an actual failure becomes new evidence for it
                    if actual:
                        by_id[mode]["instances"] = by_id[mode].get("instances", []) + [entry]
                    covered.append(dict(entry, kind=x.get("kind"), mode=mode))
                    continue
                if not pm.get("name"):
                    continue
                proposed.append({"id": f"P-{n:03d}", "name": pm.get("name"), "definition": pm.get("definition"),
                                 "when_to_use": pm.get("when_to_use"), "when_not_to_use": pm.get("when_not_to_use"),
                                 "origin": "observed" if actual else "anticipated",
                                 "closest": x.get("closest"), "why_not": x.get("why_not"),
                                 "instances": [entry] if actual else [],
                                 "possible_at": [] if actual else [{"trace_id": t["trace_id"], "quote": x.get("quote"),
                                                                   "what_could_go_wrong": x.get("what")}]})
        bad = check_quotes([p["instances"][0] for p in proposed if p["instances"]] +
                           [c for c in covered if c["kind"] == "actual"], text_by_id)
        log(f"  {sum(c['kind'] == 'actual' for c in covered)} actual failures fitted existing modes (added as their "
            f"instances); {len(proposed)} new modes proposed ({sum(p['origin'] == 'anticipated' for p in proposed)} "
            f"possible); {bad} quotes not verbatim")
        (r.out / vx("07_gaps.json")).write_text(dump({"proposed": proposed, "covered": covered}))

    log("segment 2: merge proposals into the taxonomy (consolidation prompt)")
    merged = taxonomy + (proposed if not a.dry_run else stub_taxonomy(15))
    co = r.ask("07_gap_consolidation", "04_consolidation", build("04_consolidation", modes=dump(merged)))
    if not a.dry_run:
        taxonomy, changes = apply_edits(merged, co)
        taxonomy, renames = assign_ids(taxonomy)
        taxonomy = rename_refs(taxonomy, resolve(merged_into(changes), renames))
        for m in taxonomy:  # modes the gap step added: backed by an actual instance, or only possible
            if m.get("proposed_as"):
                m["gap"] = "missed" if m.get("instances") else "possible"
        missing, dup = account(taxonomy, [i["instance_id"] for m in merged for i in m.get("instances", [])])
        (r.out / vx("07_taxonomy_after_gap.json")).write_text(dump({"taxonomy": taxonomy, "changes": changes, "edits": co}))
        log(f"  {len(taxonomy)} modes after gap; {len(changes)} edits; {len(missing)} instances lost")

    log(f"segment 2: split check on modes with at least {a.split_min} instances")
    candidates = [m for m in taxonomy if len(m.get("instances", [])) >= a.split_min] if not a.dry_run else stub_taxonomy(8)
    tax_text = dump(slim(taxonomy))
    res = r.many([(f"08_split_{m['id']}", "08_split",
                   build("08_split", taxonomy=tax_text, mode=dump(slim([m])[0]), instances=dump(m.get("instances", []))),
                   None) for m in candidates])
    if a.dry_run:
        return taxonomy
    final, log_split = [], []
    by_cand = dict(zip([c["id"] for c in candidates], res))
    next_id = 1 + max((int(re.sub(r"\D", "", m["id"]) or 0) for m in taxonomy), default=0)
    for m in taxonomy:
        rres = by_cand.get(m["id"])
        insts = {x["instance_id"]: x for x in m.get("instances", [])}
        if rres and rres.get("split") and len(rres.get("parts", [])) >= 2:
            assigned = [i for p in rres["parts"] for i in p.get("instance_ids", [])]
            ok = (all(p.get("instance_ids") for p in rres["parts"])
                  and sorted(assigned) == sorted(insts) and len(set(assigned)) == len(assigned))
            if ok:
                for p in rres["parts"]:
                    final.append({"id": f"FM-{next_id:02d}", "name": p["name"], "definition": p["definition"],
                                  "when_to_use": p["when_to_use"], "when_not_to_use": p["when_not_to_use"],
                                  "origin": "observed", "split_from": m["id"],
                                  **({"gap": m["gap"]} if m.get("gap") else {}),
                                  "instances": [insts[i] for i in p["instance_ids"]], "possible_at": []})
                    next_id += 1
                log_split.append({"mode": m["id"], "split": True, "why": rres.get("why")})
                continue
            log_split.append({"mode": m["id"], "split": False, "why": "split rejected by check: parts overlap, miss instances, or are empty"})
        elif rres:
            log_split.append({"mode": m["id"], "split": False, "why": rres.get("why")})
        final.append(m)
    log(f"  {sum(s['split'] for s in log_split)} of {len(candidates)} examined modes split; {len(final)} modes after split")
    (r.out / vx("08_splits.json")).write_text(dump(log_split))
    (r.out / vx("08_taxonomy_after_split.json")).write_text(dump({"taxonomy": final}))
    return final


# ---------------------------------------------------------------- main

def latest_taxonomy(out: Path, stages):
    """The newest taxonomy written by an earlier stage that is not being run now."""
    order = [("gen", "04_taxonomy_initial.json"), ("seg1", "06_taxonomy_after_seg1.json"),
             ("seg2", "08_taxonomy_after_split.json")]
    for stage, name in reversed(order):
        for cand in dict.fromkeys([vx(name), name]):
            if stage not in stages and (out / cand).exists():
                log(f"loading taxonomy from {cand}")
                return json.loads((out / cand).read_text())["taxonomy"]
    raise SystemExit(f"no earlier taxonomy in {out}; run the earlier stages first")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True,
                    help="dir with sample/ (N traces) and, for the final segment, validation/ (F*M more); one JSON file per trace")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default=None, help='e.g. "arena/gemini-3.8-flash" or "openrouter/google/gemini-2.5-flash"')
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stages", default="gen,seg1,seg2,seg3")
    ap.add_argument("--annotators", type=int, default=4, help="K")
    ap.add_argument("--rounds", type=int, default=1, help="R: segment 1 rounds")
    ap.add_argument("--final-rounds", type=int, default=1, help="F: final validation rounds, on validation/ traces")
    ap.add_argument("--traces-per-round", type=int, default=5, help="M: new traces per segment 1 round")
    ap.add_argument("--discussion-rounds", type=int, default=2, help="D: discussion rounds within a segment 1 round")
    ap.add_argument("--quorum", type=int, default=2, help="Q: annotators who must find a failure for it to be kept")
    ap.add_argument("--kappa-target", type=float, default=0.75, help="reported only; refinement runs unless perfect")
    ap.add_argument("--coverage-target", type=float, default=0.70, help="reported only; refinement runs unless perfect")
    ap.add_argument("--split-min", type=int, default=4, help="S: examine a mode for splitting if it has at least this many instances")
    ap.add_argument("--traces-per-call", type=int, default=1)
    ap.add_argument("--context-tokens", type=int, default=1_000_000, help="the model's context window")
    ap.add_argument("--reserve-chars", type=int, default=200_000,
                    help="room kept in every prompt for everything except the trace; the rest bounds a trace part")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--annotator-temperature", type=float, default=0.7)
    ap.add_argument("--max-output", type=int, default=32768)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--price-in", type=float, default=None, help="USD per million input tokens, for the estimate")
    ap.add_argument("--variant", default="",
                    help="suffix for every file and new reply this run writes (e.g. extra_step -> final_taxonomy_extra_step.json); "
                         "the original run's replies are reused where the prompt is identical, and nothing of it is overwritten")
    ap.add_argument("--answers", type=Path, default=None,
                    help="JSON {trace_id: correct final answer}: every step sees each trace's answer (the answer-provided "
                         "variant); the variant suffix defaults to answer_provided")
    a = ap.parse_args()
    if not a.dry_run and not a.model:
        raise SystemExit("--model is required unless --dry-run")
    global VARIANT
    VARIANT = a.variant or ("answer_provided" if a.answers else "")
    if a.answers:
        use_answers(a.answers)

    sample = [json.loads(p.read_text()) for p in sorted((a.data / "sample").glob("*.json"))]
    held = a.rounds * a.traces_per_round
    if held >= len(sample):
        raise SystemExit(f"R*M = {held} leaves no traces for initial generation out of N = {len(sample)}")
    gen_traces = sample[: len(sample) - held]
    rounds = [sample[len(gen_traces) + i * a.traces_per_round: len(gen_traces) + (i + 1) * a.traces_per_round]
              for i in range(a.rounds)]
    stages = a.stages.split(",")
    held_out = [json.loads(p.read_text()) for p in sorted((a.data / "validation").glob("*.json"))]
    need = a.final_rounds * a.traces_per_round
    if "seg3" in stages and len(held_out) < need:
        raise SystemExit(f"the final segment needs F*M = {need} traces in {a.data / 'validation'}, found {len(held_out)}; "
                         f"add them or leave seg3 out of --stages")
    finals = [held_out[i * a.traces_per_round:(i + 1) * a.traces_per_round] for i in range(a.final_rounds)] \
        if "seg3" in stages else []
    a.prompt_chars = (a.context_tokens - a.max_output) * 3  # about 3 characters per token, on the safe side
    a.trace_budget = a.prompt_chars - a.reserve_chars
    everything = sample + [t for f in finals for t in f]
    if a.answers and any(t["trace_id"] not in ANSWERS for t in everything):
        raise SystemExit(f"{a.answers} has no answer for {[t['trace_id'] for t in everything if t['trace_id'] not in ANSWERS]}")
    text_by_id = {t["trace_id"]: render(t) for t in everything}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / vx("config.json")).write_text(dump({k: str(v) for k, v in vars(a).items()}))
    (a.out / vx("allocation.json")).write_text(dump({"initial_generation": [t["trace_id"] for t in gen_traces],
                                                 **{f"segment1_round{i + 1}": [t["trace_id"] for t in rt]
                                                    for i, rt in enumerate(rounds)},
                                                 "segment2": [t["trace_id"] for t in sample],
                                                 **{f"final_round{i + 1}": [t["trace_id"] for t in f]
                                                    for i, f in enumerate(finals)}}))
    log(f"N = {len(sample)} traces from {a.data}: {len(gen_traces)} for initial generation, "
        f"{a.rounds} x {a.traces_per_round} for segment 1, all {len(sample)} for segment 2; "
        f"{len(finals)} x {a.traces_per_round} unseen traces for the final validation; "
        f"model {a.model}; {'DRY RUN' if a.dry_run else 'LIVE'}")

    r = Runner(a)
    r.units = {t["trace_id"]: split_trace(t, a.trace_budget) for t in everything}
    split = {tid: len(v) for tid, v in r.units.items() if len(v) > 1}
    if split:
        log(f"{len(split)} traces too long for one call are split into parts: {split}")
    if "gen" in stages:
        tax, fa_text = initial_generation(r, gen_traces, text_by_id)
    else:
        tax = latest_taxonomy(a.out, stages)
        fa_file = next((a.out / c for c in dict.fromkeys([vx("01_field_analysis.json"), "01_field_analysis.json"])
                        if (a.out / c).exists()), None)
        fa_text = fa_file.read_text() if fa_file else dump({"field": "x" * 3000})
    if "seg1" in stages:
        tax = validation(r, tax, rounds, fa_text, text_by_id, "seg1")
    if "seg2" in stages:
        tax = segment2(r, tax, sample, text_by_id)
    if "seg3" in stages:
        tax = validation(r, tax, finals, fa_text, text_by_id, "seg3")
    if not a.dry_run:
        (a.out / vx("final_taxonomy.json")).write_text(dump(tax))
        evidence = [m for m in tax if m.get("gap") != "possible"]  # the same taxonomy without possible-only modes
        (a.out / vx("final_taxonomy_evidence.json")).write_text(dump(evidence))
        log(f"final taxonomy: {len(tax)} modes -> {a.out / vx('final_taxonomy.json')}")

    total = sum(s["input_tokens_est"] for s in r.stats.values())
    lines = [f"{'stage':20s} {'calls':>6s} {'input tokens (est.)':>20s}"]
    for st, s in sorted(r.stats.items()):
        lines.append(f"{st:20s} {s['calls']:6d} {s['input_tokens_est']:20,d}")
    lines.append(f"{'TOTAL':20s} {sum(s['calls'] for s in r.stats.values()):6d} {total:20,d}")
    if a.dry_run:
        lines.append("(discussion and refinement counted at their maximum)")
    if a.price_in:
        lines.append(f"input cost at ${a.price_in}/M tokens: ${total / 1e6 * a.price_in:,.2f} (output tokens not included)")
    report = "\n".join(lines)
    (a.out / vx("dry_run_estimate.txt" if a.dry_run else "usage_estimate.txt")).write_text(report + "\n")
    print(report)
    if not a.dry_run:
        from call_report import billed, report as call_report
        text = call_report(a.out, VARIANT)
        (a.out / vx("call_report.txt")).write_text(text + "\n")
        (a.out / vx("cost.json")).write_text(dump(billed(a.out, VARIANT)))
        print(text)


if __name__ == "__main__":
    main()
