#!/usr/bin/env python3
"""Find what a finished taxonomy misses, on traces it was not built from.

    python -m new_pipeline.generation.gaps --taxonomy <t.json> --corpus <dir> --exclude <gen_out> --out <dir>

Generation names mechanisms from what it happened to observe. Whether that
vocabulary covers behaviour it has not seen is a different question, and it is
answered by observing fresh traces WITHOUT the taxonomy in view and then asking
which of those observations the taxonomy can express.

The observation passes are the same ones generation uses -- the reader walks
every step and is not shown the vocabulary, so it cannot be steered toward
confirming what already exists. Mapping happens afterwards, under the rule that
"none" is a rare exception which must show which codes were ruled out and why.
An unmapped finding backed by that reasoning is a candidate addition; one without
it is a mapper that did not look.

Traces already read during generation are excluded by id. A gap test on the
evidence that produced the taxonomy measures nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from new_pipeline.judge import judge as J                     # noqa: E402
from new_pipeline.llm import gemini_call, llm_call, log       # noqa: E402
from new_pipeline.generation import contracts, prompts           # noqa: E402
from new_pipeline.generation.run import batches, call_stage, require, salvage, turns_ok, flatten_turns   # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--structure", type=Path, required=True)
    ap.add_argument("--exclude", type=Path,
                    help="a generation output dir; its traces are skipped")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--tasks", type=int, default=40)
    ap.add_argument("--per-task", type=int, default=1)
    ap.add_argument("--trace-ids", type=Path, default=None,
                    help="file with one trace id per line; observe exactly these "
                         "and ignore --tasks/--per-task. They must all lie on "
                         "tasks generation did not read.")
    ap.add_argument("--work-ledger", action="store_true",
                    help="work pass returns a per-step ledger (see generation/run.py)")
    ap.add_argument("--turns-per-call", type=int, default=1,
                    help="with --per-turn-work: consecutive turns of one candidate per call")
    ap.add_argument("--per-turn-work", action="store_true",
                    help="work pass one agent turn per item (see generation/run.py)")
    ap.add_argument("--thinking", choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"],
                    default=None, help="Gemini thinking level; unset = model default")
    ap.add_argument("--max-output", type=int, default=32768,
                    help="thinking tokens count against this; raise it if a "
                         "response comes back cut")
    ap.add_argument("--work-batch-chars", type=int, default=70000)
    ap.add_argument("--batch-chars", type=int, default=260000)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    tax = json.loads(a.taxonomy.read_text())
    codes = tax.get("codes") or []
    names = [c.get("name") for c in codes]
    tax_flat = {"codes": [{"id": c.get("name"), "name": c.get("name"),
                           "description": c.get("definition"),
                           "when_to_use": c.get("when_to_use"),
                           "when_not_to_use": c.get("when_not_to_use")}
                          for c in codes]}
    tax_text = J.render_taxonomy(tax_flat)
    valid = {c["id"] for c in tax_flat["codes"]}

    # Exclude by TASK, not by trace. A different candidate attempting a problem
    # generation already read is not fresh evidence about the vocabulary: the
    # mechanisms available to be found are bounded by the problem, not by who
    # attempted it. Excluding only trace ids also silently returned almost
    # nothing, because the same seed draws the same tasks first.
    seen_traces, seen_tasks = set(), set()
    if a.exclude and (a.exclude / "stage2_observation.json").exists():
        prev = json.loads((a.exclude / "stage2_observation.json").read_text())
        seen_traces = {t["trace_id"] for t in prev["traces"]}
        for f in a.corpus.glob("*.json"):
            d = json.loads(f.read_text())
            if d.get("trace_id") in seen_traces:
                seen_tasks.add((d.get("metadata") or {}).get("task_source_id"))
    log(f"excluding {len(seen_tasks)} tasks generation already read "
        f"({len(seen_traces)} traces)")

    structure = json.loads(a.structure.read_text())
    by_cand = contracts.extract_all(a.corpus, structure)
    ctext_by = {ci: contracts.render(cs) for ci, cs in by_cand.items()}
    (a.out / "contracts.json").write_text(json.dumps(
        {str(k): v for k, v in by_cand.items()}, indent=2))

    # Build a corpus view holding only unseen tasks, then sample from it. A
    # different seed is not enough: the draw is task-ordered, so the same tasks
    # would come first again.
    fresh_dir = a.out / "fresh_corpus"
    fresh_dir.mkdir(exist_ok=True)
    kept_tasks = set()
    for f in sorted(a.corpus.glob("*.json")):
        d = json.loads(f.read_text())
        tid = (d.get("metadata") or {}).get("task_source_id")
        if tid in seen_tasks:
            continue
        kept_tasks.add(tid)
        tgt = fresh_dir / f.name
        if not tgt.exists():
            tgt.write_text(f.read_text())
    log(f"fresh corpus: {len(kept_tasks)} unseen tasks")

    ids = None
    if a.trace_ids is not None:
        ids = [l.strip() for l in a.trace_ids.read_text().splitlines() if l.strip()]
        # A recorded sample must still be fresh: refuse any id whose task
        # generation read, rather than trusting the file that drew it.
        fresh_ids = {json.loads(f.read_text()).get("trace_id")
                     for f in fresh_dir.glob("*.json")}
        stale = [t for t in ids if t not in fresh_ids]
        if stale:
            raise SystemExit(f"{len(stale)} of {len(ids)} requested traces are on "
                             f"tasks generation already read (or absent): {stale[:3]}")
        (a.out / "trace_ids.txt").write_text("\n".join(ids) + "\n")
        log(f"fixed sample: {len(ids)} trace ids from {a.trace_ids}, all fresh")

    agents = list(structure["discovered_agents"]["agents"])
    groups, n, n_tasks, _ = batches(fresh_dir, a.tasks, a.per_task, a.batch_chars,
                                    trace_ids=ids, agents=agents)
    wgroups, _, _, _ = batches(fresh_dir, a.tasks, a.per_task, a.work_batch_chars,
                               trace_ids=ids, agents=agents, per_turn=a.per_turn_work,
                               turns_per_call=a.turns_per_call)
    fresh = len({i for _, ids_, _, _ in wgroups for i in ids_})
    log(f"fresh traces available: {fresh}")
    if fresh == 0:
        raise SystemExit("no traces left after excluding generation; the pool is "
                         "exhausted and a gap test on seen evidence measures nothing")
    if ids is None:
        # trim to the requested size (the cap counts traces, not tasks)
        want = a.tasks
        def trim(grps, cap):
            out, used = [], 0
            for g, ids_, ci, exp in grps:
                if used >= cap:
                    break
                out.append((g, ids_, ci, exp)); used += len(ids_)
            return out
        groups, wgroups = trim(groups, want), trim(wgroups, want)
    n_used = len({i for _, ids_, _, _ in wgroups for i in ids_})

    work_stage = "stage2a_ledger" if a.work_ledger else "stage2a"
    if a.dry_run:
        # Build one real prompt per pass. A dry run that only counts batches
        # cannot catch a stage that is not registered, and one did not.
        if wgroups:
            g, _, ci, _ = wgroups[0]
            pw = prompts.build(work_stage, traces=g)
            (a.out / f"dry_{work_stage}.prompt.txt").write_text(pw)
            log(f"  {work_stage}: {len(pw):,} chars for the first work item")
        if groups:
            g, _, ci, _ = groups[0]
            pc = prompts.build("stage2b", contracts=ctext_by[ci], traces=g)
            (a.out / "dry_stage2b.prompt.txt").write_text(pc)
            log(f"  stage2b: {len(pc):,} chars for the first conformance batch")
        log(f"would observe {n_used} fresh traces in {len(wgroups)} work + "
            f"{len(groups)} conformance batches, then ~1 mapping call per 25 findings")
        log(f"  ~{len(wgroups) + len(groups)} observation calls; nothing spent")
        return

    call, a.model = llm_call(a.model, temperature=0.0, retries=5,
                             max_output=a.max_output, timeout=a.timeout,
                             thinking=a.thinking)
    t0 = time.time()

    def obs_ok(d):
        ts = d.get("traces")
        if not isinstance(ts, list) or not ts:
            return "expected a non-empty 'traces' list"
        return None

    findings = []
    for tag, stage, grps, mk in (
            ("work", work_stage, wgroups, lambda g, ci: {"traces": g}),
            ("conformance", "stage2b", groups,
             lambda g, ci: {"contracts": ctext_by[ci], "traces": g})):
        for i, (g, ids, ci, expected) in enumerate(grps, 1):
            nm = f"obs_{tag}_{i}"
            pg = prompts.build(stage, **mk(g, ci))
            d = call_stage(nm, pg, a.out, call, a.model,
                           log_prefix=f"  [{tag} {i}/{len(grps)}]")
            d = require(d, nm, lambda dd, _e=expected: turns_ok(dd, _e),
                        a.out, pg, call, a.model)
            for t in d["traces"]:
                if not isinstance(t, dict):
                    continue
                fs, _ = flatten_turns(t, tag)
                for f in fs:
                    f["trace_id"] = t.get("trace_id")
                    findings.append(f)
    log(f"observed {len(findings)} findings on fresh traces "
        f"({sum(1 for f in findings if f['kind']=='work')} work)")

    # Map each finding onto the taxonomy, graded. Every assignment is recorded
    # against its finding: keeping only counts, as an earlier version did, threw
    # away the one thing worth auditing -- which finding got which code, and how
    # well it actually fitted.
    from new_pipeline.judge.judge import FIT_GOOD, FIT_LOOSE, FIT_STRETCH
    mapped, records = Counter(), []
    B = 25
    for i in range(0, len(findings), B):
        chunk = findings[i:i + B]
        got = J.map_open(call, a.model,
                         [str(f.get("what_happened")) for f in chunk],
                         tax_text, valid)
        if got is None:
            log(f"  [!] mapping batch {i//B+1} failed; its findings recorded unmapped")
            records += [{"problem": str(f.get("what_happened")), "codes": [],
                         "best_fitness": None, "verdict": "mapping_failed",
                         "trace_id": f.get("trace_id"), "kind": f["kind"],
                         "turn": f.get("turn"), "agent": f.get("agent")}
                        for f in chunk]
            continue
        counts, details = got
        mapped.update(counts)
        for d in details:
            # join by index: identical finding text recurs across traces
            k = d.get("index")
            src = chunk[k] if isinstance(k, int) and 0 <= k < len(chunk) else {}
            d["trace_id"] = src.get("trace_id")
            d["kind"] = src.get("kind")
            d["turn"] = src.get("turn")
            d["agent"] = src.get("agent")
            records.append(d)

    verdicts = Counter(r["verdict"] for r in records)
    fits = [r["best_fitness"] for r in records if r.get("best_fitness") is not None]
    multi = sum(1 for r in records if len(r.get("codes") or []) > 1)
    gaps = [r for r in records if r["verdict"] in ("stretch", "uncovered")]
    out = {"benchmark": a.benchmark, "taxonomy": str(a.taxonomy),
           "fresh_traces": n_used, "findings": len(findings),
           "verdicts": dict(verdicts),
           "fitness": {"median": sorted(fits)[len(fits)//2] if fits else None,
                       "min": min(fits) if fits else None,
                       "max": max(fits) if fits else None,
                       "below_good": sum(1 for f in fits if f < FIT_GOOD),
                       "below_loose": sum(1 for f in fits if f < FIT_LOOSE)},
           "findings_with_multiple_codes": multi,
           "mapped_at_good_fit": dict(mapped.most_common()),
           "codes_never_matched_well": sorted(valid - set(mapped)),
           "records": records,
           "minutes": round((time.time() - t0) / 60, 1)}
    (a.out / "gaps.json").write_text(json.dumps(out, indent=2))
    log("=" * 60)
    log(f"{len(findings)} findings on {n_used} fresh traces")
    log(f"  verdicts: {dict(verdicts)}")
    log(f"  fitness: median {out['fitness']['median']}, "
        f"{out['fitness']['below_good']} below {FIT_GOOD}, "
        f"{out['fitness']['below_loose']} below {FIT_LOOSE}")
    log(f"  findings needing more than one code: {multi}")
    log(f"  codes never matched at a good fit: "
        f"{len(out['codes_never_matched_well'])} of {len(valid)}")
    log(f"  -> {a.out}/gaps.json  ({out['minutes']} min)")


if __name__ == "__main__":
    main()
