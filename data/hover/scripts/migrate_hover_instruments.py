#!/usr/bin/env python3
"""Duplicate the instrument outputs for HoVer into data/hover: the program
structure both instruments read, the two taxonomies with the runs that made
them, and the judge's mappings of those taxonomies onto captures cap-2 and
cap-3. Read-only on runs/ and results/. Refuses to overwrite.

Requires the captures (cap-1..3) to exist: every trace a taxonomy or mapping
refers to is checked against a capture index by id.
"""
from __future__ import annotations

import datetime
import gzip
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

from hoverlib import (NEW, REPO, TODAY, jdump, jload, jsonl_read, jsonl_write, load_registry, log, provenance,
                      scan_gold_keys, sha256_bytes, sha256_file, source_fingerprint, capture_index_to_id)

SCRIPT = "data/hover/scripts/migrate_hover_instruments.py"
RUNS = REPO / "runs" / "taxgen-v4"
RES = REPO / "results" / "hover"
STRUCTURE_SRC = REPO / "runs" / "taxgen-v2" / "structures" / "hover.json"
SAMPLES = REPO / "benchmarks" / "hover" / "traces" / "traces-3" / "generation" / "samples"
SAMPLE1 = SAMPLES / "sample-1" / "trace_ids.txt"   # the fixed sample the generator read
SAMPLE2 = SAMPLES / "sample-2" / "trace_ids.txt"   # the fresh sample the gap test read

TAXONOMIES = {
    "tax-7": RUNS / "hover" / "taxonomy_v2.json",
    "tax-18": RUNS / "hover-granularity" / "taxonomy_split18.json",
}
MAPPINGS = [  # map id, taxonomy, judge run dir, capture, split portion
    ("map-1", "tax-7", "judge-tax2-judging", "cap-2", "sample"),
    ("map-2", "tax-7", "judge-tax2-generalization", "cap-3", "domain"),
    ("map-3", "tax-18", "judge-tax18-judging", "cap-2", "sample"),
    ("map-4", "tax-18", "judge-tax18-generalization", "cap-3", "domain"),
]
HEX24 = re.compile(r"\b[0-9a-f]{24}\b")

JUDGE_SOURCES = [REPO / "pipeline" / "measure" / "run.py", REPO / "pipeline" / "measure" / "judge.py",
                 REPO / "pipeline" / "taxonomy2" / "render.py", REPO / "pipeline" / "goldfree.py"]
GENERATOR_SOURCES = sorted((REPO / "pipeline" / "taxonomy2").glob("*.py")) + [REPO / "pipeline" / "goldfree.py",
                                                                             REPO / "pipeline" / "taxonomy" / "stages.py"]


def capture_index(cap: str) -> dict[str, dict]:
    return {r["trace_id"]: r for r in jsonl_read(NEW / "traces" / cap / "index.jsonl")}


def ids_in(obj) -> set[str]:
    return set(HEX24.findall(json.dumps(obj)))


def first_sentence(s: str) -> str:
    s = " ".join(s.split())
    m = re.match(r"(.+?\.)(\s|$)", s)
    return (m.group(1) if m else s)[:220]


