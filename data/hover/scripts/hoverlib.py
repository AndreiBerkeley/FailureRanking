"""Shared helpers for the data/hover migration and audit scripts.

Everything here is standard library. The HoVer metric is re-implemented so
outcomes can be re-derived and checked against recorded gold without dspy.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import shutil
import string
import unicodedata
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OLD = REPO / "benchmarks" / "hover"
NEW = REPO / "data" / "hover"
TODAY = "2026-09-06"

# Keys that must never appear in a trace body or a judge record.
GOLD_KEY_PATTERNS = ("gold", "supporting", "required_titles")
GOLD_KEY_EXACT = {"label"}


# ----------------------------------------------------------------- io ---- #
def log(msg: str) -> None:
    print(msg, flush=True)


def jload(p: Path):
    with open(p) as f:
        return json.load(f)


def jdump(obj, p: Path, indent: int | None = 2) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, indent=indent, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def jsonl_write(rows, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")


def jsonl_read(p: Path):
    with open(p) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source_fingerprint(paths: list[Path]) -> str:
    """One sha256 over a set of source files, in sorted path order."""
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(str(p.relative_to(REPO)).encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


# ---------------------------------------------------------- identities --- #
def component_sha256(components: dict) -> str:
    # Exactly the recipe run_eval_v3.py used, so ids verify against the
    # captures' candidate maps.
    return sha256_bytes(json.dumps(components, sort_keys=True).encode("utf-8"))


def candidate_id_from(components: dict) -> str:
    return "cnd-" + component_sha256(components)[:12]


def load_registry() -> tuple[dict, dict]:
    """-> (by_id, by_alias) over data/hover/candidates/registry.jsonl."""
    by_id = {r["candidate_id"]: r for r in jsonl_read(NEW / "candidates" / "registry.jsonl")}
    by_alias = {r["alias"]: r for r in by_id.values()}
    return by_id, by_alias


def capture_index_to_id(cmap: dict, by_alias: dict) -> dict[int, str]:
    """A source capture's candidate_map -> {candidate_index: candidate_id}, hash-verified."""
    out = {}
    for e in cmap["candidates"]:
        row = by_alias[e["pool_candidate_id"]]
        assert row["component_sha256"] == e["component_sha256"], f"hash mismatch for {e['pool_candidate_id']}"
        out[int(e["candidate_index"])] = row["candidate_id"]
    return out


# --------------------------------------------------------------- gold ---- #
def normalize_text(s: str) -> str:
    # dspy.evaluate.metrics.normalize_text, reproduced step for step.
    s = unicodedata.normalize("NFD", s)
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def hover_score(retrieved_docs: list, gold_titles: list) -> float:
    found = {normalize_text(str(d).split(" | ", 1)[0]) for d in retrieved_docs}
    gold = {normalize_text(t) for t in gold_titles}
    return float(not (gold - found))


