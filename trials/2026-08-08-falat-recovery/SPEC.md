# FALAT-derived Recovery Instrument — Spec (v0 draft)

Gold-free adaptation of FALAT (arXiv 2606.00765) as the Stage-2 recovery
analyzer. Boundary compliance: the LLM asserts only local, falsifiable
edge claims; every recovery verdict is deterministic graph computation.
Instrument-binding change only — Ψ and Φ untouched. Trials-grade until a
dated TIMELINE binding entry adopts it.

## Position in the pipeline

Stage 1 (unchanged): the judge, under the frozen taxonomy
(`tax-20260808T184241Z-8598f86e-11ef4f`), emits failure points with step
anchors. Stage 2 (this instrument) consumes the trace + Stage-1 failure
points and emits per-occurrence recovery labels and causal positions.

## What FALAT keeps / loses in the adaptation

Kept: Phase-1 hierarchical trace representation (windowing is trivial at
our ~10-step traces); Phase-2 **typed dependency edges** with FALAT's
six-label vocabulary. Dropped: Phase 3–4 decisive-step search and
counterfactual ranking (needs the gold expected output o*; also the
low-accuracy part). Replaced: "would correcting recover o*" → "does the
occurrence's effect reach the final output?", computed on the graph.

## LLM stages (2 calls/trace, Bedrock, same judge model)

1. **Spec-only prior + abstraction** — task spec and program definition
   only (never a reference answer): expected flow, role boundaries, and
   a step-indexed summary of the trace. One call.
2. **Edge typing** — given the abstraction, the Stage-1 failure points,
   and a terminal OUTPUT node: for each ordered pair (failure point i,
   later failure point j) and each (failure point i, OUTPUT), assert at
   most one label from
   `follow_up | redundancy | no_influence | error_shift | correction |
   dead_end`, each with quoted trace evidence and the consuming step
   index. Every failure point MUST be closed out: either a path of
   influence toward OUTPUT, or an explicit correction / dead_end /
   no_influence closure. One call, JSON out.

## Deterministic recovery rules (recovery_graph.py)

- **Influence edges**: `follow_up` and `error_shift` propagate an
  occurrence's effect; `redundancy`, `no_influence`, `dead_end` do not.
- **Liveness**: influence edge (a→b) is LIVE iff a has no `correction`
  edge (a→c) with c.step < b.step — a correction only voids influence
  not yet consumed when the fix landed.
- **Verdict**: occurrence u is **PERSISTED** iff a live influence path
  reaches OUTPUT; otherwise **RECOVERED** (covers corrected-in-time,
  dead-ended, and non-propagating occurrences). Effect-inclusive by
  construction — matches IDEA.md Stage 2.
- **Unlinked occurrences** (judge asserted no edges despite the closure
  requirement): policy flag `default_when_unlinked`, default
  `persisted` (conservative, matches v0 strictness).
- **Positions** (computed for diagnostics and for the parked
  causal-position package; NOT consumed by Φ v0.1): on the live
  influence subgraph among persisted occurrences — root / middle /
  leaf / isolated, plus σ = l/(r+l) per the PARKING.md 2026-08-07
  entry. Promotion of σ into scoring remains a future TIMELINE decision.

## Φ input mapping

Per (task, mode): fully recovered iff EVERY occurrence of that mode on
the task is RECOVERED — drops into the existing harness as
recovery_status ∈ {fully_recovered, unrecovered}. K = 17 under the
frozen taxonomy.

## Error surface (Ψ)

Q_Recovery becomes edge accuracy: wrong labels, missed edges, wrong
consuming-step indices. Measurable on an oracle slice (hand-labeled
edges; optionally a small Causal Agent Replay arm). The closure
requirement makes silent omissions detectable (unlinked occurrences are
counted and reported).

## Validation plan (in order)

1. Unit tests on the deterministic core (this trial, offline).
2. Edge-typing dry run on the 24-trace refinement slice (billed, ~$2–5).
3. Full Stage-2 pass over the subset re-judge output; agreement analysis
   vs the legacy judge's recovery_status; disagreements hand-inspected.
4. If adopted: dated TIMELINE instrument re-binding entry.
