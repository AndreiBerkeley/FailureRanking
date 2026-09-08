#!/usr/bin/env python3
"""Build the frozen taxonomy from the generated 32-code draft.

Reproducible record of the freeze decisions (Andrei):
1. Trace-grounding rule (2026-08-07): drop every code with < 3
   unique-trace support in the full-view support judging
   (support_judging_full, 60 traces, max_trace_chars 40000).
2. Re-partition of the four over-broad top codes along mechanism
   boundaries found in their own evidence snippets (178 read in full).
3. (2026-08-08, after the Stage-1 dry run on the 24-trace slice)
   - Terminal_Output_Without_Verification DROPPED: it fired on 22/24
     traces for the program's specified terminal behavior (final output
     is the retrieved documents; no verdict is requested), so it
     penalized correct execution.
   - Flat sequential ids, no letter suffixes: codes retained verbatim
     from the draft keep their ids; every code whose definition changed
     (re-partitioned, merged, or rescoped) gets a fresh id above the
     draft's maxima (A ≤ 11, B ≤ 9, C ≤ 12) so no id ever denotes two
     different definitions across artifacts.
Sub-code support is PROVISIONAL (mechanical evidence reassignment, not a
fresh judging run); validated implicitly at the subset re-judge.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "taxonomy_v0/taxonomy.json"
OUT = HERE / "taxonomy_frozen_v1.json"

KEEP_AS_IS = ["A.6", "A.8", "A.10", "B.1", "B.6", "B.8", "C.1", "C.4", "C.7"]

# new/changed definitions -> fresh ids above the draft maxima
NEW_CODES = [
    dict(id="B.10", category="B", name="Evidence_Present_But_Missed",
         former="B.2 (part)",
         description=(
             "The solver claims evidence is absent or insufficient when the "
             "retrieved passages available to it contain the needed fact. "
             "Fires only when the specific claimed-missing information is "
             "verifiably present in a passage the solver received. Does not "
             "fire when the information truly is absent from the passages "
             "(see B.11 or A.12).")),
    dict(id="B.11", category="B", name="Missing_Evidence_Not_Specified",
         former="B.2 (part)",
         description=(
             "The solver correctly recognizes the claim cannot be verified "
             "but no solver summary names the specific missing entity or "
             "fact, leaving retrieval with nothing concrete to chase. "
             "DECISION TEST (apply once per evidence gap, not per summary): "
             "scan EVERY solver summary in the trace for the missing entity "
             "named explicitly; if ANY summary names it, this code does NOT "
             "fire for that gap — assign A.12 or B.13 instead. Quote the "
             "summary text you scanned. Two codes may both fire on a trace "
             "only when they concern DIFFERENT evidence gaps.")),
    dict(id="B.12", category="B", name="Verdict_Despite_Insufficiency",
         former="B.3 + B.2 (part), merged",
         description=(
             "A solver renders a definitive verdict (supported / refuted / "
             "factual-error) while its own analysis acknowledges the "
             "evidence is insufficient, or before verification is complete. "
             "Does not fire when the solver withholds judgment or the "
             "evidence genuinely settles the claim.")),
    dict(id="B.13", category="B", name="Query_Form_Mismatch",
         former="B.5 (part)",
         description=(
             "A coordinator retrieval query is formulated in a shape the "
             "retriever cannot use well: natural-language yes/no questions, "
             "compound multi-part asks bundling several targets, or "
             "unstructured keyword soup with no target entity. Judged on "
             "the query text alone. Does not fire for well-formed queries "
             "that merely repeat earlier ones (B.14).")),
    dict(id="B.14", category="B", name="Query_Stagnation",
         former="B.5/B.9/A.11 (part)",
         description=(
             "Successive retrieval queries fail to advance: near-identical "
             "wording across hops, re-asking already-answered questions, or "
             "ignoring gaps and guidance the summaries already provided, so "
             "later hops fetch the same or equivalent documents. Does not "
             "fire when queries change substantively between hops, even if "
             "retrieval still fails (A.12).")),
    dict(id="B.15", category="B", name="Retrieval_Loop_Terminated_Early",
         former="B.9 (part)",
         description=(
             "Fewer retrievals were executed than the task's required "
             "three: a RETRIEVAL EVENT message is absent for some hop, or a "
             "generated query was never executed. Count RETRIEVAL EVENT "
             "messages explicitly; do not infer hop counts from passage "
             "text inside prompts. Does not fire when all three retrievals "
             "executed but were unproductive (B.14).")),
    dict(id="A.12", category="A", name="Insufficient_Retrieved_Evidence",
         former="A.11, rescoped",
         description=(
             "Environment-attributable: the passages needed to verify the "
             "claim never arrived although the gap was explicitly named in "
             "a summary and chased by well-formed, advancing queries — a "
             "corpus or retriever coverage gap, not an agent fault. "
             "DECISION TEST (apply once per evidence gap): fires only if "
             "BOTH (i) some solver summary names the missing entity — quote "
             "it — and (ii) a later query targets that entity in usable "
             "form — quote it. If (i) fails assign B.11; if (ii) fails "
             "assign B.13 or B.14. Never assign this code and B.11 to the "
             "same evidence gap.")),
]

src = json.loads(SRC.read_text())
by_id = {c["id"]: c for c in src["codes"]}
codes = [dict(by_id[i]) for i in KEEP_AS_IS] + NEW_CODES
codes.sort(key=lambda c: (c["category"], int(c["id"].split(".")[1])))
assert len(codes) == 16, len(codes)
assert len({c["id"] for c in codes}) == 16
draft_max = {"A": 11, "B": 9, "C": 12}
for c in NEW_CODES:  # no id ever denotes two definitions
    assert int(c["id"].split(".")[1]) > draft_max[c["category"]], c["id"]

out = {
    "metadata": {
        "display_name": "HoVer three-hop grounded taxonomy (frozen v1)",
        "frozen": "2026-08-08",
        "parent": str(SRC),
        "parent_version": src.get("metadata", {}).get("version"),
        "provenance": (
            "generated by adamast generate (agreement-gated, review_required "
            "at kappa 0.37) -> full-view support judging (60 traces, "
            "max_trace_chars 40000) -> trace-grounding filter (support >= 3) "
            "-> evidence-driven re-partition -> Stage-1 dry run on the "
            "24-trace slice -> dropped Terminal_Output_Without_Verification "
            "(fired on the program's specified ending) and renumbered "
            "changed codes to fresh sequential ids -> frozen. Sub-code "
            "support provisional pending the subset re-judge. "
            "Prototyping-grade per the 2026-08-07 data amendment."),
        "counts": {"total": len(codes)},
    },
    "category_definitions": src.get("category_definitions", {}),
    "codes": codes,
}
OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
print(f"wrote {OUT} with {len(codes)} codes "
      f"({sum(1 for c in codes if c['category']=='A')} A, "
      f"{sum(1 for c in codes if c['category']=='B')} B, "
      f"{sum(1 for c in codes if c['category']=='C')} C)")
for c in codes:
    print(f"  {c['id']:>5}  {c['name']}"
          + (f"   [was {c['former']}]" if c.get("former") else ""))
