# Failure-profile stability — 18 codes (map-3 against map-4)

12 candidates. N = `map-3`: 50–50 judged tasks per candidate, 50 distinct. M = `map-4`: 172–193 judged tasks per candidate, 394 distinct. Judge outputs only; no gold was read.

Each candidate is profiled on its own judged tasks. The noise floor comes from 1,000 disjoint splits of each candidate's M tasks into 50 versus the rest: how far a profile moves between two non-overlapping task samples of the same candidate.

## 0. Which codes can be stable at all?

400 random half-splits of each candidate's N tasks (~25 vs ~25), both halves from the same pool. This is not transfer; it is the ceiling transfer could reach.

| code | name | rate/trace on N | half-split ρ |
|---|---|---:|---:|
| SP_02 | DISALLOWED_QUERY_SYNTAX_OPERATORS | 1.007 | +0.830 |
| SP_01 | CONVERSATIONAL_OR_NATURAL_LANGUAGE | 0.382 | +0.909 |
| SP_07 | OMITTED_EVIDENCE_CATEGORIZATION_SE | 0.332 | +0.740 |
| SP_06 | MISSING_TERMINAL_COMPLETION_MARKER | 0.273 | +0.741 |
| SP_17 | MALFORMED_STRUCTURED_LIST_OR_SORTI | 0.263 | +0.758 |
| SP_03 | REASONING_PARAMETRIC_KNOWLEDGE_INJ | 0.193 | +0.328 |
| SP_15 | RETRIEVAL_STATE_AND_EVIDENCE_MISTR | 0.152 | +0.594 |
| SP_09 | PREMATURE_EVIDENCE_COMPLETION_IN_R | 0.120 | +0.304 |
| SP_18 | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | 0.092 | +0.815 |
| SP_05 | HALLUCINATED_RETRIEVED_DOCUMENT_AC | 0.088 | +0.886 |
| SP_10 | NULL_OR_TERMINATION_TOKEN_QUERY_EM | 0.073 | +0.594 |
| SP_08 | OMITTED_MULTI_HOP_REASONING_MAP | 0.045 | +0.790 |
| SP_13 | PASSAGE_TEXT_MISCONSTRUCTION_OR_HA | 0.045 | +0.231 |
| SP_16 | UNMAPPED_REASONING_TRAJECTORY | 0.045 | +0.790 |
| SP_14 | INVALID_VERDICT_LOGICAL_INFERENCE | 0.043 | +0.337 |
| SP_11 | CONVERSATIONAL_EXPLANATION_IN_QUER | 0.033 | +0.201 |
| SP_12 | FALSE_PREMISE_RULE_MISAPPLICATION_ | 0.033 | +0.632 |
| SP_04 | QUERY_SEARCH_TERM_INJECTION | 0.025 | +0.482 |

Whole-profile identity within N: 76.0% (chance 8.3%).

## 1. Per-code rates, N vs M

| code | name | rate on N | rate on M | ρ across candidates | mean abs diff | sampling floor (p95) | reliability on N |
|---|---|---:|---:|---:|---:|---:|---:|
| SP_01 | CONVERSATIONAL_OR_NATURAL_LANGUAGE | 0.382 | 0.382 | +0.949 | 0.029 | 0.196 | +0.909 |
| SP_02 | DISALLOWED_QUERY_SYNTAX_OPERATORS | 1.007 | 1.051 | +0.785 | 0.086 | 0.212 | +0.830 |
| SP_03 | REASONING_PARAMETRIC_KNOWLEDGE_INJ | 0.193 | 0.202 | +0.774 | 0.034 | 0.145 | +0.328 |
| SP_04 | QUERY_SEARCH_TERM_INJECTION | 0.025 | 0.025 | +0.570 | 0.018 | 0.058 | +0.482 |
| SP_05 | HALLUCINATED_RETRIEVED_DOCUMENT_AC | 0.088 | 0.050 | +0.968 | 0.038 | 0.078 | +0.886 |
| SP_06 | MISSING_TERMINAL_COMPLETION_MARKER | 0.273 | 0.234 | +0.891 | 0.062 | 0.145 | +0.741 |
| SP_07 | OMITTED_EVIDENCE_CATEGORIZATION_SE | 0.332 | 0.306 | +0.646 | 0.063 | 0.147 | +0.740 |
| SP_08 | OMITTED_MULTI_HOP_REASONING_MAP | 0.045 | 0.030 | +0.666 | 0.022 | 0.065 | +0.790 |
| SP_09 | PREMATURE_EVIDENCE_COMPLETION_IN_R | 0.120 | 0.123 | +0.710 | 0.028 | 0.121 | +0.304 |
| SP_10 | NULL_OR_TERMINATION_TOKEN_QUERY_EM | 0.073 | 0.072 | +0.682 | 0.030 | 0.087 | +0.594 |
| SP_11 | CONVERSATIONAL_EXPLANATION_IN_QUER | 0.033 | 0.046 | +0.154 | 0.026 | 0.071 | +0.201 |
| SP_12 | FALSE_PREMISE_RULE_MISAPPLICATION_ | 0.033 | 0.033 | +0.844 | 0.010 | 0.060 | +0.632 |
| SP_13 | PASSAGE_TEXT_MISCONSTRUCTION_OR_HA | 0.045 | 0.061 | +0.101 | 0.045 | 0.101 | +0.231 |
| SP_14 | INVALID_VERDICT_LOGICAL_INFERENCE | 0.043 | 0.070 | +0.529 | 0.043 | 0.105 | +0.337 |
| SP_15 | RETRIEVAL_STATE_AND_EVIDENCE_MISTR | 0.152 | 0.158 | +0.811 | 0.045 | 0.142 | +0.594 |
| SP_16 | UNMAPPED_REASONING_TRAJECTORY | 0.045 | 0.033 | +0.647 | 0.020 | 0.063 | +0.790 |
| SP_17 | MALFORMED_STRUCTURED_LIST_OR_SORTI | 0.263 | 0.291 | +0.891 | 0.059 | 0.165 | +0.758 |
| SP_18 | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | 0.092 | 0.093 | +0.781 | 0.033 | 0.109 | +0.815 |

