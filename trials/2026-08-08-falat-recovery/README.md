# Trial: falat-recovery (2026-08-08)

**Hypothesis.** FALAT's dependency-guided attribution (arXiv 2606.00765)
can serve as the Stage-2 recovery instrument in a gold-free form: keep
its Phase-1 trace abstraction and Phase-2 typed dependency edges, drop
the gold-dependent decisive-step search (Phases 3–4), and compute
recovery deterministically as live-influence reachability to the final
output. This replaces the legacy judge's holistic recovery_status with
local falsifiable edge claims + deterministic verdicts — a strict
boundary-2 upgrade — and revives the parked causal-position package for
free (same graph).

**Setup.** [SPEC.md](SPEC.md) — the full design: two LLM calls per trace
(spec-only prior/abstraction; edge typing with a closure requirement),
FALAT's six-label edge vocabulary, the liveness rule (a correction voids
only influence not yet consumed), verdict rule (persisted iff a live
influence path reaches OUTPUT), unlinked-occurrence policy, Φ input
mapping, and the Q_Recovery error surface.
[recovery_graph.py](recovery_graph.py) — the deterministic core
(stdlib only): verdicts, root/middle/leaf/isolated positions, and
σ = l/(r+l) (computed for diagnostics and the parked package; not
consumed by Φ v0.1).

**Result — offline build complete, nothing billed yet.**

- **Deterministic core** (`recovery_graph.py`): 10/10 unit tests pass —
  chain persistence, correction-before vs correction-after consumption,
  dead-end neutralization, redundancy/no_influence non-propagation,
  error_shift propagation, unlinked-occurrence policy, σ on chains,
  step-ordering validation, and the per-(task,mode) AND mapping (a mode
  is fully_recovered only if EVERY occurrence recovered).
- **Traces converted** (`convert_pipeline_traces.py`, reusing the
  generation trial's converter with explicit RETRIEVAL EVENT
  rendering): `slice_traces/` 24 dry-run traces; `scored_traces/` 600
  scored-subset executions (50 tasks × 12 candidates, repeat 0),
  asserted counts, gold quarantine enforced in code. ~49KB/trace.
- **Prompts** (`prompts/`): `prior.txt` (program-level expectation,
  spec only — cached once, no reference answer) and `edges.txt`
  (occurrence enumeration → typed edges, with the closure requirement).
- **Runner** (`runner.py`): builds prompts, verifies every quote against
  the numbered trace (exact then fuzzy ≥0.6), counts unlocated findings
  and unverified occurrences as Q_Recovery diagnostics, invokes the
  graph, and emits per-(task,mode) recovery for the Φ harness.
  `--build-only` exercises the whole path with zero API calls; smoke
  test confirms correct step anchoring.

**Conclusion.** PENDING — awaiting the billed Stage-1 re-judge and the
Stage-2 edge-typing runs (commands prepared for Andrei).
