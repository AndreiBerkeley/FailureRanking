#!/usr/bin/env python3
"""Split codes that carry several mechanisms. Evidence proposes, data disposes.

    python -m new_pipeline.generation.granularity --taxonomy <t.json> --records <gaps.json> --out <dir>

Generation answers coverage: does every observed failure have a home? It does not
answer granularity: is each home one thing? Measured on hover, one code took 44%
of all findings and every individual mapping was correct at fitness 100 -- the
fitness score cannot see this, because it asks whether a code fits a finding, not
whether a code is doing too much.

There is no general answer to how fine a taxonomy should be; it depends on what
the evidence under each code actually looks like. So the test is empirical rather
than stipulated:

  a split is real when its parts can occur INDEPENDENTLY.

If every trace showing one part also shows the others, they are one mechanism
described several ways and the split is cosmetic. If they appear apart, they are
separate things a candidate can exhibit separately -- which is exactly what a
ranking instrument needs to distinguish.

The model proposes a split from the findings. This module then measures whether
the proposed parts actually separate, and rejects those that do not.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from new_pipeline.judge import judge as J                     # noqa: E402
from new_pipeline.llm import gemini_call, log       # noqa: E402
from new_pipeline.generation.run import call_stage, require      # noqa: E402

PROMPT = """## THE CODE UNDER EXAMINATION

{code}

## EVERY FINDING THAT WAS ASSIGNED TO IT

{findings}

## TASK

These findings were all filed under one code. Decide whether that code names ONE
mechanism or several.

Read the FINDINGS, not the definition. The definition is what someone wrote
before seeing this evidence. The findings are what actually happened.

SPLIT when the findings fall into groups that differ in MECHANISM -- in what the
program did wrong, not in what it was doing when it went wrong, not in which
agent did it, and not in how the finding happens to be worded. The decisive
question for each group: could a program exhibit THIS without exhibiting the
others? If a program that does one always does the rest, they are one mechanism
seen from several angles.

KEEP when the findings are one mechanism in different surface forms. Different
wording, different agents, different output fields, different entities involved
-- none of these is a difference in mechanism.

A split may have two parts or many. Assign EVERY finding to exactly one part. A
part holding a single finding is an instance, not a mechanism: fold it into
whichever part it most resembles, or leave the code unsplit.

Each part must stand alone as a code. It names a mechanism rather than a
consequence, carries no agent or role name, and a judge reading a trace could
tell it from its siblings without guessing.

Return ONLY JSON.
To keep the code as it is:
  {{"verdict": "keep", "why": "<why these findings are one mechanism>"}}
To split it:
  {{"verdict": "split", "why": "<what distinguishes the parts>",
    "parts": [{{"name": "...", "definition": "...", "when_to_use": "...",
               "when_not_to_use": "<how a judge tells it from its siblings>",
               "finding_indices": [<indices from the list above>]}}]}}
"""


PROMPT_FORCED = """## THE CODE UNDER EXAMINATION

{code}

## EVERY FINDING THAT WAS ASSIGNED TO IT

{findings}

## TASK

These findings were all filed under one code. Propose the BEST division of them
into distinct mechanisms.

YOU MUST PROPOSE A DIVISION. Do not decline and do not answer that the code
should stay whole. Whether it stays whole is decided afterwards, from whether
your parts actually occur apart in the traces -- not from your opinion of them.
If you are wrong and these are one mechanism, your parts will always appear
together and the division will be rejected on that evidence. That outcome costs
nothing and is more informative than declining.

Read the FINDINGS, not the definition. The definition is what someone wrote
before seeing this evidence. The findings are what actually happened.

Divide by MECHANISM -- what the program did wrong, not what it was doing when it
went wrong, not which agent did it, and not how the finding happens to be
worded. The question that matters for each part: could a program exhibit THIS
without exhibiting the others?

A division may have two parts or many. Assign EVERY finding to exactly one part.
A part holding a single finding is an instance rather than a mechanism: fold it
into whichever part it most resembles.

Each part must stand alone as a code. It names a mechanism rather than a
consequence, carries no agent or role name, and a judge reading a trace could
tell it from its siblings without guessing.

Say in "confidence" how strongly you believe these really are separate
mechanisms: "distinct" if you are confident, "unsure", or "probably_one" if you
think the code is whole and you are dividing it only because you were asked.

Return ONLY JSON:
{{"verdict": "split", "confidence": "distinct"|"unsure"|"probably_one",
  "why": "<what distinguishes the parts, or why you doubt they differ>",
  "parts": [{{"name": "...", "definition": "...", "when_to_use": "...",
             "when_not_to_use": "<how a judge tells it from its siblings>",
             "finding_indices": [<indices from the list above>]}}]}}
