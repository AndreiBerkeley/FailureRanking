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

**Result.** Deterministic core implemented and fully tested: 10/10 unit
tests pass, covering chain persistence, correction-before vs
correction-after consumption, dead-end neutralization,
redundancy/no_influence non-propagation, error_shift propagation, the
unlinked-occurrence policy flag, σ values on chains, the per-(task,mode)
full-recovery mapping into the Φ harness format, and step-ordering
validation. LLM stages not yet run — prompts and runner are the next
work item; billed dry run planned on the 24-trace refinement slice
(SPEC.md validation plan step 2).

**Conclusion.** PENDING — awaiting the edge-typing dry run.
