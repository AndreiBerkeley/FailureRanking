# check_ideas.md — ideas to check against the current model_ranking setup

Written 2026-09-16. Each idea below came out of reading two efficient-evaluation papers
(AutoJudger, arXiv:2505.21389; Factorized Active Querying / FAQ, arXiv:2601.20251) against
this branch. Neither paper's method applies here — both need gold on every queried task and
a large historical model×task matrix — but several of their components and habits of
thought do. Each idea is given with its status as decided, the reasoning, the step-by-step
procedure, and where it attaches in `methodology.md` (§ numbers refer to that file).

Status legend: **do** = agreed to run; **later** = keep as reference, not now;
**deferred** = explicitly not wanted for now; **dropped** = rejected.

Dropped and not described further: a low-rank factor model over the candidate×task×code
tensor (only useful for missing candidate–task pairs or cross-benchmark transfer; every
candidate here is judged on the same full set).

---

## 1. Uncertainty on every τ, and the ceiling any τ can reach — **do**

### Reasoning
Every number in `RESULTS.md` is a single Kendall τ with no interval. Two consequences.
First, a difference like amplitude +0.799 vs gold-50 +0.808 on the LCB draws cannot be
read as "level" or "behind" without knowing the spread of each. Second, the reference
itself is a finite sample: gold-gen on 755 (LCB) or 500 (HoVer) tasks is an estimate of the
candidates' true ordering, so there is a ceiling — the τ that *gold-gen agrees with itself*
across two halves — that no method, trace or gold, can exceed except by noise. On the
Aug-5 pipeline that ceiling was +0.394 with a 250-task reference; it has not been computed
for the current pools. Without it, "no method clears the bar" on HoVer and "gold pulls
ahead at 150" on LCB are both read against a bar whose own noise is unknown.

FAQ's habit that transfers: state the estimand (the ordering on the generalization pool),
treat the judged tasks as a sample of it, and report the sampling uncertainty.

### Procedure
1. **Bootstrap over judged tasks.** For a judged set of n tasks, draw n tasks *with
   replacement*, recompute every candidate's score under every method on the draw, rank,
   compute τ vs gold-gen. Repeat B = 1,000 times. Report the 2.5/97.5 percentiles for each
   method's τ and for gold-50's τ. Use the same draws for all methods so the intervals are
   paired; also report the interval on the *difference* (method τ − gold-50 τ), which is the
   quantity the bar comparison actually asks about.
2. **Pairwise separation.** From the same bootstrap, for each candidate pair (a, b) and
   method, the fraction of draws in which a outranks b. Pairs below (say) 0.9 are
   "not separated on this evidence" — this is the abstention mechanism, stated as a number.
3. **Reference ceiling.** Split the generalization pool into two random halves, compute τ
   between the two half-rankings, repeat over 200 random splits, report the mean. This is
   the ceiling for any τ against a reference of that size. Also compute it at the *judged*
   size (two disjoint draws of n from gold-gen) — that is the ceiling for gold-50 itself.
4. **Judge-noise term** is idea 2; until it is measured the intervals cover task-sampling
   only, and the tables should say so.

### Integration
- **§8 The measure.** Add three things to every results table: an interval column per τ,
  a `difference vs gold-50` interval, and one `reference ceiling` row per table.
- **Artifacts.** The bootstrap reuses the per-trace code sets the mapping already provides
  (§7: `codes(c,t)`, `codes(c,t,s)`), so nothing new is judged. The current draw machinery
  (`subsample_50.py` → `run_baselines.py --tasks split.json`) draws *without* replacement;
  a bootstrap needs duplicate tasks, so either `run_baselines.py` accepts per-task weights
  or the resampling is done directly on the exported code sets. Either is small.
- **§9 Judged sets.** Nothing changes; intervals are computed per judged set as listed.
- **Reading rule to add to `RESULTS.md`:** a method "clears the bar" only when the interval
  on (method τ − gold-50 τ) excludes zero; "level" when it does not; and no τ is compared
  to 1.0, only to the ceiling row.

---

## 2. Judge-rerun variance — **later**

### Reasoning
Idea 1 measures how much τ moves when the *tasks* change. It says nothing about how much
τ moves when the same traces are judged again. The two HoVer judge runs on the models set
(`pointjudge-1-sp15` on set a, `pointjudge-3` on set b) give incidence +0.750 vs +0.200 —
but they differ in tasks *and* judge pass, so the two sources are confounded. If judge
noise alone can move a method by ±0.3, the HoVer nulls and the LCB "level at 50" are
unidentifiable rather than negative, and the instrument, not the idea, is what the
results describe. This is the reason the LCB curve may plateau below gold at 150: a fixed
judge-noise floor that outcomes do not have.

### Procedure
1. Pick one judged set and one judge configuration (LCB `judging-50-1` under `pointjudge-2`
   is the cheapest: 450 traces, ≈ $21 per pass).
2. Re-run the full judge (§6: reader A, reader B, decider) R = 3–5 times on the identical
   traces. Temperature is 0 already, so vary what can be varied: reader order, seed where the
   endpoint exposes one, or the reader model (flash → pro) for one of the runs.