def main() -> None:
    for d in ("program", "taxonomies", "mappings"):
        if (NEW / d).exists():
            sys.exit(f"data/hover/{d} already exists; artifacts are append-only")
    _, by_alias = load_registry()
    cap1 = capture_index("cap-1")
    gen_fp = source_fingerprint(GENERATOR_SOURCES)
    judge_fp = source_fingerprint(JUDGE_SOURCES)
    instruments = {
        "taxonomy_generator": {"name": "taxonomy generator", "module": "pipeline/taxonomy2", "version": "v2 (generation only)",
                               "source_fingerprint_sha256": gen_fp},
        "judge": {"name": "measurement judge", "module": "pipeline/measure", "version": "v1, per-turn accounting (2026-09-02)",
                  "source_fingerprint_sha256": judge_fp},
    }

    # ---------------- program ----------------
    log("program")
    prog = NEW / "program"
    prog.mkdir(parents=True)
    shutil.copyfile(STRUCTURE_SRC, prog / "structure.json")
    st = jload(prog / "structure.json")
    jdump(provenance("program", "program structure", ["runs/taxgen-v2/structures/hover.json"],
                     {"agents": len(st.get("architecture", {}).get("agents", [])) if isinstance(st.get("architecture"), dict) else None},
                     {"copied_verbatim": True}, SCRIPT), prog / "provenance.json")
    (prog / "README.md").write_text("""# program — the HoVer program every candidate runs

All 40 candidates are the same program with different instructions. The
program is a four-module pipeline: it summarises the passages retrieved for the
claim, writes a query for the second hop, summarises again, and writes a query
for the third hop. Three retrievals happen between the modules and are performed
by the harness, not by the model. The final output is the set of everything
retrieved.

| module | what it does |
|---|---|
| `summarize1` | reads the claim and the first-hop passages, writes a summary |
| `create_query_hop2` | reads the claim and that summary, writes the second-hop search query |
| `summarize2` | reads the claim, the earlier context and the second-hop passages, writes a summary |
| `create_query_hop3` | reads everything so far, writes the third-hop search query |

A candidate is the four instruction texts for these modules (see
`../candidates/`). A trace of one run shows each module as a turn: the
instructions it had, what it received, and what it produced.

`structure.json` is the machine-readable description of this: the trace
format, the markers that separate turns, and the modules and their roles. Both
instruments read it, the taxonomy generator to know which agent each failure
belongs to and the judge to render a trace as turns. Copied verbatim from
`runs/taxgen-v2/structures/hover.json`.
""")

    # ---------------- taxonomies ----------------
    log("taxonomies")
    tax_dir = NEW / "taxonomies"
    tax_meta = {}
    for tid, src in TAXONOMIES.items():
        d = tax_dir / tid
        d.mkdir(parents=True)
        shutil.copyfile(src, d / "taxonomy.json")
        t = jload(src)
        codes = t["codes"]
        used = ids_in(t)
        in_cap1 = used & set(cap1)
        sample_ids = [l.strip() for l in SAMPLE1.read_text().splitlines() if l.strip()] if tid == "tax-7" else []
        sample_in_cap1 = [i for i in sample_ids if i in cap1]
        sample_tasks = {cap1[i]["task_id"] for i in sample_in_cap1}
        tax_meta[tid] = {"codes": [c["id"] for c in codes], "sha256": sha256_file(d / "taxonomy.json"),
                         "n_codes": len(codes)}
        rows = []
        for c in codes:
            extra = f" | {c.get('split_from', '')}" if tid == "tax-18" else ""
            rows.append(f"| `{c['id']}` | {c['column']} | {c['name']} | {first_sentence(c['definition'])}{extra} |")
        head = "| id | column | name | definition" + (" | split from (tax-7 code) |" if tid == "tax-18" else " |")
        sep = "|---|---|---|---|" + ("---|" if tid == "tax-18" else "")
        if tid == "tax-7":
            desc = f"""Seven failure modes induced from the traces of `cap-1` by the taxonomy
generator, with no result of any run in view. A *column* says where in the
program the mistake belongs: `general` failures can occur in any module,
`domain` failures are specific to what this program does. Every code names an
action of the candidate, not a topic of the task.

The generator read a fixed sample of {len(sample_ids)} traces from `cap-1`, drawn
task-first so that the vocabulary is bounded by task diversity rather than by
trace count: {len(sample_tasks)} distinct tasks, all {len(sample_in_cap1)} traces
verified present in `cap-1` by id; the list is
`../runs/taxgen-1/induction_sample_trace_ids.txt`. Its stage outputs, prompts,
raw responses and log are in `../runs/taxgen-1/`."""
            derives = ["data/hover/traces/cap-1", "runs/taxgen-v4/hover"]
            checks = {"copied_verbatim": True, "referenced_traces_in_cap1": len(in_cap1) == len(used),
                      "induction_sample_in_cap1": len(sample_in_cap1) == len(sample_ids) == 300}
            extra_prov = {"instrument": instruments["taxonomy_generator"], "framework": t.get("framework"),
                          "produced_by": t.get("produced_by"), "observations": t.get("observations"),
                          "referenced_trace_ids": sorted(used),
                          "induction_sample": {"file": "runs/taxgen-1/induction_sample_trace_ids.txt", "traces": len(sample_ids),
                                               "tasks": len(sample_tasks), "trace_ids": sample_ids},
                          "structure": "data/hover/program/structure.json"}
        else:
            df = t["derives_from"]
            cnt = t["counts"]
            desc = f"""Eighteen failure modes obtained by splitting `tax-7`. Five of its seven codes
were found to carry more than one mechanism and were split into parts; two were
kept whole. A split was accepted only when its parts occur independently in the
data: if every trace showing one part also showed the others, they were one
mechanism described several ways and the split was refused. Parts keep their
parent's column. The ids are a fresh namespace (`SP_`) so a result under this
taxonomy can never be silently compared with one under `tax-7`.

Counts: {cnt['parent_codes']} parent codes, {cnt['split']} split, {cnt['kept']} kept, {cnt['codes']} codes.
The gap test that supplied the records is in `../runs/taxgen-2/`, the split
decisions in `../runs/taxgen-3/`."""
            derives = ["data/hover/taxonomies/tax-7", "runs/taxgen-v4/hover-gaps", "runs/taxgen-v4/hover-granularity"]
            checks = {"copied_verbatim": True, "every_code_has_a_parent_in_tax7": all(
                (c.get("split_from") or c.get("name")) for c in codes)}
            extra_prov = {"instrument": instruments["taxonomy_generator"], "produced_by": t.get("produced_by"),
                          "derives_from_detail": df, "counts": cnt, "structure": "data/hover/program/structure.json"}
        (d / "README.md").write_text(f"""# {tid} — {len(codes)} failure modes for the HoVer program

{desc}

{head}
{sep}
""" + "\n".join(rows) + f"""

`taxonomy.json` is the file the judge is pointed at, copied verbatim. Each code
carries a full definition, when to use it, when not to, and the evidence it
rests on.
""")
        jdump(provenance(tid, "taxonomy", derives, {"codes": len(codes)}, checks, SCRIPT, extra_prov),
              d / "provenance.json")

    # taxonomy runs
    runs_dir = tax_dir / "runs"
    (runs_dir / "taxgen-1").mkdir(parents=True)
    for p in (RUNS / "hover").iterdir():
        if p.is_file():
            shutil.copyfile(p, runs_dir / "taxgen-1" / p.name)
    shutil.copyfile(SAMPLE1, runs_dir / "taxgen-1" / "induction_sample_trace_ids.txt")
    gaps_dst = runs_dir / "taxgen-2"
    gaps_dst.mkdir()
    fresh_ids = sorted(p.stem for p in (RUNS / "hover-gaps" / "fresh_corpus").glob("*.json"))
    for p in (RUNS / "hover-gaps").iterdir():
        if p.is_file():
            shutil.copyfile(p, gaps_dst / p.name)
    fresh_in_cap1 = [i for i in fresh_ids if i in cap1]
    sample2 = [l.strip() for l in SAMPLE2.read_text().splitlines() if l.strip()]
    assert set(sample2) <= set(fresh_ids), "gap test sample-2 not drawn from its fresh corpus"
    assert all(i in cap1 for i in sample2) and len(sample2) == 300
    shutil.copyfile(SAMPLE2, gaps_dst / "fresh_sample_trace_ids.txt")
    jdump({"note": "the gap test's fresh corpus was a copy of these cap-1 traces (every trace on the tasks the "
                   "generator had not read); the copies are not duplicated here. The 300 traces the gap test "
                   "actually read are fresh_sample_trace_ids.txt, drawn from this pool.",
           "trace_ids": fresh_ids, "count": len(fresh_ids), "in_cap1": len(fresh_in_cap1)},
          gaps_dst / "fresh_corpus_trace_ids.json")
    gran_dst = runs_dir / "taxgen-3"
    shutil.copytree(RUNS / "hover-granularity", gran_dst)
    (runs_dir / "README.md").write_text(f"""# runs — the instrument runs that produced the taxonomies

| run | what it did | produced |
|---|---|---|
| `taxgen-1` | generation: six model calls over cap-1 traces with outcomes stripped, from domain analysis to rule validation; every stage's prompt and raw response is kept | `../tax-7` |
| `taxgen-2` | gap test: from a pool of {len(fresh_ids)} cap-1 traces on tasks the generator had not read, observed a fixed sample of 300 without the taxonomy in view, then asked which observations `tax-7` could express; the records it produced are what the split step was verified on | records for `taxgen-3` |
| `taxgen-3` | granularity: proposed splits of `tax-7` codes that carry several mechanisms and accepted only those whose parts occur independently in the records | `../tax-18` |

Each directory is a verbatim copy of the run as it was left, except that
`taxgen-2`'s copy of its input traces is replaced by the list of their ids
(`fresh_corpus_trace_ids.json`); the traces themselves are in `../../traces/cap-1`.
Source locations: `runs/taxgen-v4/hover`, `hover-gaps`, `hover-granularity`.
""")
    for rid, src, out in (("taxgen-1", "runs/taxgen-v4/hover", "tax-7"),
                          ("taxgen-2", "runs/taxgen-v4/hover-gaps", "records for taxgen-3"),
                          ("taxgen-3", "runs/taxgen-v4/hover-granularity", "tax-18")):
        jdump(provenance(rid, "taxonomy generator run", [src] + (["data/hover/traces/cap-1"] if rid != "taxgen-3" else ["data/hover/taxonomies/runs/taxgen-2"]),
                         {"fresh_pool_traces": len(fresh_ids), "fresh_sample_traces": 300} if rid == "taxgen-2" else {},
                         {"copied_verbatim": True, **({"fresh_traces_in_cap1": len(fresh_in_cap1) == len(fresh_ids)} if rid == "taxgen-2" else {})},
                         SCRIPT, {"instrument": instruments["taxonomy_generator"], "produced": out}),
              runs_dir / rid / "provenance.json")
    (tax_dir / "README.md").write_text(f"""# taxonomies — failure-mode vocabularies for the HoVer program

A taxonomy is a list of failure codes, each with a definition and the evidence
it rests on. It is what the judge holds when it reads a trace. Both taxonomies
here were induced from traces in `cap-1` with no run outcome in view.

| taxonomy | codes | how it was made |
|---|---:|---|
| [`tax-7`](tax-7/README.md) | 7 | generated from cap-1 traces by the taxonomy generator |
| [`tax-18`](tax-18/README.md) | 18 | tax-7 with five codes split into parts that occur independently in the data |

The same failure points in a trace, grouped two ways. `runs/` holds the three
instrument runs that produced them.
""")

    # ---------------- mappings ----------------
    log("mappings")
    map_dir = NEW / "mappings"
    table = []
    for mid, tid, run, cap, portion in MAPPINGS:
        src = RES / run
        summary = jload(src / "summary.json")
        settings = summary["settings"]
        idx = capture_index(cap)
        cmap = jload(REPO / "benchmarks" / "hover" / "traces" / "traces-3" / ("judging" if cap == "cap-2" else "generalization") / "candidate_map.json")
        idx_to_cid = capture_index_to_id(cmap, by_alias)
        codes_allowed = set(tax_meta[tid]["codes"])
        d = map_dir / mid
        (d / "judge_records").mkdir(parents=True)
        rows_by_cand: dict[str, list] = {}
        mapping_rows = []
        status = Counter()
        firing = Counter()
        bad_codes = set()
        gold_hits = 0
        for f in sorted((src / "traces").glob("*.json")):
            t = jload(f)
            trace_id = t["trace_id"]
            assert trace_id in idx, f"{mid}: judged trace {trace_id} not in {cap}"
            r = idx[trace_id]
            cid = idx_to_cid[int(t["candidate_index"])]
            assert r["candidate_id"] == cid and r["task_id"] == t["task_id"], f"{mid}: identity mismatch on {trace_id}"
            assert t.get("gold_stripped") == [], f"{mid}: judge stripped gold from {trace_id}"
            body = {k: v for k, v in t.items() if k not in ("gold_stripped",)}
            if scan_gold_keys(body):
                gold_hits += 1
            codes = t.get("codes") or {}
            for c in codes:
                if c not in codes_allowed:
                    bad_codes.add(c)
                firing[c] += 1
            status[t["status"]] += 1
            rec = {"trace_id": trace_id, "candidate_id": cid, "task_id": t["task_id"], "repeat": r["repeat"],
                   "status": t["status"], "codes": codes if t["status"] == "judged" else None,
                   "source": t.get("source") or {}, "error": t.get("error"), "attempts": t.get("attempts")}
            mapping_rows.append(rec)
            full = dict(t)
            full["candidate_id"] = cid
            full["repeat"] = r["repeat"]
            full["legacy_candidate_index"] = full.pop("candidate_index")
            rows_by_cand.setdefault(cid, []).append(full)
        assert not gold_hits, f"{mid}: gold-bearing keys in judge records"
        assert not bad_codes, f"{mid}: codes outside {tid}: {sorted(bad_codes)}"
        mapping_rows.sort(key=lambda x: (x["candidate_id"], x["task_id"], x["repeat"]))
        jsonl_write(mapping_rows, d / "mapping.jsonl")
        rec_meta = {}
        for cid, rows in sorted(rows_by_cand.items()):
            rows.sort(key=lambda x: (x["task_id"], x["repeat"]))
            out = d / "judge_records" / f"{cid}.jsonl.gz"
            with gzip.open(out, "wt", compresslevel=6, encoding="utf-8") as fh:
                for x in rows:
                    fh.write(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n")
            rec_meta[cid] = {"file": f"judge_records/{cid}.jsonl.gz", "rows": len(rows), "sha256": sha256_file(out)}
        total_in_capture = len(idx)
        judged = status.get("judged", 0)
        coverage = judged / total_in_capture
        per_cand = Counter(x["candidate_id"] for x in mapping_rows if x["status"] == "judged")
        route = "openrouter" if str(settings["panel_model"]).startswith("openrouter/") else "gemini-direct"
        finished = datetime.date.fromtimestamp((RES / f"{run}.log").stat().st_mtime).isoformat()
        partial = judged < total_in_capture
        manifest = {
            "mapping_id": mid, "benchmark": "hover", "taxonomy": tid, "taxonomy_sha256": tax_meta[tid]["sha256"],
            "capture": cap, "split": "eval-1", "portion": portion,
            "instrument": instruments["judge"],
            "settings": {"panel_model": settings["panel_model"], "open_model": settings["open_model"], "route": route,
                         "annotators": settings["annotators"], "threshold": settings["threshold"],
                         "thinking": settings["thinking"], "max_output": settings["max_output"],
                         "traces_per_call": settings["traces_per_call"], "per_turn": settings["per_turn"],
                         "max_trace_chars": settings.get("max_trace_chars", 0), "timeout_s": settings["timeout"]},
            "structure": "data/hover/program/structure.json",
            "counts": {"traces_in_capture": total_in_capture, "attempted": len(mapping_rows), "judged": judged,
                       "failed": status.get("failed", 0), "coverage": round(coverage, 4)},
            "complete": not partial,
            "judged_per_candidate": dict(sorted(per_cand.items())),
            "traces_firing_each_code": dict(firing.most_common()),
            "unmapped_problems": summary.get("unmapped_problems"),
            "last_segment_finished": finished,
            "judge_records": rec_meta,
            "record_format": "mapping.jsonl: one row per attempted trace with the codes that fired; judge_records/: the full judge output per trace, one gzip JSONL per candidate",
            "audits": {"every_trace_in_capture_index": True, "candidate_and_task_match_capture": True,
                       "codes_within_taxonomy": True, "no_gold_keys_in_records": True,
                       "judge_reported_nothing_stripped": True},
            "derives_from": [f"results/hover/{run}", f"data/hover/taxonomies/{tid}", f"data/hover/traces/{cap}"],
        }
        jdump(manifest, d / "manifest.json")
        jdump(provenance(mid, "judge mapping", manifest["derives_from"], manifest["counts"], manifest["audits"], SCRIPT,
                         {"instrument": instruments["judge"], "taxonomy": tid, "capture": cap}), d / "provenance.json")
        cov_line = (f"**Complete: every trace of `{cap}` judged.**" if not partial else
                    f"**Partial: {judged:,} of {total_in_capture:,} traces of `{cap}` judged ({coverage:.0%}).** The judge run "
                    f"stopped there; the judged traces are spread evenly over the 12 candidates ({min(per_cand.values())} to "
                    f"{max(per_cand.values())} each). A later run that completes the capture becomes a new mapping beside this one.")
        (d / "README.md").write_text(f"""# {mid} — `{tid}` read over `{cap}` ({portion} portion)

{cov_line}

The judge held `{tid}` and read each trace of `{cap}` turn by turn, recording
which codes occurred and how many times. Two readers holding the taxonomy voted
(a code fires when both report it); one reader holding no vocabulary listed
problems, which were then mapped onto the taxonomy. A trace's codes are the
union of the two.

| | |
|---|---|
| panel | {settings['annotators']} readers, `{settings['panel_model']}`, threshold {settings['threshold']} |
| open reader | `{settings['open_model']}` |
| route | {route} |
| thinking | {settings['thinking']}; traces per call {settings['traces_per_call']}; traces never truncated |
| attempted / judged / failed | {len(mapping_rows):,} / {judged:,} / {status.get('failed', 0)} |
| problems the open reader found that mapped to no code | {summary.get('unmapped_problems')} |

| file | what it is |
|---|---|
| `mapping.jsonl` | one row per attempted trace: ids, status, the codes that fired and how often, which branch reported each |
| `judge_records/<candidate_id>.jsonl.gz` | the full judge output per trace: each reader's answer per turn, the open reader's problems and their mapping |
| `manifest.json` | settings, counts, coverage, per-code firing counts, audit results |

Traces firing each code, most to least: {", ".join(f"`{c}` {n}" for c, n in firing.most_common())}.

No gold reaches the judge and none appears here; the judge's own check that
nothing had to be stripped is recorded for every trace. Source:
`results/hover/{run}`.
""")
        table.append(f"| [`{mid}`](./{mid}/README.md) | `{tid}` | `{cap}` ({portion}) | {judged:,} / {total_in_capture:,} | {'complete' if not partial else f'partial, {coverage:.0%}'} |")
        log(f"  {mid}: {judged} judged of {total_in_capture} ({coverage:.0%}), {status.get('failed',0)} failed")

    (map_dir / "README.md").write_text("""# mappings — what the judge found in each trace

A mapping is the judge's reading of one capture under one taxonomy: for every
trace, which failure codes occurred and how many times. It is the evidence the
analyses in `../../../analyses/` are built from, and the only thing about a
trace that a scoring path reads.

| mapping | taxonomy | capture | judged | status |
|---|---|---|---:|---|
""" + "\n".join(table) + """

`map-1` and `map-3` read the same 600 traces under the two taxonomies; `map-2`
and `map-4` read the same subset of the domain traces. Comparing a sample
mapping with its domain mapping is checkpoint 1's first experiment.

A mapping is a frozen snapshot of a judge run. If a partial run is later
completed, the completed run is a new mapping; the partial one stays because
analyses cite it. Numbered ids survive a second judge configuration on the
same taxonomy and capture; this table says which is which.
""")
    jdump({"instruments": instruments, "recorded": TODAY}, NEW / "instruments.json")
    log("done")


if __name__ == "__main__":
    main()
