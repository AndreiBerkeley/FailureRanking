# Literature Library

Filed by **purpose** — what a paper is *for* in this research, not where it
was published. One primary split per paper (cross-reference when needed).
Entry format: link · year · main idea · gold availability · why we care.
Create a new split the moment the first paper of a new purpose arrives
(e.g. combinatorics / number theory / statistics splits as math
foundations accumulate). Seeded 2026-08-07 from the Google Doc "New
research directions (Andrei / Mert)".

## 1. Candidate failure evaluation — identification & attribution

- [AgentRx: Diagnosing AI Agent Failures from Execution Trajectories](https://arxiv.org/abs/2602.02475) — Barke et al., 2026.
  Generates task/policy constraints, checks them through a failed
  trajectory, uses the violation log to find the first unrecovered failure
  step and its category. Gold: receives a trajectory known to have failed
  but no reference answer; human critical-step annotations used only to
  evaluate attribution accuracy. *Why we care:* closest neighbor for
  gold-free failure identification; its 115-trajectory annotation set is a
  possible oracle source.
- [FALAT: Tracing Failures in LLM Agent Trajectories via Dependency-Guided Search](https://arxiv.org/abs/2606.00765) — Rafi et al., 2026.
  Builds an expected task structure, finds suspicious regions, follows
  dependencies to separate error-introducing steps from downstream
  symptoms/propagation. Gold: human attribution labels as evaluation gold
  only. *Why we care:* the designated base for our recovery analyzer
  (explicitly replaceable).
- [Causal Agent Replay: Counterfactual Attribution for LLM-Agent Failures](https://arxiv.org/abs/2606.08275) — Shah, 2026.
  Intervenes on a step, reruns the remainder repeatedly, measures whether
  the outcome distribution changes; causal effects and Shapley values
  computed mechanically. Gold: requires an outcome function for every
  replay. *Why we care:* the executed-replay option for recovery
  ground-truth; expensive but oracle-grade.

- [Which Agent Causes Task Failures and When? (Who&When)](https://arxiv.org/abs/2505.00212) — Zhang et al., ICML 2025.
  Formulates automated failure attribution for LLM multi-agent systems;
  Who&When dataset: failure logs from 127 multi-agent systems with human
  annotations linking each failure to the responsible agent and decisive
  error step. Best automated method: 53.5% agent-level, 14.2% step-level
  accuracy. Gold: human attribution labels, evaluation only. *Why we care:*
  the multi-agent analog of our attribution question; a measured warning
  about judge-quality ceilings (Q_Judge); its annotation set is a possible
  oracle source alongside AgentRx's.

## 2. Reliability measurement

- [Towards a Science of AI Agent Reliability](https://arxiv.org/abs/2602.16666) — Rabanser et al., 2026.
  Twelve metrics across consistency/robustness/predictability/safety
  instead of compressing reliability into success rate; violation frequency
  and conditional severity kept separate so severe errors aren't diluted.
  Gold: GAIA/τ-bench reference targets needed for most metrics. *Why we
  care:* the multi-metric profile view our Stage-3 "profile" output should
  be comparable against.
- [Consistency as a Testable Property](https://arxiv.org/abs/2605.10516) — Raj et al., 2026.
  Measures outcome and trajectory consistency under semantically equivalent
  task variations (U-statistics, kernel tests, alignment kernels). Gold:
  trajectory consistency measurable without gold; correctness is not.
  *Why we care:* statistical machinery for cross-seed stability — our
  scenario 2.
- [TraceToChain: Markov Chain Reliability for LLM Agents](https://arxiv.org/abs/2604.24579) — Tran-Truong & Le, 2026.
  Converts traces into an absorbing Markov chain; reliability, pass@k,
  decay curves computed statistically. Gold: every training trace needs a
  terminal success/failure label. *Why we care:* a competing
  trace-structure→reliability compression; contrast for our
  taxonomy-structured alternative.
- [HIP-LLM: Hierarchical Imprecise Probability for LLM Reliability](https://arxiv.org/abs/2511.00527) — Aghazadeh-Chakherlou et al., 2026.
  Probability of completing k future tasks without failure under a declared
  operational profile; hierarchical Bayes with imprecise priors. Gold:
  requires binary success/failure observations; evaluator uncertainty
  unmodeled. *Why we care:* the "declared operational profile" is the
  formal cousin of our declared evaluation scenario.

## 3. Task-set generalization & ranking

- [SubLIME: Subset Selection via Rank Correlation Prediction](https://aclanthology.org/2025.acl-long.1477/) — Saranathan et al., ACL 2025.
  Selects a benchmark subset that preserves the full-benchmark candidate
  ranking. Gold: official evaluators required for anchors and candidates.
  *Why we care:* our trace-subset-quality question (instrument-trust axis 1)
  in outcome space; baseline intuition for representativeness.
- [Quantifying Ranking Uncertainty in LLM Benchmarks](https://arxiv.org/abs/2607.16259) — Neuhof & Benjamini, 2026.
  Replaces a point rank with a confidence interval of statistically
  plausible ranks (pairwise tests + Holm correction). Gold: needs per-unit
  candidate scores — explicitly applicable to independently defined
  failure-based scores. *Why we care:* directly reusable for our ranking
  uncertainty U(c).
- [How Many Tasks Are Enough for Agent Benchmark Decisions?](https://arxiv.org/abs/2607.12338) — Huang, 2026.
  How much of a benchmark must be observed before a partial evaluation
  reproduces the full-benchmark pairwise decision. Gold: verified pass/fail
  outcomes required. *Why we care:* frames our N→M generalization scenario
  as decision fidelity; explicitly does not claim unseen-task
  generalization — the gap we target.

## 4. Statistical & failure-scoring foundations

- [The Unnecessity of Assuming Statistically Independent Tests in Bayesian Software Reliability](https://arxiv.org/abs/2208.00462) — Salako & Zhao, IEEE TSE 2023.
  Conservative reliability claims under possibly-correlated tests,
  including the zero-observed-failures case. Gold: assumes a trustworthy
  success/failure oracle. *Why we care:* correlated-evidence handling for
  co-occurring failure modes (rubric 4) and the S(c)=100 "no burden
  observed ≠ certified perfect" caveat.
- [An Assessment of RPN Prioritization in FMEA](https://doi.org/10.17764/jiet.47.1.y576m26127157313) — Bowles, 2004.
  Classical severity × occurrence × detectability multiplication is
  technically unstable and conflates distinct risk profiles. Gold: expert
  ratings, no task gold. *Why we care:* a standing warning against naively
  multiplying LLM-rated severity/frequency into one candidate score — our
  influence function must not repeat FMEA's mistake.

- [Averaging Attributable Fractions in the Multifactorial Situation](https://www.sciencedirect.com/science/article/abs/pii/S089543569800002X) — Gefeller, Land & Eide, J Clin Epi 1998 (line begins Eide & Gefeller 1995; uniqueness from [Cox 1985](https://link.springer.com/chapter/10.1007/978-3-642-59051-1_48); axiomatized by [Land & Gefeller 1997](https://onlinelibrary.wiley.com/doi/10.1002/bimj.4710390705)).
  When risk factors co-occur, per-factor attributable fractions sum past
  100% of disease burden; the fix — sequential attributable fractions
  averaged over all removal orders (the average attributable fraction) —
  is exactly the Shapley value of the risk-attribution game, unique under
  additivity, symmetry, and independence of irrelevant factors, with
  allocations summing exactly to the joint burden. Gold: exposure–disease
  data; no task-gold concept. *Why we care:* the mature incarnation of
  Φ v0.1's Step-5 allocation — co-occurring failure modes are the risk
  factors, task burden the disease load; primary related-work anchor for
  our double-counting fix.
- [Noisy-OR gate / causal independence](https://www.emergentmind.com/topics/noisy-or-gate-model) — Kim & Pearl, 1983.
  Multiple independent binary causes of one effect combine as
  1 − Π(1 − p_i): parameters linear in the number of causes, saturating,
  monotone. Gold: none — a modeling primitive. *Why we care:* Φ v0.1's
  Step-3 per-task combiner; its causal-independence assumption is
  precisely what the parked causal-position package (PARKING.md
  2026-08-07) would relax.

## 5. Considered and rejected — co-occurrence & attribution alternatives

Surveyed 2026-08-07 while choosing how Φ should handle several failure
modes striking one task, and set aside. Filed so the design space is
visible: what we did *not* adopt, and why. Promotion out of this split
is possible if the rejection reason stops applying.

- [Rothman's sufficient-component-cause model ("causal pies")](https://en.wikipedia.org/wiki/Causal_pie_model) — Rothman, 1976; see also [Rothman and multicausality](https://www.sciencedirect.com/science/article/pii/S0398762011004457).
  An outcome occurs when a "pie" of component causes is complete; a
  component's effect is defined only relative to its co-present
  components, and components recur across different pies. Gold: none —
  a conceptual frame, not a procedure. *Why we care:* the cleanest
  statement of **why per-mode marginal charges over-count**, and the
  conceptual ancestor of the attributable-fraction line in §4.
  *Rejected as a method* because it prescribes no computation; its
  deterministic engineering rendering (fault trees / minimal cut sets)
  needs authored structure, so it fits the future rubric-5 authored-rule
  layer rather than v0.1. Retained as framing, not machinery.
- [Common-cause failure parametric models — alpha-factor, beta-factor, MGL](https://ftaassociates.com/wp-content/uploads/2018/12/A.-Mosieh-Guidelines-on-Modeling-Common-Cause-Failures-in-Probabilistic-Risk-Assessment-NUREGCR-5485-November-1998.pdf) — Mosleh & Siu; NUREG/CR-4780 (1988), NUREG/CR-5485 (1998); [alpha-factor updating](https://doi.org/10.1177/1748006X16689542).
  Nuclear/aerospace PRA splits each component's failure rate into an
  independent part and a shared-cause part, with few parameters
  estimable from observed event multiplicities (how often 1, 2, … k
  components fail together). Gold: component failure data; no task-gold
  concept. *Why we care:* purpose-built for "correlated failures inflate
  naive counts," tiny parameter count, freezable on a dev split.
  *Rejected for now* because the models assume **identical redundant
  components in symmetric groups**, while our failure modes are
  heterogeneous — the mapping is an analogy needing care — and it still
  leaves allocation to the Shapley machinery we did adopt.
- [A Survey on Software Fault Localization](https://doi.org/10.1109/TSE.2016.2521368) — Wong, Gao, Li, Abreu & Wotawa, IEEE TSE 42(8), 2016; multi-fault treatment in [IJCAI 2023](https://www.ijcai.org/proceedings/2023/0350.pdf).
  Spectrum-based fault localization scores program components by
  co-occurrence with failing runs (Tarantula, Ochiai). Gold: **requires
  pass/fail per run**. *Why we care:* software engineering's version of
  our problem, and a documented negative result — suspiciousness metrics
  **degrade as simultaneous fault count grows**, the same pathology we
  hit, with its workarounds as a warning catalogue. *Rejected for the
  scoring path* on the gold requirement; usable as a gold-calibrated
  baseline and related work.
- [Bayesian-network structure learning](https://arxiv.org/abs/1302.4972) — Spirtes/Glymour PC algorithm and successors.
  Learn a DAG over mode-incidence data (typically with noisy-OR CPDs)
  and read off root-vs-derived modes. Gold: none required. *Why we care:*
  the fully data-driven route to the causal structure the parked
  σ-package needs. *Rejected* because observational co-occurrence badly
  underdetermines edge direction while **trace order gives it directly**
  (FALAT-style edges, §1), it is data-hungry at our N, and pooling
  across candidates to gain samples would break Φ's per-candidate
  independence.
- [Latent Class Analysis: A Guide to Best Practice](https://doi.org/10.1177/0095798420930932) — Weller, Bowen & Faubert, J. Black Psychology 46(4), 2020; method originates with Lazarsfeld & Henry (1968).
  Modes co-occur because several are symptoms of one unobserved fault;
  charge the latent factor rather than the observed modes. Gold: none
  required. *Why we care:* the elegant answer to taxonomy aliasing — the
  case where two codes name the same event. *Rejected* on **boundary 1**:
  estimating latent failure factors from data *is* building a taxonomy,
  which is an inherited instrument in this project, not our
  contribution; estimation is also unstable at our scale. Aliasing is
  handled instead as a Q_Taxonomy signal in Ψ.

## 6. Mathematical foundations (combinatorics · number theory · …)

*(empty — create sub-splits as the first papers are filed)*
