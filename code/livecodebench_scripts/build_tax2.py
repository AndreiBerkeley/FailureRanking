"""tax-2 = tax-1 + three hand-authored codes for the 22 points pointjudge-1 could not place.

The seven tax-1 codes are carried byte-identical. The new codes are grounded on the
uncovered points of runs/new_pipeline/lcb-models/pointjudge-1 (their evidence spans are
the `evidence` entries); those points are grounding, not occurrences under this taxonomy.

    python3 data/livecodebench/scripts/build_tax2.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "taxonomies" / "tax-1" / "taxonomy.json"
OUT = ROOT / "taxonomies" / "tax-2"
RUN = Path("runs/new_pipeline/lcb-models/pointjudge-1")

NEW = [
 {"id": "SP_08", "column": "domain", "name": "unsound_algorithmic_strategy_or_structural_premise",
  "definition": "The agent commits to an overall solution strategy -- a greedy rule, a search method, a data structure, or a decomposition of the input -- whose correctness rests on a property the problem does not guarantee (sortedness, bijectivity, unimodality, independence of choices, symmetry), so the method is wrong as a whole rather than at one step.",
  "when_to_use": "Use when the trace shows a locally consistent, syntactically complete algorithm built on a false premise about the problem's structure: a greedy choice where an exact search or matching is required, a two-pointer or ternary search whose precondition is unmet, a functional graph treated as a permutation, an order-dependent process modelled with a symmetric structure, or an assumption that choices are independent when the input couples them.",
  "when_not_to_use": "Do not use when the overall strategy is sound and the defect is one formula (SP_04), one DP state or transition (SP_03), one bookkeeping step of a simulation (SP_05), one boundary (SP_06), one predicate (SP_07), or a coding slip inside a correct method (SP_09).",
  "consequence": "The program is internally consistent and may pass the samples, but returns wrong answers on every input where the assumed property fails, or fails to terminate when the assumed structure (a return to the start state) never occurs."},
 {"id": "SP_09", "column": "domain", "name": "implementation_defect_in_a_sound_algorithm",
  "definition": "The chosen algorithm is correct and within bounds, but its realisation in code corrupts a value or state or is too slow in practice: an alias where a copy was needed, an assignment in the wrong direction, an incompletely composed mapping, floating point where exact integers are required, a modular reduction before a comparison, a type mismatch at a boundary, or constant-factor overhead inside an in-bound enumeration.",
  "when_to_use": "Use when the trace's stated method would give the right answer if transcribed faithfully, and the failure is located in how one statement realises it -- the wrong object mutated, the wrong side of an assignment, a value reduced or converted before it is compared or joined, or work recreated inside a loop that did not need it.",
  "when_not_to_use": "Do not use for a single-unit boundary shift (SP_06), a wrong or missing predicate (SP_07), an asymptotically too-slow method (SP_02), or when the method itself is unsound (SP_08). Do not use for truncated or placeholder output (SP_01).",
  "consequence": "The program computes the right quantities by the right method but emits a corrupted value, crashes on a type error, or exceeds the time limit on large inputs despite an in-bound algorithm."},
 {"id": "SP_10", "column": "general", "name": "contradicting_check_dismissed",
  "definition": "The agent's own check -- a worked sample, a recomputation, or a stated invariant -- contradicts its result, and it proceeds unchanged by rationalising the contradiction away instead of revising.",
  "when_to_use": "Use when the trace contains an explicit check whose result disagrees with the agent's answer, followed by a justification for ignoring the disagreement (the sample might be wrong, the difference does not matter) and an unrevised submission.",
  "when_not_to_use": "Do not use when the agent never ran a check, or when it revised after the check. The defect the check would have caught is coded separately where it occurs.",
  "consequence": "A defect the agent had already detected reaches the submission; the failure is certain rather than latent, because the agent's own evidence showed it."},
]

# every uncovered point of pointjudge-1, by hand: (trace_id, point index) -> code
ASSIGN = {
 ("0171a0e72f1cfe5ab714be18", 0): "SP_08",  # two-pointer on unsorted data
 ("0fce685c900b3e35b4044fe9", 0): "SP_08",  # stack greedy for a matching problem
 ("1d2877affbe639df7df3adf5", 0): "SP_08",  # fixed adjacent pairing, no search
 ("406ea98309f1310d48240e34", 0): "SP_08",  # greedy rook placement
 ("56a3f3dd187e80c18a432497", 0): "SP_08",  # functional graph treated as permutation
 ("6949045f93f71383d84c24b0", 0): "SP_08",  # ternary search without unimodality
 ("7cb1fa44c3ff410faf5e70de", 0): "SP_08",  # greedy assignment
 ("8e399502f5711026dae0faa2", 0): "SP_08",  # operations assumed independent of the fixed S
 ("93f3f946d5dc82cfa3ddf884", 0): "SP_08",  # greedy max-difference contraction
 ("985d4fed55bf51a55e871391", 0): "SP_08",  # functional graph treated as permutation
 ("9acae4da9a1164e95390a82e", 0): "SP_08",  # symmetric union-find for a directional process
 ("c1a2b97bffc1359f6188e3c0", 0): "SP_08",  # assumed the orbit returns to the start state
 ("0e7bcc350efbde175d7c0e39", 0): "SP_09",  # assignment direction reversed
 ("125b9b919a9c5c591e68cc83", 0): "SP_09",  # mapping composition incomplete in one branch
 ("1486411b25198213263ee0ad", 0): "SP_09",  # alias instead of copy during DP update
 ("2734acdc9b6fe0eabfd93f54", 0): "SP_09",  # float division for exact integer comparison
 ("324ce104f8c0ba705cd1770e", 0): "SP_09",  # str.join over bytes
 ("73c0a1e62fe2b35cd70f19e0", 0): "SP_09",  # mapping update wrong scope
 ("a97a394842e0ae77ad51305e", 0): "SP_09",  # closures recreated per combination (constant factor)
 ("caeb99a2b79364f22b98d7bc", 2): "SP_09",  # modular reduction before min()
 ("be1673f3c6ed5573670cf34b", 1): "SP_10",  # rationalised away the contradicting sample
 ("8e399502f5711026dae0faa2", 2): "SP_01",  # complete program in <answer> tags, no fence: harness ran nothing
}

base = json.loads(BASE.read_text())
points = {}
for f in sorted((RUN / "traces").glob("*.json")):
    d = json.loads(f.read_text())
    for i, p in enumerate(d["points"]):
        if p["none_fits"]:
            points[(d["trace_id"], i)] = p
assert set(points) == set(ASSIGN), (set(points) ^ set(ASSIGN))
for c in NEW:
    c["evidence"] = [{"trace_id": t, "quote": points[(t, i)]["evidence"], "missing": None}   # the point's missing field holds the decider's gap note, not an absence
                     for (t, i), code in ASSIGN.items() if code == c["id"]]
tax = dict(base)
tax["codes"] = base["codes"] + NEW
tax["derives_from"] = {"taxonomy": "data/livecodebench/taxonomies/tax-1/taxonomy.json",
                       "operation": "add three hand-authored codes, all others byte-identical",
                       "grounding": str(RUN) + " uncovered points"}
tax["produced_by"] = "data/livecodebench/scripts/build_tax2.py"
tax["hand_added_note"] = ("SP_08, SP_09 and SP_10 were written by hand on 2026-09-11 from the 22 points pointjudge-1 "
                          "marked none_fits. Those points are grounding; rates under tax-2 are valid from a judge pass "
                          "run with tax-2 in view, or from the hand-assigned derived mapping pointjudge-1-tax2, which "
                          "must be cited as hand-assigned.")
tax["counts"] = {"codes": len(tax["codes"]), "general": sum(c["column"] == "general" for c in tax["codes"]),
                 "domain": sum(c["column"] == "domain" for c in tax["codes"])}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "taxonomy.json").write_text(json.dumps(tax, indent=2))
(OUT / "assignments.json").write_text(json.dumps([{"trace_id": t, "point": i, "code": c} for (t, i), c in ASSIGN.items()], indent=2))
(OUT / "provenance.json").write_text(json.dumps({
    "artifact": "tax-2", "benchmark": "livecodebench", "created": "2026-09-11",
    "derives_from": tax["derives_from"],
    "motivated_by": {"run": str(RUN), "uncovered_points": 22,
                     "of_which": {"SP_08": 12, "SP_09": 8, "SP_10": 1, "SP_01 (existing)": 1}},
    "hand_authored": ["SP_08", "SP_09", "SP_10"],
    "counts": tax["counts"],
    "rates_valid_from": "a judge pass with tax-2 in view; pointjudge-1-tax2 is a hand-assigned derived mapping"}, indent=2))
# byte-identity check on the carried codes
for a, b in zip(base["codes"], tax["codes"]):
    assert a == b
print("tax-2:", tax["counts"], "| carried codes byte-identical: yes")