"""


def independence(parts, idx_to_trace):
    """Do the proposed parts occur apart, or always together?

    Measured per trace: a part that never appears without its siblings is not a
    separate mechanism, whatever its definition says. Reported per pair so a
    split that separates cleanly on one boundary and not another is visible
    rather than accepted or rejected wholesale.
    """
    by_part = {}
    for p in parts:
        traces = {idx_to_trace.get(i) for i in (p.get("finding_indices") or [])}
        by_part[p["name"]] = {t for t in traces if t}
    solo, pairs = {}, []
    for name, ts in by_part.items():
        others = set().union(*[v for k, v in by_part.items() if k != name]) if len(by_part) > 1 else set()
        alone = ts - others
        solo[name] = {"traces": len(ts), "alone": len(alone),
                      "alone_frac": round(len(alone) / len(ts), 2) if ts else 0.0}
    for a, b in combinations(by_part, 2):
        ta, tb = by_part[a], by_part[b]
        both = ta & tb
        pairs.append({"a": a, "b": b, "a_only": len(ta - tb), "b_only": len(tb - ta),
                      "both": len(both),
                      "separates": bool((ta - tb) and (tb - ta))})
    return solo, pairs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taxonomy", type=Path, required=True)
    ap.add_argument("--records", type=Path, required=True,
                    help="gaps.json, or any file with per-finding code assignments")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--min-findings", type=int, default=6,
                    help="codes with fewer findings than this are left alone: "
                         "there is not enough evidence to tell one mechanism "
                         "from several")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--force-split", action="store_true",
                    help="the model may not answer 'keep'; it must always propose "
                         "a division and the independence test decides. Makes "
                         "every verdict data-decided rather than only the splits "
                         "the model volunteers.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    tax = json.loads(a.taxonomy.read_text())
    codes = {c["name"]: c for c in tax["codes"]}
    recs = json.loads(a.records.read_text())["records"]

    grouped = defaultdict(list)
    for r in recs:
        if not r.get("codes"):
            continue
        top = max(r["codes"], key=lambda c: c["fitness"])
        grouped[top["code"]].append(r)

    todo = {k: v for k, v in grouped.items() if len(v) >= a.min_findings}
    skip = {k: len(v) for k, v in grouped.items() if len(v) < a.min_findings}
    log(f"{len(grouped)} codes carry findings; examining {len(todo)} with "
        f">={a.min_findings}")
    for k, n in sorted(skip.items(), key=lambda x: -x[1]):
        log(f"  left alone ({n} findings): {k}")
    if a.dry_run:
        for k, v in sorted(todo.items(), key=lambda x: -len(x[1])):
            log(f"  would examine {k}: {len(v)} findings")
        log(f"{len(todo)} calls; nothing spent")
        return

    call = gemini_call(temperature=0.0, retries=5, max_output=32768, timeout=a.timeout)
    t0, out = time.time(), []
    for name, rs in sorted(todo.items(), key=lambda x: -len(x[1])):
        c = codes.get(name, {"name": name})
        block = json.dumps({k: c.get(k) for k in
                            ("name", "column", "definition", "when_to_use",
                             "when_not_to_use")}, indent=2)
        listing = "\n".join(f"{i}. {r['problem']}" for i, r in enumerate(rs))
        tmpl = PROMPT_FORCED if a.force_split else PROMPT
        prompt = tmpl.format(code=block, findings=listing)
        nm = f"split_{name[:40]}"

        def ok(d):
            if a.force_split:
                if d.get("verdict") != "split":
                    return ("this mode does not accept 'keep'; propose the best "
                            "division you can and record your doubt in "
                            "'confidence'")
            elif d.get("verdict") not in ("keep", "split"):
                return "verdict must be 'keep' or 'split'"
            if d.get("verdict") == "keep":
                return None
            parts = d.get("parts") or []
            if len(parts) < 2:
                return "a split needs at least two parts"
            seen = [i for p in parts for i in (p.get("finding_indices") or [])]
            missing = [i for i in range(len(rs)) if i not in seen]
            if missing:
                return (f"{len(missing)} findings are assigned to no part "
                        f"({missing[:5]}); every finding must go in exactly one")
            dup = [i for i, n in Counter(seen).items() if n > 1]
            if dup:
                return f"findings assigned to more than one part: {dup[:5]}"
            return None

        d = call_stage(nm, prompt, a.out, call, a.model,
                       log_prefix=f"  [{name[:34]} x{len(rs)}]")
        d = require(d, nm, ok, a.out, prompt, call, a.model)

        idx_to_trace = {i: r.get("trace_id") for i, r in enumerate(rs)}
        entry = {"code": name, "findings": len(rs), "verdict": d["verdict"],
                 "why": d.get("why")}
        if d["verdict"] == "split":
            solo, pairs = independence(d["parts"], idx_to_trace)
            # A split whose parts never appear apart is one mechanism with two
            # names. Rejected here rather than shipped, because no later stage
            # can tell the difference from the definitions alone.
            separating = [p for p in pairs if p["separates"]]
            accepted = bool(pairs) and len(separating) == len(pairs)
            entry.update({"parts": d["parts"], "confidence": d.get("confidence"),
                          "independence": solo,
                          "pairs": pairs, "accepted": accepted,
                          "reason": ("every pair of parts occurs apart"
                                     if accepted else
                                     "some parts never occur without each other")})
            log(f"    -> split into {len(d['parts'])} "
                f"[confidence: {d.get('confidence', 'n/a')}]: "
                f"{'ACCEPTED' if accepted else 'REJECTED'} ({entry['reason']})")
            for n2, s in solo.items():
                log(f"       {n2[:46]:<48} {s['alone']}/{s['traces']} traces alone")
        else:
            log(f"    -> keep: {str(d.get('why'))[:90]}")
        out.append(entry)

    res = {"taxonomy": str(a.taxonomy), "records": str(a.records),
           "mode": "force_split" if a.force_split else "model_may_keep",
           "examined": len(todo), "left_alone": skip,
           "results": out, "minutes": round((time.time()-t0)/60, 1)}
    (a.out/"granularity.json").write_text(json.dumps(res, indent=2))
    acc = [o for o in out if o.get("accepted")]
    log("=" * 60)
    log(f"examined {len(todo)} codes: {len(acc)} splits accepted, "
        f"{sum(1 for o in out if o['verdict']=='split' and not o.get('accepted'))} "
        f"rejected as non-separating, "
        f"{sum(1 for o in out if o['verdict']=='keep')} kept")
    if acc:
        newn = len(tax['codes']) - len(acc) + sum(len(o['parts']) for o in acc)
        log(f"  taxonomy would go from {len(tax['codes'])} to {newn} codes")
    log(f"  -> {a.out}/granularity.json")


if __name__ == "__main__":
    main()