def scan_gold_keys(obj, path: str = "") -> list[str]:
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in GOLD_KEY_EXACT or any(p in kl for p in GOLD_KEY_PATTERNS):
                hits.append(f"{path}/{k}")
            hits.extend(scan_gold_keys(v, f"{path}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(scan_gold_keys(v, f"{path}[{i}]"))
    return hits


# ----------------------------------------------------------- provenance -- #
def provenance(pid: str, kind: str, derives_from: list[str], counts: dict, checks: dict,
               script: str, extra: dict | None = None) -> dict:
    d = {
        "id": pid,
        "kind": kind,
        "benchmark": "hover",
        "created": TODAY,
        "derives_from": derives_from,
        "produced_by": {"script": script, "command": "python3 " + script},
        "counts": counts,
        "checks": checks,
    }
    if extra:
        d.update(extra)
    return d


# ------------------------------------------------------- split records --- #
def split2_records() -> dict:
    """source_id -> {label, source_index, claim_sha256, split2_portion} over all of split-2."""
    s2 = jload(OLD / "splits" / "split-2" / "split.json")
    rec = {}
    for portion, rows in s2["records"].items():
        for r in rows:
            rec[r["source_id"]] = {"label": r["label"], "source_index": r["source_index"],
                                   "claim_sha256": r["claim_sha256"], "split2_portion": portion}
    return rec


# --------------------------------------------------------- captures ------ #
def migrate_capture(*, src: Path, capture_id: str, split_id: str, portions: list[str],
                    allowed_tasks: set, rec: dict, by_alias: dict, expected_tasks: int,
                    captured_on: str, derives_from: list[str], script: str,
                    description: str, runner_prov: dict | None = None, candidate_set: str = "pool-3",
                    solver_model: str = "gemini/gemini-3.1-flash-lite") -> dict:
    """Duplicate one source capture (a traces-3 portion directory) into
    data/hover/traces/<capture_id>, re-keyed to registry ids and verified.

    Returns claims, gold, index rows and outcome rows for the caller to fold
    into the task registry and the outcomes directory.
    """
    cmap = jload(src / "candidate_map.json")
    idx_to_cid = capture_index_to_id(cmap, by_alias)
    alias_of = {int(e["candidate_index"]): e["pool_candidate_id"] for e in cmap["candidates"]}
    old_outcomes = jload(src / "outcomes.json")["outcomes"]

    gold_by_task: dict[str, list[str]] = {}
    gold_score_by_trace: dict[str, float] = {}
    for f in (src / "raw" / "evaluation" / "gold_do_not_pass_to_judge").rglob("*.json"):
        g = jload(f)
        tid = g["task"]["source_id"]
        titles = sorted(g["gold_supporting_titles"])
        if tid in gold_by_task:
            assert gold_by_task[tid] == titles, f"gold differs across candidates for task {tid}"
        else:
            gold_by_task[tid] = titles
        gold_score_by_trace[g["trace_id"]] = float(g["gold_score"])
    assert set(gold_by_task) == allowed_tasks, f"{capture_id}: gold tasks != split portion tasks"

    cap = NEW / "traces" / capture_id
    bodies_dir, states_dir = cap / "bodies", cap / "program_states"
    bodies_dir.mkdir(parents=True)
    states_dir.mkdir(parents=True)

    claims: dict[str, str] = {}
    index_rows, outcome_rows, bodies_meta = [], [], {}
    status_counter: Counter = Counter()
    repeats = set()
    seen = set()
    gold_hits, mismatch = [], []

    for cidx in sorted(idx_to_cid):
        cid = idx_to_cid[cidx]
        rows = []
        for rf in sorted((src / "raw" / "evaluation" / "traces" / f"candidate_{cidx:03d}").glob("*.json")):
            raw = jload(rf)
            tid, rep, trace_id = raw["task"]["source_id"], int(raw["evaluation_repeat"]), raw["trace_id"]
            assert raw["candidate_index"] == cidx
            assert raw["candidate_component_sha256"] == by_alias[alias_of[cidx]]["component_sha256"]
            assert tid in allowed_tasks, f"{trace_id}: task outside the split portions"
            claim = raw["input"]["claim"]
            assert sha256_bytes(claim.encode("utf-8")) == raw["task"]["claim_sha256"] == rec[tid]["claim_sha256"]
            assert raw["task"]["source_index"] == rec[tid]["source_index"]
            claims.setdefault(tid, claim)
            assert claims[tid] == claim
            key = (cid, tid, rep)
            assert key not in seen, f"duplicate {key}"
            seen.add(key)
            repeats.add(rep)

            corpus = jload(src / "corpus" / f"{trace_id}.json")
            assert corpus["trace_id"] == trace_id and corpus["metadata"]["task_source_id"] == tid
            assert corpus["metadata"]["candidate_index"] == cidx

            models = sorted({c["model"] for c in raw["lm_calls"]})
            cost = float(sum(float(c.get("cost") or 0.0) for c in raw["lm_calls"]))
            body = {
                "trace_id": trace_id, "benchmark": "hover", "capture": capture_id,
                "candidate_id": cid, "task_id": tid, "repeat": rep, "status": raw["status"],
                "solver": {"models": models, "n_lm_calls": len(raw["lm_calls"]), "cost_usd": cost},
                "task_ref": {"claim_sha256": raw["task"]["claim_sha256"], "source_index": raw["task"]["source_index"]},
                "input": raw["input"], "prediction": raw["prediction"], "lm_calls": raw["lm_calls"],
                "judge_view": {"messages": corpus["messages"], "metadata": corpus["metadata"]},
                "legacy": {"candidate_index": cidx, "pool_alias": alias_of[cidx],
                           "source": str(src.relative_to(REPO))},
            }
            if scan_gold_keys(body):
                gold_hits.append(trace_id)
            status_counter[raw["status"]] += 1
            score = hover_score(raw["prediction"]["retrieved_docs"], gold_by_task[tid])
            if not (score == gold_score_by_trace[trace_id] == float(old_outcomes[alias_of[cidx]][str(rep)][tid])):
                mismatch.append(trace_id)
            outcome_rows.append({"candidate_id": cid, "task_id": tid, "repeat": rep, "trace_id": trace_id,
                                 "score": score, "capture": capture_id})
            rows.append(body)

        rows.sort(key=lambda b: (b["task_id"], b["repeat"]))
        assert len(rows) == expected_tasks * len(repeats), f"{capture_id} {cid}: {len(rows)} traces"
        out = bodies_dir / f"{cid}.jsonl.gz"
        with gzip.open(out, "wt", compresslevel=6, encoding="utf-8") as f:
            for b in rows:
                line = json.dumps(b, sort_keys=True, ensure_ascii=False)
                f.write(line + "\n")
                index_rows.append({"trace_id": b["trace_id"], "candidate_id": cid, "task_id": b["task_id"],
                                   "repeat": b["repeat"], "status": b["status"],
                                   "n_lm_calls": b["solver"]["n_lm_calls"], "cost_usd": b["solver"]["cost_usd"],
                                   "body_sha256": sha256_bytes(line.encode("utf-8"))})
        bodies_meta[cid] = {"file": f"bodies/{cid}.jsonl.gz", "rows": len(rows), "sha256": sha256_file(out)}
        shutil.copyfile(src / "raw" / "candidate_states" / f"cand_{cidx:03d}.json", states_dir / f"{cid}.json")
        log(f"  {capture_id} {cid} ({alias_of[cidx]}): {len(rows)} traces")

    assert not gold_hits, f"{capture_id}: gold-bearing keys in {len(gold_hits)} bodies"
    assert not mismatch, f"{capture_id}: re-score disagrees with recorded gold on {len(mismatch)} traces"
    expected = len(idx_to_cid) * expected_tasks * len(repeats)
    assert len(index_rows) == expected
    index_rows.sort(key=lambda r: (r["candidate_id"], r["task_id"], r["repeat"]))
    jsonl_write(index_rows, cap / "index.jsonl")

    src_prov = {"produced_by": runner_prov} if runner_prov is not None else jload(src.parent / "provenance.json")
    audits = {
        "raw_corpus_one_to_one": True, "candidate_task_repeat_unique": True, "tasks_within_split": True,
        "claim_sha256_matches_registry": True, "component_sha256_matches_registry": True,
        "no_gold_keys_in_bodies": True, "rescored_equals_recorded_gold": True,
    }
    manifest = {
        "capture_id": capture_id, "benchmark": "hover", "description": description,
        "candidate_set": candidate_set, "candidate_ids": sorted(idx_to_cid.values()),
        "split": split_id, "portions": portions, "task_count": expected_tasks, "repeats": sorted(repeats),
        "solver": {"model": solver_model, "max_tokens": 8192},
        "program": "HoverMultiHop (4 components), dspy 3.3.0",
        "runner": src_prov["produced_by"], "captured_on": captured_on,
        "expected_traces": expected, "present_traces": len(index_rows),
        "status_counts": dict(status_counter), "bodies": bodies_meta,
        "body_format": "one gzip JSONL per candidate; one trace per line; index.jsonl carries the sha256 of each line",
        "judge_view": "field judge_view holds the outcome-blind message list exactly as emitted for judging in the source capture",
        "audits": audits, "derives_from": derives_from,
    }
    jdump(manifest, cap / "manifest.json")
    jdump(provenance(capture_id, "trace capture", derives_from,
                     {"traces": len(index_rows), "candidates": len(idx_to_cid), "tasks": expected_tasks,
                      "repeats": len(repeats)}, audits, script), cap / "provenance.json")
    outcome_rows.sort(key=lambda r: (r["candidate_id"], r["task_id"], r["repeat"]))
    return {"claims": claims, "gold_by_task": gold_by_task, "index_rows": index_rows,
            "outcome_rows": outcome_rows, "status_counter": status_counter, "manifest": manifest}


def write_capture_readme(capture_id: str, title: str, body: str) -> None:
    (NEW / "traces" / capture_id / "README.md").write_text(f"# {capture_id} — {title}\n\n{body}")


def write_outcomes(capture_id: str, outcome_rows: list, derives_from: list[str], script: str) -> None:
    jsonl_write(outcome_rows, NEW / "outcomes" / f"{capture_id}.jsonl")
    per = {}
    for r in outcome_rows:
        per.setdefault(r["candidate_id"], []).append(r["score"])
    jdump(provenance(f"outcomes/{capture_id}", "gold outcomes", derives_from,
                     {"records": len(outcome_rows),
                      "mean_score_by_candidate": {c: round(sum(v) / len(v), 4) for c, v in sorted(per.items())}},
                     {"rescored_from_registry_gold_and_trace_predictions": True,
                      "equals_recorded_gold_score_on_every_trace": True,
                      "equals_source_outcomes_json_on_every_trace": True},
                     script,
                     {"scorer": "hover_retrieval_metric, re-implemented in data/hover/scripts/hoverlib.py: "
                                "score 1 iff every gold title, after dspy normalize_text, is among the titles of prediction.retrieved_docs"}),
          NEW / "outcomes" / f"{capture_id}.provenance.json")


def write_outcomes_readme() -> None:
    rows = []
    for p in sorted((NEW / "outcomes").glob("cap-*.jsonl")):
        n = sum(1 for _ in open(p))
        rows.append(f"| `{p.stem}` | {n} | HoVer retrieval metric: 1 iff all three gold titles retrieved |")
    (NEW / "outcomes" / "README.md").write_text("""# outcomes — gold scores per trace

One file per capture, one row per trace: `candidate_id`, `task_id`, `repeat`,
`trace_id`, `score`. Derived by a scorer that reads the task registry's gold and
the trace's prediction; nothing here is copied from the source tree, and the
re-derived scores were checked equal to the recorded ones for every trace. Each
file has a `<capture>.provenance.json` beside it.

Gold-bearing by construction. Any scoring path that claims to be free of gold
must not read this directory.

| capture | records | scorer |
|---|---:|---|
""" + "\n".join(rows) + "\n")


def write_tasks(claims: dict, gold_by_task: dict, rec: dict, portions_of: dict, script: str,
                derives_from: list[str]) -> int:
    """Rewrite the task registry as the union of what is passed in and what is
    already there. Existing rows must be identical to what would be written."""
    existing = {r["task_id"]: r for r in jsonl_read(NEW / "tasks" / "tasks.jsonl")} if (NEW / "tasks" / "tasks.jsonl").exists() else {}
    rows = {}
    for tid in claims:
        rows[tid] = {
            "task_id": tid, "benchmark": "hover", "claim": claims[tid], "label": rec[tid]["label"],
            "gold": {"supporting_titles": gold_by_task[tid]},
            "source": {"dataset": "hover-nlp/hover", "dataset_split": "train",
                       "source_index": rec[tid]["source_index"], "claim_sha256": rec[tid]["claim_sha256"],
                       "filter": "exactly three distinct supporting titles"},
            "splits": portions_of.get(tid, []),
        }
    for tid, old in existing.items():
        if tid in rows:
            o = dict(old); o.pop("splits", None)
            n = dict(rows[tid]); n.pop("splits", None)
            assert o == n, f"task {tid} would change on rewrite"
            rows[tid]["splits"] = sorted(set(old.get("splits", [])) | set(rows[tid]["splits"]))
        else:
            rows[tid] = old
    out = [rows[t] for t in sorted(rows)]
    jsonl_write(out, NEW / "tasks" / "tasks.jsonl")
    jdump(provenance("tasks", "task registry", derives_from,
                     {"tasks": len(out), "labels": dict(Counter(r["label"] for r in out))},
                     {"claim_sha256_verified_against_split_records": True,
                      "gold_consistent_across_candidates": True,
                      "existing_rows_unchanged_on_growth": True},
                     script,
                     {"note": "holds every task any stored capture references; grows as captures are added"}),
          NEW / "tasks" / "provenance.json")
    return len(out)


def write_tasks_readme() -> None:
    rows = list(jsonl_read(NEW / "tasks" / "tasks.jsonl"))
    tags = Counter(t for r in rows for t in r.get("splits", []))
    lines = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(tags.items()))
    (NEW / "tasks" / "README.md").write_text(f"""# tasks — the HoVer task registry

One row per task. Gold-bearing: this is the only place gold lives.

| field | meaning |
|---|---|
| `task_id` | the source dataset's uid; the identity every other file uses |
| `claim` | the claim to verify |
| `label` | the dataset's supported / not-supported label (1 / 0) |
| `gold.supporting_titles` | the three Wikipedia titles a run must retrieve to score 1 |
| `source` | dataset, split, row index, and the claim's sha256 |
| `splits` | which split portions the task belongs to, as `split/portion` |

Currently {len(rows)} tasks. The registry holds every task any stored capture
references; it grows as captures are added and never shrinks. A task's row
never changes once written; only its `splits` list can gain entries.

| split / portion | tasks |
|---|---:|
{lines}
""")
