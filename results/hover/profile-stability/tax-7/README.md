# Failure-profile stability — 7 codes

M covers **375 distinct tasks**, 169–186 per candidate. If that exceeds the task set you filtered to, the output directory also holds traces from an earlier run over the same corpus; they are the same instrument on the same pool and are included deliberately.

12 candidates. N: 50–50 tasks per candidate. M: 169–186 tasks per candidate. Judge outputs only; no gold was read.

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
| FM_001 | DISALLOWED_QUERY_SYNTAX_OR_STYLE | 1.247 | +0.849 |
| FM_003 | MISSING_REQUIRED_OUTPUT_FIELD_OR_M | 0.510 | +0.871 |
| FM_006 | MALFORMED_STRUCTURED_LIST_OR_SORTI | 0.275 | +0.865 |
| FM_002 | UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJ | 0.197 | +0.232 |
| FM_004 | PREMATURE_RETRIEVAL_TERMINATION_OR | 0.138 | +0.677 |
| FM_005 | EVIDENCE_MISCONSTRUCTION_OR_LOGICA | 0.103 | -0.386 |
| FM_007 | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | 0.077 | +0.566 |

Whole-profile identity within N: 66.2% (chance 8.3%).

## 1. Per-code rates, N vs M

| code | name | rate on N | rate on M | ρ across candidates | mean abs diff | sampling floor (p95) | reliability on N |
|---|---|---:|---:|---:|---:|---:|---:|
| FM_001 | DISALLOWED_QUERY_SYNTAX_OR_STYLE | 1.247 | 1.257 | +0.865 | 0.072 | 0.160 | +0.849 |
| FM_002 | UNGROUNDED_ENTITY_OR_KNOWLEDGE_INJ | 0.197 | 0.185 | +0.539 | 0.036 | 0.140 | +0.232 |
| FM_003 | MISSING_REQUIRED_OUTPUT_FIELD_OR_M | 0.510 | 0.460 | +0.918 | 0.084 | 0.185 | +0.871 |
| FM_004 | PREMATURE_RETRIEVAL_TERMINATION_OR | 0.138 | 0.146 | +0.592 | 0.053 | 0.122 | +0.677 |
| FM_005 | EVIDENCE_MISCONSTRUCTION_OR_LOGICA | 0.103 | 0.158 | +0.276 | 0.076 | 0.150 | -0.386 |
| FM_006 | MALFORMED_STRUCTURED_LIST_OR_SORTI | 0.275 | 0.275 | +0.944 | 0.063 | 0.156 | +0.865 |
| FM_007 | CLAIM_CONSTRAINT_OMISSION_IN_QUERY | 0.077 | 0.091 | +0.648 | 0.029 | 0.109 | +0.566 |

⚠ marks a code whose N-vs-M gap exceeds what sampling alone explains.

## 2. Whole-profile shape

L1 distance between share vectors. Sampling floor: median 0.147, 95th percentile 0.286.

**11 of 12 candidates** sit inside the sampling floor.

| candidate | L1(N, M) | inside floor |
|---|---:|---|
| cand_00 | 0.230 | yes |
| cand_01 | 0.067 | yes |
| cand_02 | 0.117 | yes |
| cand_03 | 0.203 | yes |
| cand_04 | 0.149 | yes |
| cand_05 | 0.274 | yes |
| cand_06 | 0.139 | yes |
| cand_07 | 0.113 | yes |
| cand_08 | 0.301 | no |
| cand_09 | 0.136 | yes |
| cand_10 | 0.100 | yes |
| cand_11 | 0.165 | yes |

## 3. Identity: is a candidate's nearest M profile its own?

| | rate |
|---|---:|
| N profile finds its own candidate | **9/12 = 75.0%** |
| ceiling: a 50-task subsample of M finds its own | 96.2% |
| chance | 8.3% |

| candidate | nearest M profile | own distance | rank of own |
|---|---|---:|---:|
| cand_00 | cand_00 ✓ | 0.230 | 1 |
| cand_01 | cand_01 ✓ | 0.067 | 1 |
| cand_02 | cand_02 ✓ | 0.117 | 1 |
| cand_03 | cand_02 | 0.203 | 2 |
| cand_04 | cand_02 | 0.149 | 2 |
| cand_05 | cand_05 ✓ | 0.274 | 1 |
| cand_06 | cand_06 ✓ | 0.139 | 1 |
| cand_07 | cand_07 ✓ | 0.113 | 1 |
| cand_08 | cand_01 | 0.301 | 2 |
| cand_09 | cand_09 ✓ | 0.136 | 1 |
| cand_10 | cand_10 ✓ | 0.100 | 1 |
| cand_11 | cand_11 ✓ | 0.165 | 1 |

## 4. What carries the identity?

A signature resting on one frequent code is a thinner claim than one resting
on the shape. Single codes are scored by absolute rate difference: a one-code
*share* vector is always [1.0], which would make that row vacuous.

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