3. For each rerun, recompute every method's score per candidate and τ vs gold-gen.
4. Report (a) the spread of each candidate's amplitude/incidence across reruns, (b) the
   spread of τ across reruns with tasks fixed, (c) point-level agreement between reruns
   (fraction of failure points that reappear with the same code at the same step).
5. Compare (b) to the draw spread from idea 1: judge variance vs task variance, side by side.

### Integration
- **§6 The judge.** Record, per judge configuration, its rerun agreement (c) as an
  instrument property, next to the inter-annotator kappa the taxonomy gate already reports
  in §5 stage 8.
- **§8 The measure / §10 Runs and cost.** Add a `judge-rerun` row family alongside the
  `stability` (ten draws) rows, with its cost.
- **Idea 1** then folds the rerun spread into its intervals (task noise + judge noise).

---

## 3. Ranking agreement as a function of judged-set size — **do**

### Reasoning
The two LCB numbers that exist — level with gold-50 at n = 50, behind gold at n = 150
(+0.889 vs +0.941) — are two points on a curve. The shape between and beyond them is the
result: at what n the trace methods reach a given τ compared to outcomes (evidence per
task, purely relative), where the trace curve flattens (the minimum subset size), and
whether it flattens *below* gold (a noise floor, idea 2) or merely later. The same curve on
HoVer shows whether the nulls are flat at every n (instrument carries nothing) or rise
slowly (instrument carries little per task). Nothing here is an absolute score; every
point is a τ between two rankings.

### Procedure
1. For each judged pool with ≥ 100 judged tasks (LCB `judging-150` under `pointjudge-2`;
   HoVer models `both-100`; HoVer GEPA `both-100`), take k ∈ {10, 20, 30, 50, 75, 100, 150}
   as available.
2. For each k, D = 20 uniform draws without stratification (the current draw rule), each
   scored by every method and by gold-k, τ vs gold-gen.
3. Report per k: mean τ and the idea-1 interval for each method and for gold-k; the
   fraction of draws where each method beats gold-k; top-1 rate.
4. Read off: the smallest k at which each method's mean τ is within 0.05 of its k = 150
   value (plateau), and the largest k at which any trace method's mean τ ≥ gold-k's
   (crossover).

### Integration
- **§8 The measure, "Stability".** Currently one size (ten draws of 50). This generalises
  it to a size sweep; `subsample_50.py` already takes `--k` and `--draws`, so the sweep is
  a loop over k with the existing script and no new judging.
- **§9 Judged sets.** No new sets; the sweep draws from the judged pools that exist.
- **`RESULTS.md`.** One table per pool with k as rows; the current 50×10 tables become the
  k = 50 row of it.

---

## 4. Tiered judge with a correction on a random subset — **do (as an analysis)**

### Reasoning
FAQ's estimator separates *prediction* from *reference*: a cheap predictor covers every
item, an expensive reference is consulted on a random subset, and the final estimate is the
cheap mean plus the reweighted discrepancy observed on the subset. The estimate is unbiased
for what the reference would have said on every item, whatever the cheap predictor's
quality — a bad cheap tier only widens the interval. Here the reference is not gold: it is
the most expensive judge configuration, and the claim is "the ranking that judge would
produce on all judged tasks, at a fraction of its cost". This is the only form of
uncertainty-with-a-guarantee available without outcomes, and it also gives a principled
way to spend an opus/fable-class judge sparingly.

The current decider already costs about as much as the two readers (§10), so a saving
exists only if the cheap tier is genuinely cheap — readers-only, or a single flash pass —
and the expensive tier is the full three-model pass with a stronger decider.

### Procedure (retrospective first — no new expensive judging needed)
1. **Reference tier, already run:** `pointjudge-2` on LCB `judging-150` (readers +
   sonnet decider, all 150 tasks) serves as the expensive judge on every task.
2. **Cheap tier:** produce a cheap mapping on the same 150 tasks: readers only, no decider
   (points merged by evidence overlap with a fixed rule), or a single flash-class pass.
3. **Simulate the budget:** for each candidate, draw a uniform random subset S of size m
   (m = 15, 30, 50) from the 150 tasks; treat the reference tier's mapping on S as "the
   expensive judge was consulted there". Same S for all candidates.
4. **Corrected score**, per candidate and per method whose score is a per-task mean
   (amplitude, incidence, combinations, step-amp, containment all are): with per-task
   values v_cheap(c,t) on all 150 and v_exp(c,t) on S,

       v̂(c) = mean over all t of v_cheap(c,t)  +  mean over t ∈ S of [ v_exp(c,t) − v_cheap(c,t) ]

   This is the difference estimator; with S drawn uniformly it is unbiased for the
   reference tier's mean over all 150. Its standard error is
   sd(v_exp − v_cheap on S) / √m · √(1 − m/150); bootstrap S for the interval.
5. **Rank** candidates by v̂ and compare four rankings against gold-gen and against the
   reference tier's own full ranking: cheap-only on 150; expensive-only on S; corrected;
   reference on all 150. Repeat over 20 draws of S per m.
