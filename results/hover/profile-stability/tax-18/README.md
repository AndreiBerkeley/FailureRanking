# Failure-profile stability — 18 codes

M covers **394 distinct tasks**, 172–193 per candidate. If that exceeds the task set you filtered to, the output directory also holds traces from an earlier run over the same corpus; they are the same instrument on the same pool and are included deliberately.

12 candidates. N: 50–50 tasks per candidate. M: 172–193 tasks per candidate. Judge outputs only; no gold was read.

Each candidate is profiled on its own judged tasks, not on tasks judged for all
twelve — the corpus is hash-ordered, so a partial run has an empty all-twelve
intersection. The floor subsamples each candidate independently to match.

The noise floor comes from 1,000 disjoint splits of each candidate's M tasks into 50 versus the rest: that is how far a profile moves between two non-overlapping task samples of the same candidate.

## 0. Which codes can be stable at all?

400 random half-splits of each candidate's N tasks (~25 vs ~25), both halves from the same pool. This is not
transfer — it is the ceiling transfer could reach. A code that fails here has
no stability to lose.

| code | name | rate/trace on N | half-split ρ |
|---|---|---:|---:|
| SP_02 | DISALLOWED_QUERY_SYNTAX_OPERATORS | 1.007 | +0.837 |
| SP_01 | CONVERSATIONAL_OR_NATURAL_LANGUAGE | 0.382 | +0.912 |
| SP_07 | OMITTED_EVIDENCE_CATEGORIZATION_SE | 0.332 | +0.739 |
| SP_06 | MISSING_TERMINAL_COMPLETION_MARKER | 0.273 | +0.743 |
| SP_17 | MALFORMED_STRUCTURED_LIST_OR_SORTI | 0.263 | +0.770 |
| SP_03 | REASONING_PARAMETRIC_KNOWLEDGE_INJ | 0.193 | +0.326 |
| SP_15 | RETRIEVAL_STATE_AND_EVIDENCE_MISTR | 0.152 | +0.626 |
| SP_09 | PREMATURE_EVIDENCE_COMPLETION_IN_R | 0.120 | +0.303 |
| SP_18 | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | 0.092 | +0.832 |
| SP_05 | HALLUCINATED_RETRIEVED_DOCUMENT_AC | 0.088 | +0.892 |
| SP_10 | NULL_OR_TERMINATION_TOKEN_QUERY_EM | 0.073 | +0.606 |
| SP_08 | OMITTED_MULTI_HOP_REASONING_MAP | 0.045 | +0.790 |
| SP_13 | PASSAGE_TEXT_MISCONSTRUCTION_OR_HA | 0.045 | +0.207 |
| SP_16 | UNMAPPED_REASONING_TRAJECTORY | 0.045 | +0.790 |
| SP_14 | INVALID_VERDICT_LOGICAL_INFERENCE | 0.043 | +0.329 |
| SP_11 | CONVERSATIONAL_EXPLANATION_IN_QUER | 0.033 | +0.208 |
| SP_12 | FALSE_PREMISE_RULE_MISAPPLICATION_ | 0.033 | +0.632 |
| SP_04 | QUERY_SEARCH_TERM_INJECTION | 0.025 | +0.511 |

Whole-profile identity within N: 75.6% (chance 8.3%).

## 1. Per-code rates, N vs M