⚠ marks a code whose N-vs-M gap exceeds what sampling alone explains.

## 2. Whole-profile shape

L1 distance between share vectors. Sampling floor: median 0.215, 95th percentile 0.349.

**12 of 12 candidates** sit inside the sampling floor.

| candidate | L1(N, M) | inside floor |
|---|---:|---|
| cand-019 | 0.253 | yes |
| cand-020 | 0.317 | yes |
| cand-012 | 0.255 | yes |
| cand-033 | 0.138 | yes |
| cand-016 | 0.082 | yes |
| cand-008 | 0.265 | yes |
| cand-014 | 0.204 | yes |
| cand-039 | 0.188 | yes |
| cand-015 | 0.150 | yes |
| cand-011 | 0.262 | yes |
| cand-026 | 0.210 | yes |
| cand-004 | 0.309 | yes |

## 3. Identity: is a candidate's nearest M profile its own?

| | rate |
|---|---:|
| N profile finds its own candidate | **12/12 = 100.0%** |
| ceiling: a 50-task subsample of M finds its own | 99.4% |
| chance | 8.3% |

| candidate | nearest M profile | own distance | rank of own |
|---|---|---:|---:|
| cand-019 | cand-019 ✓ | 0.253 | 1 |
| cand-020 | cand-020 ✓ | 0.317 | 1 |
| cand-012 | cand-012 ✓ | 0.255 | 1 |
| cand-033 | cand-033 ✓ | 0.138 | 1 |
| cand-016 | cand-016 ✓ | 0.082 | 1 |
| cand-008 | cand-008 ✓ | 0.265 | 1 |
| cand-014 | cand-014 ✓ | 0.204 | 1 |
| cand-039 | cand-039 ✓ | 0.188 | 1 |
| cand-015 | cand-015 ✓ | 0.150 | 1 |
| cand-011 | cand-011 ✓ | 0.262 | 1 |
| cand-026 | cand-026 ✓ | 0.210 | 1 |
| cand-004 | cand-004 ✓ | 0.309 | 1 |

## 4. What carries the identity?

| profile | identity |
|---|---:|
| all 18 codes, absolute rates | 91.7% |
| all 18 codes, shares only | 100.0% |
| SP_02 alone (most frequent, 1.01/trace) | 16.7% |
| without SP_02, absolute | 91.7% |
| without SP_02, shares | 83.3% |
| chance | 8.3% |

Drop-one-code, shares:

| code dropped | identity |
|---|---:|
| SP_02 (DISALLOWED_QUERY_SYNTAX_OPERAT) | 83.3% |
| SP_17 (MALFORMED_STRUCTURED_LIST_OR_S) | 91.7% |
| SP_01 (CONVERSATIONAL_OR_NATURAL_LANG) | 100.0% |
| SP_03 (REASONING_PARAMETRIC_KNOWLEDGE) | 100.0% |
| SP_04 (QUERY_SEARCH_TERM_INJECTION) | 100.0% |
| SP_05 (HALLUCINATED_RETRIEVED_DOCUMEN) | 100.0% |
