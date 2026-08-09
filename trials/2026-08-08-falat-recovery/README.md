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

**Stage-1 on the dry-run slice (24 traces, two runs).**
- Run 1 (`slice_stage1.json`, K = 17) exposed two taxonomy defects; both
  handled in the generation trial: the spec-conformant code dropped, and
  the two evidence-gap codes rewritten as per-evidence-gap decision
  tests. Codes renumbered flat.
- Run 2 (`slice_stage1_v2.json`, K = 16) — healthy profile: 14/16 codes
  fire, mean 3.8 findings/trace, no `none_apply`, and **no code
  over-fires** (max B.14 Query_Stagnation at 15/24 = 63%, vs 22/24 for
  the dropped code). B.15 and C.1 silent at this sample size.
- **Q_Judge datum (Ψ):** B.11 and A.12 co-fire on 4/24 traces and all
  four cite the *same* evidence gap, with B.11's own quoted evidence
  contradicting B.11's decision test (A.12 correct in 4/4). Decision
  (Andrei, 2026-08-08): **keep both codes, change nothing** — instrument
  imperfections are to be measured and accounted for, not engineered
  away. This 4/24 same-gap disagreement rate is the first recorded
  Q_Judge measurement for this instrument binding; re-measured at the
  600-trace re-judge.

**Note for launching Stage 2:** `runner.py` needs `boto3`, which is
present in the AdaMAST venv but not in the system python3 — invoke it
with `~/.local/share/uv/tools/adamast/bin/python`.

**Conclusion.** PENDING — awaiting the Stage-2 edge-typing dry run, then
the full 600-trace Stage-1 + Stage-2 pass.
