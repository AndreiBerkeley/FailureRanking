# Parking — Untested Methods & Ideas

Anything we can't pursue on the spot but must not lose: untested methods,
formula variants, instrument alternatives, experiment ideas, hunches.
One entry per item: date added · the idea in enough detail to reconstruct
it cold · why it's parked · status (`parked` / `promoted → <where>` /
`discarded (reason)`). Nothing here is committed-to; promotion happens via
TIMELINE.md when an idea becomes an actual method change or experiment.

---

## 2026-08-07 — Causal-position charging for co-occurring failure modes

**Status:** parked.

**Context.** Discussed 2026-08-07 (Andrei + Claude) as a candidate answer to
the co-occurrence double-counting problem in Φ (modes A and B both
unrecovered on one task each charge in full). Andrei's decision: adopt the
simpler Φ v0.1 (task-first saturating aggregation + Shapley profile
allocation, no causal machinery) first; park this package for a future
stage. It never entered TIMELINE.md — recorded here directly from the
discussion.

**The package (three linked pieces):**

1. **Reformulated measurement layer.** Per mode: (1) appearance rate,
   (2) full recovery rate, (3) causal relations between modes — with Φ a
   function of this per-mode measurement structure rather than a bare
   additive sum over modes.
2. **Case reduction (Andrei).** For mode X on a task: if X fully recovered,
   ignore causal relations entirely. If unrecovered, classify X's position
   in its causal connected component: isolated / root / middle / leaf.
3. **Position-severity charging.** Per task, build the causal graph over
   *unrecovered occurrences only*; each edge is a judge-asserted, locally
   falsifiable micro-claim ("occurrence of Y at step t consumed the
   corrupted output of X at step s") — time-ordering keeps the occurrence
   graph acyclic, and positions fall out of deterministic graph computation
   (verdict boundary intact). With r = distance to nearest root and
   l = distance to farthest leaf:

       σ(X) = l / (r + l)     root or isolated: σ = 1 · leaf: σ = 0 · middle: interpolated

   Charging semantics (Andrei): root = full fault; middle = closer to the
   root ⇒ more severe; leaf = treated as actually recovered. Integration:
   per-task recovery credit c_t = 1 if fully recovered, else
   1 − max σ over the mode's unrecovered occurrences on t; mode level keeps
   appearance rate raw and generalizes full-recovery rate to mean recovery
   credit. Degenerates exactly to the v0 measurements when no edges are
   asserted (every unrecovered occurrence is isolated ⇒ σ = 1 ⇒ credit 0).

**Caveats recorded at parking time:**
- Leaf-as-recovered is sound only under effect-inclusive recovery semantics
  (IDEA.md Stage 2 reads that way) or an explicit no-evaporation rule (the
  charge falls to the nearest unrecovered node when all ancestors
  recovered). Must be settled before promotion.
- The recovery-credit column then measures *origination responsibility*,
  not presence; appearance rate retains presence. Profile readers must be
  told.
- Multi-root DAG conventions (nearest root / farthest leaf) were chosen for
  simplicity; revisit if real components aren't short chains.
- Requires a Stage-1/2 annotation-schema extension (edge micro-claims) and
  adds a new judge error surface (mis-asserted links) to Ψ's Q_Judge — the
  main cost behind the parking decision.

**Related methods surveyed the same day** (context for whoever revisits):
Shapley / average attributable fraction (Cox 1985; Eide & Gefeller 1995;
Land & Gefeller 1997) as the principled burden allocation; FALAT-style
dependency tracing as the natural edge instrument; noisy-OR (Kim & Pearl)
as the saturating combiner that Φ v0.1 adopted instead; CCF alpha/beta-
factor models, latent-class models (tension with boundary 1 — learning
latent factors ≈ building a taxonomy), BN structure learning, and SBFL —
all considered and set aside with reasons in the 2026-08-07 discussion.
