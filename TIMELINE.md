# Timeline

Tracks experiments and changes to the methods/setup (scoring formulas,
judging machinery, instruments). Entries are dated; newest last.

---

## 2026-08-07 13:52 — Method entry: Ranking-Trust Functional Ψ (v0)

**Objects.** Benchmark **B ∈ ℬ**; scenario **S ∈ 𝒮**; taxonomy **𝒯**.
Every component maps into **[0, 1]**, 1 = oracle-grade.

```
Ψ : ℬ × 𝒮 → [0, 1]

Ψ(B, S) = f( Q_Judge(B), Q_Recovery(B), Q_Success(B), Q_TaskSet(B, S), Q_Taxonomy(B) )
```

**Axioms on f:** monotone non-decreasing in every argument; weakest-link
bounded — Ψ never exceeds its smallest argument; not a bare product of
components. f is scenario-dependent: which components dominate, and how
hard the weakest link binds, varies with S. Evidence volume is absent by
design (it belongs to score uncertainty, not machinery trust).

- **Q_Judge.** How accurately the judge identifies failure occurrences and
  codes them: surfacing every failure truly present in the trace,
  inventing none that aren't there, and assigning the correct taxonomy
  mode to what it finds.
- **Q_Recovery.** How accurately recovery is labeled at the occurrence
  level: genuine recoveries recognized, and nothing credited as recovered
  whose effect actually persisted.
- **Q_Success.** How accurately we determine whether a task failed,
  compared against gold.
- **Q_TaskSet.** How well the scored task set stands in for the target
  that scenario S declares: the scored tasks themselves (observed-set),
  the broader unseen task distribution (generalization), or repeated seed
  executions (cross-seed). Its failure-mode profile should be close to
  what that target would elicit, with balanced coverage of task types and
  difficulty.
- **Q_Taxonomy.** How fit the frozen vocabulary is for this benchmark: it
  covers every failure that actually occurs, its definitions are clear
  enough for consistent assignment, and its modes are relevant rather
  than dead weight.

*(𝒯 is used for the taxonomy object so τ stays free for Kendall's τ in
validation work.)*

---

## 2026-08-07 13:57 — Method entry: Candidate-Score Function Φ (v0)

**Objects.** Candidate **C ∈ 𝒞**; scenario **S ∈ 𝒮**. Φ pairs with Ψ:
Φ scores a candidate, Ψ says how much to trust the ranking Φ produces.

**General form:**

```
Φ : 𝒞 × 𝒮 → score

Φ(C, S) = g_S( Failures(C), Recoveries(C), Coverage(C), Uncertainty(C) )
```

- **Failures(C).** The observed failure occurrences and their properties —
  which modes, on which tasks, deduplicated per task.
- **Recoveries(C).** What happened after each failure: recovered fully,
  partially, or not at all.
- **Coverage(C).** Which tasks, traces, and seeds the evidence comes from.
- **Uncertainty(C).** How precise the resulting estimate is, given the
  evidence.

