# Failure-profile stability — 7 codes (map-1 against map-2)

12 candidates. N = `map-1`: 50–50 judged tasks per candidate, 50 distinct. M = `map-2`: 169–186 judged tasks per candidate, 375 distinct. Judge outputs only; no gold was read.

Each candidate is profiled on its own judged tasks. The noise floor comes from 1,000 disjoint splits of each candidate's M tasks into 50 versus the rest: how far a profile moves between two non-overlapping task samples of the same candidate.

## 0. Which codes can be stable at all?

400 random half-splits of each candidate's N tasks (~25 vs ~25), both halves from the same pool. This is not transfer; it is the ceiling transfer could reach.

| code | name | rate/trace on N | half-split ρ |
|---|---|---:|---:|
| FM_001 | DISALLOWED_QUERY_SYNTAX_OR_STYLE | 1.247 | +0.848 |
| FM_003 | MISSING_REQUIRED_OUTPUT_FIELD_OR_M | 0.510 | +0.873 |
| FM_006 | MALFORMED_STRUCTURED_LIST_OR_SORTI | 0.275 | +0.861 |
| FM_002 | UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJ | 0.197 | +0.225 |
| FM_004 | PREMATURE_RETRIEVAL_TERMINATION_OR | 0.138 | +0.681 |
| FM_005 | EVIDENCE_MISCONSTRUCTION_OR_LOGICA | 0.103 | -0.368 |
| FM_007 | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | 0.077 | +0.558 |

Whole-profile identity within N: 66.2% (chance 8.3%).

## 1. Per-code rates, N vs M

| code | name | rate on N | rate on M | ρ across candidates | mean abs diff | sampling floor (p95) | reliability on N |
|---|---|---:|---:|---:|---:|---:|---:|
| FM_001 | DISALLOWED_QUERY_SYNTAX_OR_STYLE | 1.247 | 1.257 | +0.865 | 0.072 | 0.164 | +0.848 |
| FM_002 | UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJ | 0.197 | 0.185 | +0.539 | 0.036 | 0.139 | +0.225 |
| FM_003 | MISSING_REQUIRED_OUTPUT_FIELD_OR_M | 0.510 | 0.460 | +0.918 | 0.084 | 0.185 | +0.873 |
| FM_004 | PREMATURE_RETRIEVAL_TERMINATION_OR | 0.138 | 0.146 | +0.592 | 0.053 | 0.122 | +0.681 |
| FM_005 | EVIDENCE_MISCONSTRUCTION_OR_LOGICA | 0.103 | 0.158 | +0.276 | 0.076 | 0.157 | -0.368 |
| FM_006 | MALFORMED_STRUCTURED_LIST_OR_SORTI | 0.275 | 0.275 | +0.944 | 0.063 | 0.156 | +0.861 |
| FM_007 | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | 0.077 | 0.091 | +0.648 | 0.029 | 0.108 | +0.558 |

⚠ marks a code whose N-vs-M gap exceeds what sampling alone explains.

## 2. Whole-profile shape

L1 distance between share vectors. Sampling floor: median 0.148, 95th percentile 0.291.

**11 of 12 candidates** sit inside the sampling floor.

| candidate | L1(N, M) | inside floor |
|---|---:|---|
| cand-019 | 0.274 | yes |
| cand-020 | 0.301 | no |
| cand-012 | 0.149 | yes |
| cand-033 | 0.100 | yes |
| cand-016 | 0.067 | yes |
| cand-008 | 0.139 | yes |
| cand-014 | 0.203 | yes |
| cand-039 | 0.165 | yes |
| cand-015 | 0.117 | yes |
| cand-011 | 0.113 | yes |
| cand-026 | 0.136 | yes |
| cand-004 | 0.230 | yes |

## 3. Identity: is a candidate's nearest M profile its own?

| | rate |
|---|---:|
| N profile finds its own candidate | **9/12 = 75.0%** |
| ceiling: a 50-task subsample of M finds its own | 96.5% |
| chance | 8.3% |

| candidate | nearest M profile | own distance | rank of own |
|---|---|---:|---:|
| cand-019 | cand-019 ✓ | 0.274 | 1 |
| cand-020 | cand-016 | 0.301 | 2 |
| cand-012 | cand-015 | 0.149 | 2 |
| cand-033 | cand-033 ✓ | 0.100 | 1 |
| cand-016 | cand-016 ✓ | 0.067 | 1 |
| cand-008 | cand-008 ✓ | 0.139 | 1 |
| cand-014 | cand-015 | 0.203 | 2 |
| cand-039 | cand-039 ✓ | 0.165 | 1 |
| cand-015 | cand-015 ✓ | 0.117 | 1 |
| cand-011 | cand-011 ✓ | 0.113 | 1 |
| cand-026 | cand-026 ✓ | 0.136 | 1 |
| cand-004 | cand-004 ✓ | 0.230 | 1 |

## 4. What carries the identity?

| profile | identity |
|---|---:|
| all 7 codes, absolute rates | 100.0% |
| all 7 codes, shares only | 75.0% |
| FM_001 alone (most frequent, 1.25/trace) | 8.3% |
| without FM_001, absolute | 91.7% |
| without FM_001, shares | 58.3% |
| chance | 8.3% |

Drop-one-code, shares:

| code dropped | identity |
|---|---:|
| FM_001 (DISALLOWED_QUERY_SYNTAX_OR_STY) | 58.3% |
| FM_007 (CLAIM_CONSTRAINT_OMISSION_IN_Q) | 58.3% |
| FM_002 (UNGROUNDED_ENTITY_OR_KNOWLEDGE) | 66.7% |
| FM_006 (MALFORMED_STRUCTURED_LIST_OR_S) | 66.7% |
| FM_003 (MISSING_REQUIRED_OUTPUT_FIELD_) | 75.0% |
| FM_004 (PREMATURE_RETRIEVAL_TERMINATIO) | 83.3% |
