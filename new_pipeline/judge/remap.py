#!/usr/bin/env python3
"""Re-map the open reader's findings onto the taxonomy, without re-judging.

    python -m new_pipeline.judge.remap --taxonomy <tax.json> --results <run>/traces

Why this exists as a separate pass: the open reader's problems are stored
verbatim in every result, so correcting the MAPPING costs one call per trace
instead of the six a full re-judge costs. Measured on the first runs, 1,002
calls against 10,800.

What it changes and what it does not. The panel is untouched -- its votes and
counts are already correct and independent of the mapping. Only the open
branch's contribution and the union are recomputed. The original mapping is
preserved under `open.superseded` so the correction is auditable rather than
silent.

Run it over the WHOLE result set, never a subset. A corpus half-mapped under one
prompt and half under another is two instruments, and comparing candidates
measured by different instruments is the error this project exists to avoid.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median_low

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from new_pipeline.judge import judge                          # noqa: E402
from new_pipeline.llm import gemini_call, log       # noqa: E402


def remap_one(path: Path, tax_text, valid_ids, call, model, threshold):
    r = json.loads(path.read_text())
    if r.get("status") != "judged":
        return None
    op = r.get("open") or {}
    problems = op.get("problems") or []
    if not problems:
        return None                                # nothing to re-map

    got = judge.map_open(call, model, problems, tax_text, valid_ids)
    if got is None:
        return ("failed", path.name)
    open_counts, unmapped = got

    before = dict(r["codes"])
    panel = (r.get("panel") or {}).get("annotators") or []
    final, votes = judge.consolidate(panel, open_counts, threshold, agg=median_low)

    src = {}
    for c, v in votes.items():
        if v >= threshold:
            src.setdefault(c, []).append("panel")
    for c in open_counts:
        src.setdefault(c, []).append("open")

    r["codes"] = final
    r["source"] = {c: src[c] for c in final}
    r["open"] = {"problems": problems, "mapped": open_counts, "unmapped": unmapped,
                 # the original mapping, kept so the correction is auditable
                 "superseded": {"mapped": op.get("mapped"),
                                "unmapped": op.get("unmapped"),
                                "reason": "mapping prompt rebalanced; 'none' was "
                                          "being answered for problems an existing "
                                          "code already covered"}}
    path.write_text(json.dumps(r, indent=2))
    just = sum(1 for u in unmapped if isinstance(u, dict) and u.get("justified"))
    return ("ok", before, final, len(problems), len(unmapped),
            len(op.get("unmapped") or []), just)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--results", type=Path, required=True, help="the traces/ dir")
    ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--threshold", type=int, default=2)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    taxonomy = json.loads(a.taxonomy.read_text())
    tax_text = judge.render_taxonomy(taxonomy)
    valid_ids = {c["id"] for c in taxonomy["codes"]}
    files = sorted(a.results.glob("*.json"))
    if a.limit:
        files = files[:a.limit]

    todo = []
    for f in files:
        r = json.loads(f.read_text())
        if r.get("status") == "judged" and (r.get("open") or {}).get("problems"):
            todo.append(f)
    log(f"remap: {len(files)} results, {len(todo)} carry open problems "
        f"-> {len(todo)} calls")
    if a.dry_run:
        log("dry run: nothing spent")
        return

    call = gemini_call(temperature=a.temperature, retries=5)
    t0 = time.time()
    stats = Counter(); gained = Counter(); lost = Counter()
    um_before = um_after = just_after = 0

    def work(f):
        return remap_one(f, tax_text, valid_ids, call, a.model, a.threshold)

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, fut in enumerate(as_completed([ex.submit(work, f) for f in todo]), 1):
            out = fut.result()
            if out is None:
                continue
            if out[0] == "failed":
                stats["failed"] += 1
                continue
            _, before, after, nprob, nun, nun_before, njust = out
            stats["remapped"] += 1
            um_after += nun; um_before += nun_before; just_after += njust
            for c in set(after) - set(before):
                gained[c] += 1
            for c in set(before) - set(after):
                lost[c] += 1
            if i % 50 == 0:
                log(f"  {i}/{len(todo)} ({time.time()-t0:.0f}s)")

    log("=" * 60)
    log(f"remapped {stats['remapped']}, failed {stats['failed']}, "
        f"{round((time.time()-t0)/60,1)} min")
    log(f"  unmapped problems: {um_before} -> {um_after} "
        f"({100*(um_before-um_after)/um_before if um_before else 0:.0f}% recovered)")
    # a "none" that shows which codes it ruled out is a coverage finding;
    # one that does not is the mapper failing to look. Never sum them.
    log(f"    of those {um_after}: {just_after} justified (ruled_out shown) = "
        f"real coverage gaps, {um_after - just_after} unjustified = mapper "
        f"declined without checking")
    log(f"  code firings gained: {sum(gained.values())}  {dict(gained.most_common(6))}")
    log(f"  code firings lost:   {sum(lost.values())}  {dict(lost.most_common(6))}")
    log("  the panel was not touched; only the open branch and the union changed")


if __name__ == "__main__":
    main()
