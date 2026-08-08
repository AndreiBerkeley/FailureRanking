# Trial: legacy-hover-phi-harness (2026-08-07)

**Hypothesis.** The legacy HoVer shakedown annotations
(`data/legacy-hover-shakedown/`, prototyping-only per data/SOURCES.md) can
be loaded into the Φ input representation, and Φ v0 vs Φ v0.1
(TIMELINE.md 2026-08-07 13:57 / 16:57) will produce mostly-consistent but
not identical rankings, with disagreements concentrated where mode
co-occurrence differs between candidates.

**Setup.** `phi_harness.py` (stdlib only): loads one annotation run
(candidate folders of per-trace JSONs) into per-candidate
`{task: {mode: [recovery_status,...]}}`, restricts to the 50-task
evaluation subset when given, and scores every candidate with v0 and v0.1
side by side. Placeholder hyperparameters δ = 0.5, w₀ = 0.5 (no grids yet).

Loader policy (explicit, flag-controlled):
- Mode presence: **primary** taxonomy mappings only by default
  (`--include-secondary` to add secondary).
- Full recovery per (task, mode): every contributing failure point has
  status in {fully_recovered, made_irrelevant}. Statuses unrecovered,
  partially_recovered, unclear, and not_applicable count as not fully
  recovered by default; `--na-policy {unrecovered,recovered,exclude}`
  controls the 330 not_applicable cases.
- Gold safety: any path containing `gold_do_not_pass_to_judge` raises;
  the harness never touches `refinement_slice/`.

Verification: `--self-test` reproduces the worked example frozen in the
2026-08-07 discussion (Φ = 62.70, Influence A = 27.28 / B = 10.02), checks
the two-mode Shapley closed form against the O(n²) elementary-symmetric
implementation, asserts Shapley efficiency (Σφ = b_t) on every task of
every real run, and confirms v0/v0.1 rank agreement on co-occurrence-free
synthetic data. All pass.

**Result** (annotations_v3, 12 candidates × 50 common tasks, K = 21,
defaults; full tables in `results/`):

- Every candidate has all 50 subset tasks annotated (n_tasks = 50, none
  missing).
- Co-occurrence is pervasive: mean modes/task 1.26–2.00 per candidate,
  max 5 modes on a single task — the double-counting scenario Φ v0.1
  targets is the *normal case* in this data, not an edge case.
- v0 vs v0.1: Kendall τ-a = 0.939. Both agree on the top candidate
  (candidate_008) and the bottom two (006, 007). Disagreement cluster:
  candidate_011 (mean 1.76 modes/task) rises 7 → 5 under v0.1 while 000
  and 009 each drop one place — saturation credits concentrated failures,
  the C1/C2 effect on real distributions.
- Score spread: v0 compresses 12 candidates into 90.9–94.2; v0.1 spreads
  them across 36.9–60.6 at the same δ — much larger dynamic range at
  these placeholder hyperparameters.
- Sensitivity: τ-a = 0.879 with `--na-policy exclude`; 0.788 with
  secondary mappings included (more co-occurrence ⇒ formulas diverge
  more); pilot run (K = 19, 20 traces — noise-level volume) τ-a = 0.833.

**Conclusion.** Loading works and the harness is reusable for future Φ
variants (one function per variant, shared loader/report). v0.1 behaves
as designed on real distributions: same broad ordering as v0, principled
divergence exactly where co-occurrence concentration differs. The
not_applicable recovery status (330 failure points) and
primary-vs-secondary mapping choice are the two loader decisions that
visibly move rankings — both must be settled (with Andrei) before any
run that matters. Nothing here is claims-bearing: shakedown-era judge,
taxonomy, and placeholder hyperparameters throughout.