| code | name | rate on N | rate on M | ρ across candidates | mean abs diff | sampling floor (p95) | reliability on N |
|---|---|---:|---:|---:|---:|---:|---:|
| SP_01 | CONVERSATIONAL_OR_NATURAL_LANGUAGE | 0.382 | 0.382 | +0.949 | 0.029 | 0.196 | +0.912 |
| SP_02 | DISALLOWED_QUERY_SYNTAX_OPERATORS | 1.007 | 1.051 | +0.785 | 0.086 | 0.211 | +0.837 |
| SP_03 | REASONING_PARAMETRIC_KNOWLEDGE_INJ | 0.193 | 0.202 | +0.774 | 0.034 | 0.142 | +0.326 |
| SP_04 | QUERY_SEARCH_TERM_INJECTION | 0.025 | 0.025 | +0.570 | 0.018 | 0.053 | +0.511 |
| SP_05 | HALLUCINATED_RETRIEVED_DOCUMENT_AC | 0.088 | 0.050 | +0.968 | 0.038 | 0.078 | +0.892 |
| SP_06 | MISSING_TERMINAL_COMPLETION_MARKER | 0.273 | 0.234 | +0.891 | 0.062 | 0.145 | +0.743 |
| SP_07 | OMITTED_EVIDENCE_CATEGORIZATION_SE | 0.332 | 0.306 | +0.646 | 0.063 | 0.145 | +0.739 |
| SP_08 | OMITTED_MULTI_HOP_REASONING_MAP | 0.045 | 0.030 | +0.666 | 0.022 | 0.068 | +0.790 |
| SP_09 | PREMATURE_EVIDENCE_COMPLETION_IN_R | 0.120 | 0.123 | +0.710 | 0.028 | 0.114 | +0.303 |
| SP_10 | NULL_OR_TERMINATION_TOKEN_QUERY_EM | 0.073 | 0.072 | +0.682 | 0.030 | 0.088 | +0.606 |
| SP_11 | CONVERSATIONAL_EXPLANATION_IN_QUER | 0.033 | 0.046 | +0.154 | 0.026 | 0.070 | +0.208 |
| SP_12 | FALSE_PREMISE_RULE_MISAPPLICATION_ | 0.033 | 0.033 | +0.844 | 0.010 | 0.060 | +0.632 |
| SP_13 | PASSAGE_TEXT_MISCONSTRUCTION_OR_HA | 0.045 | 0.061 | +0.101 | 0.045 | 0.101 | +0.207 |
| SP_14 | INVALID_VERDICT_LOGICAL_INFERENCE | 0.043 | 0.070 | +0.529 | 0.043 | 0.105 | +0.329 |
| SP_15 | RETRIEVAL_STATE_AND_EVIDENCE_MISTR | 0.152 | 0.158 | +0.811 | 0.045 | 0.142 | +0.626 |
| SP_16 | UNMAPPED_REASONING_TRAJECTORY | 0.045 | 0.033 | +0.647 | 0.020 | 0.063 | +0.790 |
| SP_17 | MALFORMED_STRUCTURED_LIST_OR_SORTI | 0.263 | 0.291 | +0.891 | 0.059 | 0.163 | +0.770 |
| SP_18 | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | 0.092 | 0.093 | +0.781 | 0.033 | 0.109 | +0.832 |

⚠ marks a code whose N-vs-M gap exceeds what sampling alone explains.

## 2. Whole-profile shape

L1 distance between share vectors. Sampling floor: median 0.214, 95th percentile 0.351.

**12 of 12 candidates** sit inside the sampling floor.

| candidate | L1(N, M) | inside floor |
|---|---:|---|
| cand_00 | 0.309 | yes |
| cand_01 | 0.082 | yes |
| cand_02 | 0.150 | yes |
| cand_03 | 0.204 | yes |
| cand_04 | 0.255 | yes |
| cand_05 | 0.253 | yes |
| cand_06 | 0.265 | yes |
| cand_07 | 0.262 | yes |
| cand_08 | 0.317 | yes |
| cand_09 | 0.210 | yes |
| cand_10 | 0.138 | yes |
| cand_11 | 0.188 | yes |

## 3. Identity: is a candidate's nearest M profile its own?

| | rate |
|---|---:|
| N profile finds its own candidate | **12/12 = 100.0%** |
| ceiling: a 50-task subsample of M finds its own | 99.8% |
| chance | 8.3% |

| candidate | nearest M profile | own distance | rank of own |
|---|---|---:|---:|
| cand_00 | cand_00 ✓ | 0.309 | 1 |
| cand_01 | cand_01 ✓ | 0.082 | 1 |
| cand_02 | cand_02 ✓ | 0.150 | 1 |
| cand_03 | cand_03 ✓ | 0.204 | 1 |
| cand_04 | cand_04 ✓ | 0.255 | 1 |
| cand_05 | cand_05 ✓ | 0.253 | 1 |
| cand_06 | cand_06 ✓ | 0.265 | 1 |
| cand_07 | cand_07 ✓ | 0.262 | 1 |
| cand_08 | cand_08 ✓ | 0.317 | 1 |
| cand_09 | cand_09 ✓ | 0.210 | 1 |
| cand_10 | cand_10 ✓ | 0.138 | 1 |
| cand_11 | cand_11 ✓ | 0.188 | 1 |

## 4. What carries the identity?

A signature resting on one frequent code is a thinner claim than one resting
on the shape. Single codes are scored by absolute rate difference: a one-code
*share* vector is always [1.0], which would make that row vacuous.

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
