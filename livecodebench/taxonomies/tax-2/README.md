# tax-2 — tax-1 plus three hand-authored codes

**tax-1 plus `SP_08`, `SP_09`, `SP_10`; the seven tax-1 codes are byte-identical.** So a
tax-1 rate and a tax-2 rate for `SP_01`–`SP_07` mean the same thing, and any movement is
attributable to the new codes absorbing points that previously fit nothing.

Written by hand on 2026-09-11 from the 22 points `pointjudge-1` (tax-1, 450 traces of
`judging-50-1`) marked `none_fits`. Not induced by `new_pipeline`; disclosed as such.

| id | column | name | grounding points |
|---|---|---|---|
| `SP_08` | domain | `unsound_algorithmic_strategy_or_structural_premise` | 12 — greedy where exact search is required (×5), functional graph treated as a permutation (×2), assumed return to the start state, ternary search without unimodality, two-pointer on unsorted data, symmetric union-find for a directional process, operations assumed independent of the fixed string |
| `SP_09` | domain | `implementation_defect_in_a_sound_algorithm` | 8 — alias instead of copy, assignment direction reversed, mapping composition wrong (×2), float for exact integers, modular reduction before `min`, `str.join` over bytes, closures recreated per iteration |
| `SP_10` | general | `contradicting_check_dismissed` | 1 — the sample disagreed with the answer and the agent argued the sample might be suboptimal |

The 22nd point — a complete program wrapped in `<answer>` tags with no backtick fence —
was assigned to the existing `SP_01`: its consequence is exactly SP_01's (the harness
receives nothing executable). SP_01's text was not changed; this is recorded as a
judgment call in `assignments.json`.

## Boundaries that carry the weight

`SP_08` vs `SP_04`: SP_04 explicitly excludes "incorrect greedy heuristics"; SP_08 is
where they go. `SP_08` vs `SP_03`/`SP_05`/`SP_06`/`SP_07`: those fire on one step of a
sound method; SP_08 requires the method itself to be wrong for the problem's structure.
`SP_09` is the residual "right method, wrong code" family and is bounded against the two
specific implementation codes (`SP_06` boundary shifts, `SP_07` predicates), which take
precedence. It is broad by construction — eight distinct mechanisms — and should be split
when a judge pass with it in view supplies enough occurrences to see which of them recur.
`SP_10` has one grounding point and no rate yet; it is included because the mechanism is
general (a check that contradicts the answer, ignored) and a judge with it in view is
expected to find more of it than a judge without.

## What must not be done with the grounding points

The 22 points are grounding, not occurrences. `pointjudge-1-tax2` is the derived mapping in
which they carry these codes **by hand assignment**, made so experiments can run before a
re-judge; it must be cited as hand-assigned. Rates comparable to a tax-1 judge pass come
from a judge pass with tax-2 in view.

Built by `scripts/build_tax2.py`, which also writes `assignments.json` (every uncovered
point → code) and asserts the carried codes are byte-identical.