6. **Read off:** how close the corrected ranking gets to the reference ranking (τ between
   them) at each m, versus cheap-only and expensive-only — i.e. how much of the expensive
   judge's ranking is recoverable from m expensive reads plus 150 cheap ones.
7. **Extension, if step 6 is favourable:** a three-tier nest (flash on all, sonnet on a
   subset, opus/fable on a sub-subset), the same estimator applied twice; and a *live* run
   where the expensive tier is actually only executed on S.

### Integration
- **§6 The judge.** Two configurations are needed instead of one: the existing
  reader+decider (reference) and a declared cheap configuration. Both mappings live under
  `judge_traces/` as separate runs, as now.
- **§7 From mapping to ranking.** One new scoring entry, `corrected-<method>`, which reads
  *two* mappings and a subset file. It is the first formula in `methods/README.md` that
  reads more than one mapping; the difference-estimator form above is parameter-free
  (m is a budget, not a strength parameter), so it does not violate the "no parameter"
  rule of §7.
- **§8 The measure.** Add τ vs the reference tier's full ranking as a second target next to
  τ vs gold-gen, for this analysis only.
- **§10 Runs and cost.** Cost is one cheap pass over 150 (readers ≈ $39 already known for
  LCB; a single-flash pass far less). No new decider runs for the retrospective version.

---

## 5. Task stratification — **deferred**

Not wanted for now: no task separation of any kind in the draws. Recorded for completeness:
if it is ever revisited, strata come from existing metadata (§2: LCB difficulty and source;
HoVer hop structure), not from embedding clusters, and the only use is balancing random
draws (§9) and reporting per-stratum firing rates. Note that LCB `judging-50-1` is already
drawn within difficulty with easy under-weighted (§9), so one judged set is stratified today
while the ten-draw stability rows are not; the size sweep in idea 3 uses uniform draws only.

---

## 6. Holdout discipline for anything chosen after seeing τ — **do (as a rule)**

### Reasoning
Every decision taken *after* looking at τ against the reference fits the method to its
own test. The parameter-free formulas (§7) and the task-disjoint pools (§1) already prevent
nearly all of this. Two places it touches the branch today: (a) five of eleven baselines
are reported and the rest set aside as dominated — a choice made on results; (b) tax-1 →
tax-2 on LCB added three codes after 22 unplaced points were seen, and the hand-assigned
mapping moved amplitude from +0.657 to +0.941 before the real re-judge landed between them
(`RESULTS.md`, "the two named judged sets"). Both are disclosed; the rule below keeps
future versions of them from becoming undisclosed.

### Procedure
1. Formulas: report all eleven entries of `code/BASELINES.md` in the raw tables (already
   the case) and state in `RESULTS.md` that the five headline entries were fixed *before*
   the HoVer models and GEPA runs, or, if not, which runs they were chosen on.
2. Taxonomy amendments made after a judge pass (§5 hand amendments): the amended taxonomy
   is evaluated only by a fresh judge pass, never by hand-assignment — the branch already
   does this for tax-2; make it the stated rule.
3. Anything learned or selected in future — a code subset, code weights, a formula picked
   among variants — is chosen on one candidate set and scored on the other. HoVer has two
   candidate sets on the same benchmark (9 models, 12 instruction sets) for exactly this;
   LCB has one, so a selection made on LCB is scored on a fresh judged draw of LCB tasks.
4. Since candidate sets span both base models and instruction sets, a selection made on
   the models set is not assumed to hold on the instruction set until checked.

### Integration
- **§1** gains one sentence: which decisions are made on which pool or candidate set.
- **§5** gains the "amended taxonomies are re-judged, never hand-assigned" rule.
- **§7 / §10 "What was run but is not reported"** states when the headline five were fixed.

---

## Raised in conversation, not yet reviewed

Recorded so they are not lost; none has a status.

**Consequence gate at taxonomy induction (§5, stage 6).** The HoVer taxonomies describe
the form of the modules' work: two codes carry 48% of the models-set points and fire on
passing and failing traces alike, and incidence is *negative* on the GEPA set (better
candidates do more, form codes fire on doing). A rule-validation check that rejects any
draft code whose firing rate on passing vs failing traces in the *taxonomy pool* is not
separated would remove them before the taxonomy is frozen. It reads gold, but only in the
taxonomy pool, which §1 already opens to the composer; it would widen that permission from
"choose failing traces" to "reject non-discriminating codes", and needs a decision on
whether that is still gold-free enough.

**Activity normalisation (§7).** A parameter-free variant of amplitude divided by the amount
of work in the trace (steps, or retrieved passages, or tokens), so a candidate that does
more is not scored as failing more. Directly aimed at the negative-incidence result.

**Per-code containment (§7).** Containment is the one method with a consistent positive
sign on HoVer. Reporting, per code, the fraction of its firings that are contained would
say which codes propagate and which are inert — a gold-free code-quality diagnostic that
could feed the consequence gate above without reading outcomes at all.
