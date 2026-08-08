#!/usr/bin/env python3
"""Build the frozen 17-code taxonomy from the generated 32-code draft.

Reproducible record of the 2026-08-07 freeze decisions (Andrei):
1. Trace-grounding rule: drop every code with < 3 unique-trace support in
   the full-view support judging (support_judging_full, 60 traces,
   max_trace_chars 40000).
2. Re-partition of the four over-broad top codes along mechanism
   boundaries found in their own evidence snippets (178 read in full):
   B.2 -> B.2a/B.2b (+ B.2c merged into B.3); B.5 -> B.5a/B.5b;
   B.9 -> B.9a/B.9b; A.11 rescoped to environment-side gaps.
3. Kept unchanged: the nine mid-tier grounded codes.
Sub-code support is PROVISIONAL (mechanical evidence reassignment, not a
fresh judging run); validated implicitly at the subset re-judge.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "taxonomy_v0/taxonomy.json"
OUT = HERE / "taxonomy_frozen_v1.json"

KEEP_AS_IS = ["A.6", "A.8", "A.10", "B.1", "B.6", "B.8", "C.1", "C.4", "C.7"]

NEW_CODES = [
    dict(id="B.2a", category="B", name="Evidence_Present_But_Missed",
         description=(
             "The solver claims evidence is absent or insufficient when the "
             "retrieved passages available to it contain the needed fact. "
             "Fires only when the specific claimed-missing information is "
             "verifiably present in a passage the solver received. Does not "
             "fire when the information truly is absent from the passages "
             "(see B.2b or A.11).")),
    dict(id="B.2b", category="B", name="Missing_Evidence_Not_Specified",
         description=(
             "The solver correctly recognizes the claim cannot be verified "
             "but no solver summary names the specific missing entity or "
             "fact, leaving retrieval with nothing concrete to chase. Does "
             "not fire when any summary explicitly names the gap (then see "
             "A.11 if well-formed queries still failed), or when the "
             "evidence was actually present (B.2a).")),
    dict(id="B.3", category="B", name="Verdict_Despite_Insufficiency",
         description=(
             "A solver renders a definitive verdict (supported / refuted / "
             "factual-error) while its own analysis acknowledges the "
             "evidence is insufficient, or before verification is complete. "
             "Merge of the draft's Solver_Premature_Verification_Conclusion "
             "with the verdict-despite-acknowledged-insufficiency pattern "
             "formerly inside B.2. Does not fire when the solver withholds "
             "judgment or the evidence genuinely settles the claim.")),
    dict(id="B.5a", category="B", name="Query_Form_Mismatch",
         description=(
             "A coordinator retrieval query is formulated in a shape the "
             "retriever cannot use well: natural-language yes/no questions, "
             "compound multi-part asks bundling several targets, or "
             "unstructured keyword soup with no target entity. Judged on "
             "the query text alone. Does not fire for well-formed queries "
             "that merely repeat earlier ones (B.5b).")),
    dict(id="B.5b", category="B", name="Query_Stagnation",
         description=(
             "Successive retrieval queries fail to advance: near-identical "
             "wording across hops, re-asking already-answered questions, or "
             "ignoring gaps and guidance the summaries already provided, so "
             "later hops fetch the same or equivalent documents. One home "
             "for the stagnation pattern formerly smeared across B.5, B.9, "
             "and A.11. Does not fire when queries change substantively "
             "between hops, even if retrieval still fails (A.11).")),
    dict(id="B.9a", category="B", name="Retrieval_Loop_Terminated_Early",
         description=(
             "Fewer retrievals were executed than the task's required "
             "three: a RETRIEVAL EVENT message is absent for some hop, or a "
             "generated query was never executed. Count RETRIEVAL EVENT "
             "messages explicitly; do not infer hop counts from passage "
             "text inside prompts. Does not fire when all three retrievals "
             "executed but were unproductive (B.5b) or the ending lacked "
             "verification (B.9b).")),
    dict(id="B.9b", category="B", name="Terminal_Output_Without_Verification",
         description=(
             "The run ends with a final document dump and no concluding "
             "verification analysis: all required retrievals executed, but "
             "no final solver pass assesses the claim against what was "
             "retrieved. Does not fire when a final summary renders or "
             "explicitly withholds a verification assessment.")),
    dict(id="A.11", category="A", name="Insufficient_Retrieved_Evidence",
         description=(
             "RESCOPED, environment-attributable: the passages needed to "
             "verify the claim never arrived although the gap was "
             "explicitly named in a summary and chased by well-formed, "
             "advancing queries — a corpus or retriever coverage gap, not "
             "an agent fault. Does not fire when the gap was never named "
             "(B.2b), queries were malformed (B.5a), or queries stagnated "
             "(B.5b).")),
]

src = json.loads(SRC.read_text())
by_id = {c["id"]: c for c in src["codes"]}
codes = [dict(by_id[i]) for i in KEEP_AS_IS] + NEW_CODES
codes.sort(key=lambda c: (c["category"], c["id"]))
assert len(codes) == 17, len(codes)

out = {
    "metadata": {
        "display_name": "HoVer three-hop grounded taxonomy (frozen v1)",
        "frozen": "2026-08-07",
        "parent": str(SRC),
        "parent_version": src.get("metadata", {}).get("version"),
        "provenance": (
            "generated by adamast generate (agreement-gated, review_required "
            "at kappa 0.37) -> full-view support judging (60 traces, "
            "max_trace_chars 40000) -> trace-grounding filter (support >= 3) "
            "-> evidence-driven re-partition of B.2/B.5/B.9/A.11, B.3 merge "
            "-> frozen. Sub-code support provisional pending subset re-judge. "
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