**Design principles.** The scoring range is a presentation choice and adds
no information; evidence volume must never directly raise or lower a
score — it affects normalization and Uncertainty only; scores are computed
independently per candidate (adding or removing another candidate cannot
move C's score), and the ranking is derived only after all scores exist.
**g_S** is scenario-specific — same measurements, different aggregation
per scenario.

**Initial concrete form (v0)** — for candidate **C** and failure mode
**m**, over the **N** evaluated tasks:

```
Affected(C, m)   = number of tasks on which mode m appeared (counted once per task)
Recovered(C, m)  = number of those tasks on which every occurrence of m was recovered

Prevalence(C, m)   = Affected(C, m) / N
RecoveryRate(C, m) = Recovered(C, m) / Affected(C, m)

Influence(C, m) = Weight(m) · Prevalence(C, m) · discount^RecoveryRate(C, m)

Φ(C) = 100 − Σₘ Influence(C, m)
```

- **Affected / Recovered** — raw task counts: how broadly a mode strikes,
  and on how many of those tasks the candidate fully cleaned it up.
- **Prevalence** — the share of evaluated tasks a mode touches.
- **RecoveryRate** — the share of affected tasks where recovery was
  complete.
- **Influence** — the burden a mode contributes to the score: grows with
  prevalence, shrinks (never to zero) as recovery becomes consistent.
- **Weight(m)** — a mode's maximum penalty; starts equal at 100/K over the
  K frozen taxonomy modes (Weight ≥ 0, Σ Weight = 100).
- **discount ∈ (0, 1)** — strength of the recovery reduction; tuned on the
  development split, then frozen.

A score of 100 means no failure burden was observed under the frozen
taxonomy and available traces — not certified perfection.

**Deliberately outside v0** (promotable later as dated method changes):
partial recovery per task; mode co-occurrence relations; authored
superseding rules; appearance-variance coefficients from equal training
splits; within-task occurrence counts; trace position;
persistence/propagation; task difficulty; repeated seeds; trace-length
differences.

---

## 2026-08-07 14:04 — Setup entry: Initial instrument binding (v0)

All measurement roles are filled by the AdaMAST pipeline initially:
judge/annotator = AdaMAST two-pass taxonomy-conditioned annotator;
recovery analysis = AdaMAST pipeline; taxonomy generation/refinement =
AdaMAST pipeline (𝒯 frozen before evaluation traces are analyzed; K
determined at freeze). Instruments are replaceable by design — any swap
is a future dated setup entry. Functions Ψ and Φ are unchanged by this
binding; it only sets where their inputs come from.

---

## 2026-08-07 16:57 — Method entry: Candidate-Score Function Φ (v0.1) — task-first saturating aggregation

Supersedes the v0 concrete form (2026-08-07 13:57 entry); the general form
Φ(C, S) = g_S(Failures, Recoveries, Coverage, Uncertainty), all its design
principles, and Ψ are unchanged. The v0 entry remains in the ledger as the
historical record.

**Motivation.** v0 sums per-mode Influence, so a task where modes A and B
both appear unrecovered is charged twice, without bound; and concentration
is invisible — a candidate with A+B on the same 10 tasks scores identically
to one with the same failures spread over 20 tasks. v0.1 reorders the
aggregation task-first and saturates per-task burden, so co-occurring modes
add burden with diminishing returns and a task can never cost more than
"fully failed". Causal explanations of co-occurrence are deliberately not
modeled (see PARKING.md 2026-08-07).

**Inputs.** Candidate C; N evaluated tasks; frozen taxonomy of K modes;
M_t = deduplicated set of modes appearing on task t; per (t, m) a flag:
did every occurrence of m on t recover. Frozen constants: per-mode weight
w_m ∈ (0, 1] (equal default w₀), discount δ ∈ (0, 1).

```
Step 1 — per-mode rates (unchanged from v0):
  Affected(m)  = #{ t : m ∈ M_t }           Prevalence(m) = Affected(m) / N
  Recovered(m) = #{ t : m ∈ M_t, every occurrence of m on t recovered }
  rr(m)        = Recovered(m) / Affected(m)

Step 2 — per-mode unit charge:
  q_m = w_m · δ^rr(m)

Step 3 — per-task burden (noisy-OR saturation):
  b_t = 1 − Π_{m ∈ M_t} (1 − q_m)           (empty M_t ⇒ b_t = 0)

Step 4 — candidate score:
  Φ(C) = 100 · (1 − (1/N) · Σ_t b_t)

Step 5 — per-mode Influence profile (not needed for the scalar):
  Influence(m) = (100/N) · Σ_t φ_{t,m}, where φ_{t,m} is the Shapley value
  of m in the game v_t(T) = 1 − Π_{j ∈ T} (1 − q_j) over T ⊆ M_t, computed
  by exact enumeration (|M_t| is small). Efficiency of the Shapley value
  gives Φ(C) = 100 − Σ_m Influence(m) — profile and scalar cannot disagree.
  Two-mode closed form: φ_A = q_A · (1 − q_B/2), φ_B = q_B · (1 − q_A/2).
```

**Decisions frozen with this entry.**
- v0's Σ Weight = 100 budget is dropped: saturation now bounds the score.
  w_m is a per-task severity cap in (0, 1]; the equal default w₀ becomes a
  real hyperparameter (it sets saturation speed) and joins δ as a constant
  tuned on the development split, then frozen (grids TBD at E001 setup).
- Recovery enters at the mode level: q_m uses rr(m) uniformly across m's
  affected tasks, so v0.1 consumes exactly the two per-mode measurements
  (appearance rate, full recovery rate) plus the per-task mode sets.
  Per-task binary recovery (unrecovered → w_m, recovered → w_m·δ) was
  considered and set aside — it changes what is measured.

**Properties.** Deterministic over the annotations; per-candidate
independent; N enters only as normalization; reduces to v0's ordering when
no task carries two modes; the scalar needs Steps 1–4 only; the scoring
range remains a presentation choice.

**Deliberately outside v0.1** (in addition to everything outside v0):
causal relations between failure modes — the root/middle/leaf
position-charging package parked 2026-08-07 in PARKING.md.

---

## 2026-08-07 17:03 — Setup entry: from-zero amendment — legacy HoVer shakedown artifacts imported as test data

**Amendment, approved by Andrei.** The from-zero rule (CLAUDE.md) is
amended: shakedown-era judge/recovery/scoring outputs from the pre-reset
workspaces are imported as provenance-tracked test data for
formula/integration prototyping only.

**What was imported → `data/legacy-hover-shakedown/` (read-only after
import, `chmod -R a-w`):**
- `~/Desktop/GEPA_Experiments/grading/`: annotations_pilot (20 traces,
  taxonomy v2), annotations_pilot_mast (2 traces, MAST),
  annotations_v3 (596 traces, 12 candidates, taxonomy v3),
  refinement_slice (incl. quarantined `gold_do_not_pass_to_judge/`),
  evaluation_subset.json (50-task common subset, gold not consulted),
  taxonomy/ (full version ladder + freeze records).
- `~/Desktop/certification_analysis/`: README.md (defines the
  effect-inclusive recovery semantics), examples/, and the
  hover_gepa_baseline README (documents the 12-candidate GEPA pool) —
  interpretive artifacts only; no code, caches, or venvs.

Per-item provenance and caveats: `data/SOURCES.md`. Binding restriction:
this data is usable ONLY in `trials/` for prototyping Φ/Ψ machinery —
never as claims-bearing evidence; official experiments still require
fresh data under their own TIMELINE entries. Hard rule 3 stands: nothing
in any scoring path reads `gold_do_not_pass_to_judge/`.

---

## 2026-08-07 17:46 — Setup entry: taxonomy regeneration run launched (AdaMAST protocol, prototyping-grade)

**Launched by Andrei** from `trials/2026-08-07-adamast-taxonomy-regen/`:
`adamast generate` — the agreement-gated AdaMAST protocol (default κ
target and coverage floor, early stop) — over 60 converted legacy HoVer
traces: 5 per candidate × 12 candidates, repeat 0, drawn only from
held-out tasks **outside** the 50-task scored subset (freeze discipline:
generation sees no trace Φ scores). Provider: Bedrock; model:
`us.anthropic.claude-sonnet-4-5-20250929-v1:0` (pinned to the legacy
judge model for comparability). Output:
`trials/2026-08-07-adamast-taxonomy-regen/taxonomy_regen_v0/`.

**Motivation.** The 2026-08-07 dissection of candidates 002/008/009: the
shakedown v3 taxonomy's high-prevalence B codes are style/protocol
violations structurally unable to affect HoVer's doc-retrieval gold
(e.g. B.3 at 80% gold-pass on affected tasks), while the C-only Φ beat
the full taxonomy on generalization (+0.29 vs +0.20 τ against gold-300).
Instrument re-binding only — Ψ and Φ are unchanged by this entry.

**Restriction.** Built from amendment-imported shakedown traces ⇒
prototyping-grade; the official E001 taxonomy must be frozen on E001's
own trace source under its own entry.
