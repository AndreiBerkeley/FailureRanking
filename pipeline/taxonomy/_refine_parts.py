"""Prompts and helpers lifted verbatim from the audited refiner.

Kept in one place so the pipeline and the standalone script cannot drift.
"""
import json
from collections import Counter, defaultdict

MAX_EV = 800
MAX_TRACE = 2500
MAX_EXAMPLES = 3

STYLE = """A failure-mode code names a KIND OF FAILING BEHAVIOUR that a candidate
program exhibits, observable in an execution trace.

STYLE CONTRACT
- Names an ACT, not a lack. A judge must be able to QUOTE trace text satisfying it.
- Boundaries separate it from neighbours by what is VISIBLE, never by intent,
  never by outcome.
- No remedy, no routing, no advice, no consequence in its identity.
- Names the CANDIDATE'S ACTION, never the task's subject matter:
  "Unjustified_Case_Elimination" is valid, "Geometry_Error" is not.

CATEGORIES (a generality ladder)
  A  varies with neither agent nor task: a behaviour any candidate could show
  B  varies with the agent role; carries applies_to_role
  C  varies with the domain; names the act of solving, never the topic

SUBJECT TEST - candidate behaviour vs environment failure
The question is NOT whether a failure sounds like infrastructure. It is:
  could a DIFFERENTLY-DESIGNED candidate, on the same task and the same
  infrastructure, have avoided it?
  - Token-limit exhaustion from verbose generation -> YES, a more concise
    design avoids it -> CANDIDATE behaviour, keep.
  - Timeout from looping or an inefficient approach -> YES -> CANDIDATE, keep.
  - Context overflow from a bloated prompt or unbounded accumulation -> YES ->
    CANDIDATE, keep.
  - API 500, network error, rate limit, retriever whose corpus lacks the
    document, framework template rendering bug -> NO, no design avoids it ->
    ENVIRONMENT, retire.
A candidate that hits limits more often than its siblings is exhibiting a real
quality difference, and the taxonomy must be able to say so.
"""

PASS1 = """## TASK 1: complete the checklist for EVERY code

Return one entry per code. Every field is required, including "code" which
must hold the code's exact id (for example "A.1"). A missing entry or field is
an error.

  subject      "candidate" | "environment"   (apply the SUBJECT TEST above)
  observable   "yes" | "no"                  (could a judge quote evidence)
  style        "ok" | "violates"             (act-not-lack, no remedy/consequence)
  category     "ok" | "A" | "B" | "C"        (ok, or the band it belongs in)
  role         "ok" | "n/a" | "<role>"       (ALWAYS answer; use "n/a" for
                                              category A and C codes, which have
                                              no role. For B codes: "ok" if its
                                              applies_to_role exists in this
                                              architecture, else the correct role)
  adequacy     "matches" | "too_narrow" | "too_broad" | "covers_two"
               (judge by the STRETCHED evidence: if the code is repeatedly
                forced onto behaviour its definition does not name, it is
                too_narrow or covers_two, NOT "matches")
  granularity  "ok" | "too_specific" | "too_general"
  reason       one sentence
  duplicate_of "<code id>"   whenever this code names the same behaviour as another

There is NO verdict field. The verdict is DERIVED from the checks above, so a
check and a verdict can never contradict each other:

  subject=environment or observable=no        -> the code is retired
  adequacy=covers_two                         -> the code is split
  adequacy=too_narrow or too_broad,
    or style=violates, or category!=ok,
    or granularity!=ok                        -> the code is EDITED
  otherwise                                   -> the code is kept

THEREFORE: whenever ANY check is not "ok"/"matches"/"n/a", you MUST also supply
the corrected fields below. Marking a code too_narrow without supplying a wider
definition is an incomplete answer and will be rejected.

  name              corrected name, or the existing name if it needs none
  definition        corrected definition that covers how the code is ACTUALLY
                    being used, per the STRETCHED evidence shown for it
  when_to_use       corrected boundary
  when_not_to_use   corrected boundary, naming the neighbouring codes it must
                    be distinguished from

Judge each code on the CODE ITSELF. A code that did not fire in this sample is
not thereby faulty; removal by measured support happens elsewhere. A code is
retired ONLY for subject="environment" or observable="no".

Return ONLY JSON: {"checks":[{...}]}
"""

PASS2 = """## TASK 2: cross-code operations

The per-code checklist is above; codes marked environment or unobservable are
already being retired, and codes marked "edit" already have corrected
definitions. Decide only what requires seeing codes TOGETHER, or failures no
code covers.

- MERGE codes that name the same behaviour (use the merge_candidate /
  duplicate_of findings), or codes so specific they describe one incident and
  belong under one mechanism. The merged definition must cover everything its
  sources covered. Merging may cross categories; pick the band that fits the
  merged behaviour.
- SPLIT any code whose checklist says covers_two, or whose evidence clusters
  into two distinct behaviours.
- ADD only where unmapped failure points show an uncovered CANDIDATE behaviour
  that RECURS. One occurrence is not a pattern. An environment failure is never
  a code.

Return ONLY JSON:
{"merge":[{"codes":["X.1","Y.2"],"category":"A|B|C","name":"...","definition":"...","when_to_use":"...","when_not_to_use":"...","applies_to_role":"only for B","reason":"..."}],
 "split":[{"code":"C.4","reason":"...","into":[{"name":"...","definition":"...","when_to_use":"...","when_not_to_use":"..."}]}],
 "add":[{"category":"A|B|C","name":"...","definition":"...","when_to_use":"...","when_not_to_use":"...","applies_to_role":"only for B","reason":"..."}]}
"""

CONSOLIDATE = """## TASK: consolidate the panel

Four reviewers independently completed the per-code checklist above, seeing the
same codes and the same evidence. Their verdicts are shown per code. Where they
agree, the finding is stable. Where they disagree, one of them is reading the
evidence wrong, and you must decide which by looking at the evidence yourself.

For every code, return the final checklist entry. Rules:
- Where all four agree, keep that answer unless the evidence plainly
  contradicts it.
- Where they split, decide from the STRETCHED evidence shown for that code: a
  code repeatedly forced onto behaviour its definition does not name IS
  too_narrow or covers_two, regardless of how many reviewers said "matches".
- A lone dissenter who cites specific evidence outweighs three who assert
  without it.

Same field rules as the reviewers: every field required, and whenever any check
is not "ok"/"matches"/"n/a" you MUST supply corrected name, definition,
when_to_use and when_not_to_use. Also return "panel_note" for each code, one
sentence saying whether the panel agreed and how you resolved any split.

Return ONLY JSON: {"checks":[{...}]}
"""

def elide(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    head = int(limit * 0.6)
    return (text[:head] + f"\n[... {len(text)-limit} chars elided by the refinement "
            f"harness, not by the agent ...]\n" + text[-(limit - head):])

def gather(results, traces):
    weak, fired = defaultdict(list), defaultdict(list)
    unmapped = defaultdict(lambda: {"support": 0, "evidence": [], "definitions": [],
                                    "ruled_out": Counter()})
    util = defaultdict(lambda: {"n": 0, "conf": [], "co": Counter()})
    for r in results:
        rid = r.get("run_id")
        trace = traces.get(rid, "")
        ss = r.get("selection_summary", {}) or {}
        fps = {fp.get("failure_point_id"): fp for fp in (r.get("failure_points") or [])}
        for wm in (ss.get("weak_taxonomy_matches") or []):
            code = wm.get("code")
            if not code:
                continue
            fp = fps.get(wm.get("failure_point_id")) or {}
            weak[code].append({
                "conf": wm.get("mapping_confidence"),
                "rationale": wm.get("mapping_rationale"),
                "summary": fp.get("summary"),
                "evidence": elide(fp.get("observed_evidence"), MAX_EV),
                "trace": elide(trace, MAX_TRACE)})
        for up in (ss.get("unmapped_failure_points") or []):
            name = (up.get("proposed_name") or "").strip()
            if not name:
                continue
            s = unmapped[name.lower()]
            s["support"] += 1
            s["name"] = name
            if up.get("proposed_definition"):
                s["definitions"].append(up["proposed_definition"])
            for c in (up.get("ruled_out_codes") or []):
                s["ruled_out"][c] += 1
            fp = fps.get(up.get("failure_point_id")) or {}
            s["evidence"].append({
                "summary": fp.get("summary") or up.get("summary"),
                "evidence": elide(fp.get("observed_evidence"), MAX_EV),
                "trace": elide(trace, MAX_TRACE)})
        for fp in (r.get("failure_points") or []):
            here = [tm.get("code") for tm in (fp.get("taxonomy_mappings") or []) if tm.get("code")]
            for tm in (fp.get("taxonomy_mappings") or []):
                code = tm.get("code")
                if not code:
                    continue
                u = util[code]
                u["n"] += 1
                c = tm.get("mapping_confidence")
                if isinstance(c, (int, float)):
                    u["conf"].append(float(c))
                for o in here:
                    if o != code:
                        u["co"][o] += 1
                if len(fired[code]) < MAX_EXAMPLES:
                    fired[code].append({
                        "conf": c, "summary": fp.get("summary"),
                        "evidence": elide(fp.get("observed_evidence"), MAX_EV),
                        "rationale": tm.get("mapping_rationale")})
    return weak, unmapped, fired, util

def code_block(c, util, fired, weak, roles):
    u = util.get(c.code, {})
    confs = u.get("conf") or []
    avg = round(sum(confs) / len(confs), 2) if confs else None
    co = dict(u.get("co") or {})
    out = [f"\n### {c.code}  {c.name}   [category {c.category}"
           + (f", applies_to_role {c.applies_to_role}" if c.applies_to_role else "") + "]",
           f"definition: {c.definition}"]
    if c.when_to_use:
        out.append(f"when_to_use: {c.when_to_use}")
    if c.when_not_to_use:
        out.append(f"when_not_to_use: {c.when_not_to_use}")
    out.append(f"USAGE: fired {u.get('n', 0)}x"
               + (f", avg confidence {avg}" if avg is not None else "")
               + (f", co-mapped with {co}" if co else ""))
    for ex in fired.get(c.code, []):
        out.append(f"  USED @ {ex['conf']}: {ex['summary']}")
        out.append(f"    judge-recorded evidence: {ex['evidence']}")
    for w in weak.get(c.code, [])[:3]:
        out.append(f"  STRETCHED @ {w['conf']}: {w['summary']}")
        out.append(f"    judge-recorded evidence: {w['evidence']}")
        out.append(f"    judge stretched it because: {w['rationale']}")
        out.append(f"    ACTUAL TRACE (verify the claim yourself):\n{w['trace']}")
    return "\n".join(out)
