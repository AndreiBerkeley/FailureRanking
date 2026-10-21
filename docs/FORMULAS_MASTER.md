# Every formula, in one place

Every formula used to rank candidates since the 2026-08-27 reset: its results on the five published benchmarks,
what it measures, and how to compute it step by step. Numbers are Kendall tau-b against the generalization set's pass
rates, written by `docs/scripts/formulas_master.py` from the recorded runs (no model call). The same code writes the
published tables in `sharing/`, so the numbers here match them.

Contents: 1. benchmarks, scoring and the split; 2. the baseline (gold against gold); 3. every formula, by family;
4. reading a score as a solve rate; 5. what is not here.

## 1. Benchmarks, scoring and the split

### 1.1 The benchmarks

Each benchmark is one pool of candidates, each run once per task, and three disjoint sets of tasks (1.3).

| experiment | candidates | judged tasks | generalization tasks | judged tasks also in the generalization set | taxonomy | judge | recovery reader |
|---|---|---:|---:|---:|---|---|---|
| GEPA candidates · HoVer | 12 GEPA-optimised prompt sets | 50 | 500 | 0 | GEPA_Candidates_HoVer_taxonomy.json (15 codes, 2 hand-authored) | readers gpt-5.6-luna ×2, decider gpt-5.6-sol; success rule in view | claude-sonnet-5; success rule in view |
| Models · HoVer (judged set b) | 9 models behind the same program | 50 | 500 | 0 | Models_HoVer_taxonomy.json (15 codes, 1 hand-authored) | readers gemini-3.6-flash ×2, decider claude-sonnet-5; before the success rule | claude-sonnet-5 (via Arena); success rule in view (recovery-2; recovery-1 predates the rule and is superseded) |
| Models · Terminal-Bench 2.0 | 7 models behind the Terminus 2 agent | 19 | 69 | 0 | Models_TerminalBench_taxonomy.json (10 codes) | readers gpt-5.6-luna ×2, decider gpt-5.6-sol; success rule in view | claude-sonnet-5; success rule in view |
| Models · LiveCodeBench | 9 models behind the same program | 50 | 755 | 0 | Models_LiveCodeBench_taxonomy.json (10 codes) | readers gemini-3.6-flash ×2, decider claude-sonnet-5; before the success rule | claude-sonnet-5 (via Arena); success rule in view; single-turn programs, so almost nothing can be recovered |
| Models · SWE-bench Verified | 12 models behind mini-SWE-agent 2.0.0 | 50 | 405 | 0 | Models_SWEbench_taxonomy.json (29 codes) | gemini-3.8-flash, one pass per trace (RedoAdamast pipeline); success rule not in view | gemini-3.8-flash (via Arena); success rule in view; output claims checked against the submitted patch |

The column of judged tasks also found in the generalization set is computed from the split files every time this
document is regenerated. It is 0 on every benchmark.

All five are published on the GitHub branch `model_ranking`. Short names in the tables: GEPA·HoVer (12 prompt sets from
one GEPA run, one model), Models·HoVer, TB 2.0 (Terminal-Bench 2.0), LCB (LiveCodeBench, its 50-task judged split), SWE
(SWE-bench Verified). **mean** averages the five.

### 1.2 What is computed

1. Every candidate runs once on every task. A trace is everything the candidate did on one task; the benchmark's grader
   gives each trace a pass/fail outcome $y_{c,t}\in\{0,1\}$ (gold).
2. The judge reads the traces of the **judged tasks only**, one trace at a time, without the outcome, and records its
   failure instances (1.4). The recovery reader, where used, reads the same traces and the judge's instances.
3. A formula turns one candidate's instances on the judged tasks into one score, computed for that candidate alone.
   Lower is better for every formula. The candidates are ranked by score.
4. The ranking is compared with the ranking by pass rate on the **generalization tasks**, which no judge or reader
   ever read: $\mathrm{gen}_c = \frac{1}{|G|}\sum_{t\in G} y_{c,t}$.

No formula reads gold. The only rows that do are the baseline (section 2) and gold-discounted incidence (3.4), which
is marked.

### 1.3 The split

```
all tasks of the benchmark
 ├─ taxonomy draw ─────────→ the failure taxonomy is generated from these traces; used for nothing else
 ├─ judged draw  (small) ──→ judge + recovery reader → failure instances → formula → ranking
 │                          (their gold gives the baseline row only)
 └─ generalization draw ───→ pass rate per candidate only = the target every ranking is compared with
    (large, never judged)
```

The three draws share no task (1.1). The generalization draw is the larger one and is only ever the target.

### 1.4 Inputs and notation

For candidate $c$ on judged task $t$, the judge returns a list of **failure instances** $P(c,t)$. Instance $i$ is a triple

$$ (s_i,\; M_i,\; r_i) $$

| symbol | meaning |
|---|---|
| $s_i$ | the step (turn) of the trace the instance sits on |
| $M_i$ | the failure modes (taxonomy codes) it carries; an instance no code fits carries the pseudo-code *(uncoded)* |
| $r_i$ | 1 if the recovery reader marked it *corrected* or *contained*, 0 if *unrecovered* or if the reader could not settle it |
| $T$ | the number of judged tasks |
| $\mathrm{codes}(c,t)$ | $\bigcup_i M_i$: the distinct codes on the trace, each counted once |
| $\mathrm{codes}(c,t,s)$ | the codes of the instances at step $s$ |
| $s_{\text{last}}(t)$ | the trace's final step |
| $\mathrm{rate}(c,m)$ | $\frac{1}{T}\sum_t \mathbf 1[m\in\mathrm{codes}(c,t)]$, the share of judged tasks on which code $m$ fired (coded codes only) |

*Corrected*: a later step replaced the wrong thing and the output does not carry it. *Contained*: the output does not
carry it and nothing corrected it. Recovery means the effect never reached the output; it never means the task passed.
A trace with no instance contributes 0 to every formula; a trace that could not be judged is left out of every sum and
of $T$.

**Every instance or unrecovered instances.** Most formulas are run twice: on every instance, and on unrecovered
instances only (every instance with $r_i=1$ deleted first). The two appear as two rows of the same formula.

**Formatting codes** (used by the endpoint formulas in 3.5 and by the formatting-removed rows of incidence). For each
benchmark, the codes about the shape of the output rather than its content:

| GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE |
|---|---|---|---|---|
| SP_09, SP_10, SP_13 | SP_04, SP_08, SP_09, SP_10, SP_11 | SP_01, SP_02, SP_03 | none | FM-01, FM-30 |

### 1.5 The measure

Kendall tau-b between the formula's ranking and the ranking by generalization pass rate:

1. Take every pair of candidates $(a,b)$: $n_0=\binom{n}{2}$ pairs.
2. A pair is **concordant** if the formula and the target order it the same way, **discordant** if they order it
   opposite ways. A pair tied in either is neither.
3. $n_1$ = pairs tied by the formula, $n_2$ = pairs tied by the target.

$$ \tau_b = \frac{C-D}{\sqrt{(n_0-n_1)(n_0-n_2)}} $$

$+1$: every pair ordered like the target; $-1$: every pair reversed; 0: no relation. With 7 to 12 candidates there are
21 to 66 pairs, so one pair moves tau by about 0.02 to 0.1. (Before 2026-10-08 the tables reported $(C-D)/(C+D)$,
Goodman–Kruskal gamma, under the tau-b label; every number here is true tau-b.)

## 2. The baseline: gold against gold

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| gold on the judged tasks | +0.779 | +0.444 | +0.551 | +0.743 | +0.445 | +0.592 |

**What it is.** The pass rate on the judged tasks, ranked against the pass rate on the generalization tasks. It reads
the same traces' outcomes that the formulas read the failures of, so it is the bar: a formula is useful when it ranks the
candidates at least this well from the same tasks.

**Steps.**

1. For every candidate and judged task, read the gold outcome $y_{c,t}$.
2. $G(c) = \frac{1}{T}\sum_{t} y_{c,t}$, the pass rate on the judged tasks. Higher is better.
3. Rank the candidates by $G(c)$ and compute tau-b against the generalization pass rates (1.5).

## 3. The formulas

Each entry: the results (one row per input or per setting), what the formula means, the variables, and the steps.
Every table repeats the gold row for reference. Lower score is better for every formula.

### 3.1 Per-task flags

#### Incidence

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| every instance | -0.334 | +0.255 | +0.582 | +0.761 | +0.305 | +0.314 |
| unrecovered instances (*unrecovered incidence*) | +0.776 | +0.535 | +0.951 | +0.761 | +0.781 | +0.761 |
| every instance, formatting codes removed | -0.505 | +0.493 | +0.732 | +0.761 | +0.395 | +0.375 |
| unrecovered instances, formatting codes removed | +0.753 | +0.535 | +0.951 | +0.761 | +0.835 | +0.767 |

**What it measures.** The share of judged tasks on which anything failed. On unrecovered instances: the share of judged tasks whose trace has at least one failure that reached the output.

**Steps.**

1. For each task, flag it if any instance is left: $f(c,t)=\mathbf 1[\mathrm{codes}(c,t)\neq\emptyset]$.
2. $I(c)=\frac{1}{T}\sum_t f(c,t)$.
3. Formatting-removed rows: before step 1, delete the benchmark's formatting codes from every $M_i$ and drop instances left with no code.

#### Last-turn incidence

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| every instance | +0.357 | +0.279 | +0.282 | +0.761 | -0.092 | +0.317 |
| unrecovered instances | +0.795 | +0.667 | +0.683 | +0.761 | +0.331 | +0.647 |

**What it measures.** The share of judged tasks with a failure at the trace's final step, after which nothing could fix it. It reads only the final step's instances.

**Steps.**

1. Find the final step $s_{\text{last}}(t)$.
2. Flag the task if a code fired there: $f(c,t)=\mathbf 1[\mathrm{codes}(c,t,s_{\text{last}}(t))\neq\emptyset]$.
3. $I_{\text{last}}(c)=\frac1T\sum_t f(c,t)$.

#### First and last, recovery checked on the two endpoints

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| formatting codes removed | +0.822 | +0.514 | +0.926 | +0.761 | +0.603 | +0.725 |

**What it measures.** The share of judged tasks whose first or last failure instance was not recovered. Only the two endpoints' verdicts are read; an unrecovered instance in the middle does not count.

**Steps.**

1. Delete formatting codes; drop instances left with no code. Call the result $P'(c,t)$.
2. Order $P'(c,t)$ by step, then by the judge's listing order: $\mathrm{first}(c,t)$ and $\mathrm{last}(c,t)$ (the same instance if there is one).
3. $S(c)=\frac1T\sum_t \mathbf 1\big[P'(c,t)\neq\emptyset \wedge \big(r_{\mathrm{first}}=0 \vee r_{\mathrm{last}}=0\big)\big]$.

### 3.2 Counts

#### Amplitude

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| every instance | -0.382 | +0.000 | +0.851 | +0.857 | +0.443 | +0.354 |
| unrecovered instances | +0.185 | +0.743 | +0.683 | +0.817 | +0.684 | +0.622 |

**What it measures.** How much goes wrong: the mean number of distinct failure modes per judged task. A code cited several times on one trace counts once.

**Steps.**

1. For each task, $k(c,t)=|\mathrm{codes}(c,t)|$ (*(uncoded)* counts as a code).
2. $A(c)=\frac1T\sum_t k(c,t)$, equivalently $\sum_m \mathrm{rate}(c,m)$ plus the uncoded share.

#### Step-amplitude

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| every instance | -0.400 | +0.000 | +0.586 | +0.857 | +0.137 | +0.236 |
| unrecovered instances | +0.185 | +0.761 | +0.619 | +0.817 | +0.321 | +0.540 |

**What it measures.** Amplitude counted per step: a code counts once for every step it fires at, so a mode that recurs through the trace weighs more.

**Steps.**

1. For each task, collect the (step, code) pairs that fired: $U(c,t)=\{(s,m): m\in\mathrm{codes}(c,t,s)\}$.
2. $A_{\text{step}}(c)=\frac1T\sum_t |U(c,t)|$.

#### Damped PIE

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| every instance, β = 0.5 | -0.424 | -0.056 | +0.810 | +0.833 | +0.473 | +0.327 |
| unrecovered instances, β = 0.5 | +0.626 | +0.667 | +0.810 | +0.778 | +0.738 | +0.724 |

**What it measures.** A count that saturates: each further distinct code on a task adds less. Between incidence and amplitude.

**Variables.** $\beta$ is a fixed constant; only $\beta=0.5$ was run. From the 2026-09-09 sweep; kept as a recorded baseline.

**Steps.**

1. $k=|\mathrm{codes}(c,t)|$.
2. Inclusion–exclusion over the task's codes with a subset of size $j$ weighted $\beta^{\,j-1}$ has the closed form $d(c,t)=\frac{1-(1-\beta)^k}{\beta}$. With $\beta=0.5$, a task with 1, 2, 3, 4 codes contributes 1, 1.5, 1.75, 1.875.
3. $D(c)=\frac1T\sum_t d(c,t)$. At $\beta\to0$ this is amplitude; at $\beta=1$ it is incidence.

#### Containment

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| every instance | -0.333 | +0.000 | +0.619 | +0.857 | +0.137 | +0.256 |
| unrecovered instances | +0.382 | +0.648 | +0.524 | +0.817 | +0.321 | +0.538 |

**What it measures.** Step-amplitude minus the firings the program's own later steps ran clean after: a failure followed only by clean steps is treated as contained. (The propagation discount of the 2026-09-09 sweep; kept as a recorded baseline.)

**Steps.**

1. Take the (step, code) pairs $U(c,t)$ and the set of steps that fired, $S(c,t)$.
2. A pair $(s,m)$ is *contained* when later steps exist ($s<s_{\text{last}}(t)$) and no code fired at any of them. The last step is never contained.
3. $A_{\text{con}}(c)=\frac1T\sum_t |\{(s,m)\in U(c,t): \text{not contained}\}|$.

### 3.3 Profile shape

#### Breadth

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| every instance | -0.469 | -0.057 | +0.329 | +0.745 | +0.208 | +0.151 |
| unrecovered instances | +0.000 | +0.417 | +0.309 | +0.745 | +0.614 | +0.417 |

**What it measures.** How many different things go wrong: the number of codes the candidate ever triggers on the judged tasks.

**Steps.**

1. Compute $\mathrm{rate}(c,m)$ for every code (uncoded excluded).
2. $B(c)=|\{m:\mathrm{rate}(c,m)>0\}|$.

#### Worst mode

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| every instance | -0.574 | +0.254 | +0.976 | +0.551 | +0.338 | +0.309 |
| unrecovered instances | -0.125 | +0.572 | +0.551 | +0.551 | +0.699 | +0.449 |

**What it measures.** How often the candidate's most frequent failure mode fires.

**Steps.**

1. Compute $\mathrm{rate}(c,m)$ for every code (uncoded excluded).
2. $W(c)=\max_m \mathrm{rate}(c,m)$.

#### Patterns

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| every instance | -0.202 | -0.167 | +0.714 | +0.712 | +0.140 | +0.239 |
| unrecovered instances | +0.331 | +0.572 | +0.451 | +0.756 | +0.551 | +0.532 |

**What it measures.** How many distinct combinations of failure modes the candidate shows across tasks.

**Steps.**

1. Collect the non-empty code sets $\mathrm{codes}(c,t)$ (uncoded excluded).
2. $P(c)$ = how many distinct sets there are.

### 3.4 Recovery-weighted formulas

#### Recovery-weighted amplitude

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| γ = 1 | +0.182 | +0.778 | +0.619 | +0.817 | +0.382 | +0.555 |
| γ = 2 | +0.000 | +0.833 | +0.619 | +0.817 | +0.412 | +0.536 |
| γ = 3 | -0.182 | +0.889 | +0.524 | +0.817 | +0.412 | +0.492 |

**What it measures.** Every failure counts, weighted by how often this candidate fails to recover from that kind of failure: a unit it always recovers from weighs 0, one it never recovers from weighs 1.

**Variables.** $\gamma\in\{1,2,3\}$ is a fixed constant: larger $\gamma$ forgives units that are recovered often. The 3-task minimum is a fixed constant. A variant with one weight per unit pooled over all candidates was negative on GEPA·HoVer and is not kept.

**Steps.**

1. A unit is a (step, code) pair $u=(s,m)$. On task $t$ the unit is recovered only if every instance carrying it was: $\mathrm{rec}_u(c,t)=\bigwedge\{r_i: s_i=s,\ m\in M_i\}$.
2. Over the candidate's tasks: $\mathrm{app}_u(c)$ = tasks on which $u$ fired, $\mathrm{recd}_u(c)$ = those on which it was recovered.
3. Recovery share $\rho_u(c)=\mathrm{recd}_u(c)/\mathrm{app}_u(c)$. If $u$ fired on fewer than 3 tasks, use the candidate's overall share $\sum_u\mathrm{recd}_u/\sum_u\mathrm{app}_u$.
4. Weight $w_u(c)=1-\rho_u(c)^{\gamma}$.
5. $A_{\text{rw}}(c)=\frac1T\sum_u w_u(c)\,\mathrm{app}_u(c)$.

#### Profile risk

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| own consequence, max over the task's codes | +0.545 | +0.722 | +0.810 | +0.761 | +0.504 | +0.668 |

**What it measures.** Unrecovered incidence predicted from the candidate's failure profile: each code carries the share of its instances this candidate left unrecovered, and a task is as risky as its riskiest code.

**Steps.**

1. For each code $m$: $\mathrm{app}(m)$ = the candidate's instances carrying $m$, $\mathrm{unr}(m)$ = those left unrecovered.
2. Consequence $q_c(m)=\mathrm{unr}(m)/\mathrm{app}(m)$.
3. Task risk $\rho(c,t)=\max_{m\in\mathrm{codes}(c,t)} q_c(m)$, 0 for a task with no code.
4. $R(c)=\frac1T\sum_t\rho(c,t)$.

A noisy-OR combination, $1-\prod_m(1-q_c(m))$, did worse: modes on the same task recover together, so treating them as independent risks over-counts candidates with many codes per trace. It is not kept.

#### Gold-discounted incidence (reads gold)

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| w = 0.5 | +0.831 | +0.535 | +0.878 | +0.722 | +0.853 | +0.764 |

**What it measures.** Unrecovered incidence with a flagged task discounted when the candidate passed it anyway. **It reads the judged tasks' gold, so it is not outcome-free and is never a candidate for the best method.**

**Variables.** $w=0.5$ is a fixed constant; only this value was run.

**Steps.**

1. Flag the task if it has an unrecovered instance.
2. A flagged task counts 1 if the candidate failed it ($y_{c,t}=0$) and $w$ if it passed; an unflagged task counts 0.
3. $I_g(c)=\frac1T\sum_{t\ \text{flagged}}\big(\mathbf 1[y_{c,t}=0]+w\,\mathbf 1[y_{c,t}=1]\big)$.

### 3.5 Endpoint formulas (first and last failure instance)

These read only each trace's first and last failure instance (plus, for the weights, the counts of those endpoints over
tasks and candidates). Preparation, shared by all of them:

1. Delete the benchmark's formatting codes from every $M_i$; drop instances left with no code. The result is $P'(c,t)$.
2. Choose the instances read: every instance of $P'(c,t)$, or its unrecovered instances only.
3. Order them by step, then by the judge's listing order: $\mathrm{first}(c,t)$, $\mathrm{last}(c,t)$ (one instance is
   both). $M(p)$ is the code set of endpoint $p\in\{\mathrm{first},\mathrm{last}\}$; a trace with no instance has no endpoints
   and contributes 0.

#### Weighted endpoint codes (the 75-cell grid)

Each (endpoint, code) pair of a task gets a value $v=w\cdot q$; a combiner turns the task's values into $V(c,t)$; the
score is $S(c)=\frac1T\sum_t V(c,t)$. Five recovery weights × five mode weights × three combiners = 75 settings, one row each.

**Recovery weight: no recovery**

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| none · max | -0.505 | +0.493 | +0.732 | +0.761 | +0.395 | +0.375 |
| none · sum over modes | -0.062 | +0.535 | +0.476 | +0.857 | +0.469 | +0.455 |
| none · sum over endpoints | -0.047 | +0.667 | +0.651 | +0.778 | +0.258 | +0.461 |
| rarity, own · max | -0.030 | +0.389 | +0.429 | +0.889 | -0.076 | +0.320 |
| rarity, own · sum over modes | +0.091 | +0.556 | +0.333 | +0.778 | -0.137 | +0.324 |
| rarity, own · sum over endpoints | +0.182 | +0.722 | +0.524 | +0.833 | -0.198 | +0.413 |
| rarity, pooled · max | +0.091 | +0.389 | +0.524 | +0.889 | +0.168 | +0.412 |
| rarity, pooled · sum over modes | +0.091 | +0.444 | +0.333 | +0.889 | +0.107 | +0.373 |
| rarity, pooled · sum over endpoints | +0.152 | +0.556 | +0.429 | +0.833 | +0.076 | +0.409 |
| rarity, combined · max | -0.030 | +0.444 | +0.524 | +0.833 | -0.198 | +0.315 |
| rarity, combined · sum over modes | +0.121 | +0.556 | +0.333 | +0.778 | -0.168 | +0.324 |
| rarity, combined · sum over endpoints | +0.091 | +0.611 | +0.429 | +0.778 | -0.168 | +0.348 |
| spread across candidates · max | -0.242 | +0.333 | +0.048 | +0.667 | +0.168 | +0.195 |
| spread across candidates · sum over modes | -0.091 | +0.333 | +0.238 | +0.778 | +0.382 | +0.328 |
| spread across candidates · sum over endpoints | -0.152 | +0.444 | +0.429 | +0.778 | +0.351 | +0.370 |

**Recovery weight: recovery-weighted, own**

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| none · max | +0.636 | +0.556 | +1.000 | +0.761 | +0.443 | +0.679 |
| none · sum over modes | +0.303 | +0.722 | +0.429 | +0.817 | +0.473 | +0.549 |
| none · sum over endpoints | +0.303 | +0.722 | +0.524 | +0.778 | +0.443 | +0.554 |
| rarity, own · max | +0.485 | +0.722 | +0.619 | +0.889 | +0.565 | +0.656 |
| rarity, own · sum over modes | +0.424 | +0.722 | +0.429 | +0.778 | +0.565 | +0.584 |
| rarity, own · sum over endpoints | +0.394 | +0.889 | +0.429 | +0.833 | +0.565 | +0.622 |
| rarity, pooled · max | +0.515 | +0.611 | +0.429 | +0.889 | +0.595 | +0.608 |
| rarity, pooled · sum over modes | +0.273 | +0.722 | +0.333 | +0.889 | +0.534 | +0.550 |
| rarity, pooled · sum over endpoints | +0.364 | +0.944 | +0.429 | +0.833 | +0.504 | +0.615 |
| rarity, combined · max | +0.515 | +0.722 | +0.429 | +0.833 | +0.534 | +0.607 |
| rarity, combined · sum over modes | +0.364 | +0.889 | +0.333 | +0.778 | +0.504 | +0.573 |
| rarity, combined · sum over endpoints | +0.303 | +1.000 | +0.429 | +0.778 | +0.504 | +0.603 |
| spread across candidates · max | +0.303 | +0.611 | +0.619 | +0.667 | +0.412 | +0.522 |
| spread across candidates · sum over modes | +0.182 | +0.667 | +0.524 | +0.778 | +0.412 | +0.512 |
| spread across candidates · sum over endpoints | +0.182 | +0.778 | +0.429 | +0.778 | +0.443 | +0.522 |

**Recovery weight: recovery-weighted, pooled**

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| none · max | +0.000 | +0.556 | +0.714 | +0.761 | +0.473 | +0.501 |
| none · sum over modes | +0.091 | +0.833 | +0.429 | +0.817 | +0.504 | +0.535 |
| none · sum over endpoints | +0.152 | +0.833 | +0.524 | +0.778 | +0.504 | +0.558 |
| rarity, own · max | +0.394 | +0.389 | +0.429 | +0.889 | +0.534 | +0.527 |
| rarity, own · sum over modes | +0.273 | +0.667 | +0.333 | +0.778 | +0.626 | +0.535 |
| rarity, own · sum over endpoints | +0.303 | +0.889 | +0.429 | +0.833 | +0.534 | +0.598 |
| rarity, pooled · max | +0.424 | +0.611 | +0.333 | +0.889 | +0.565 | +0.564 |
| rarity, pooled · sum over modes | +0.303 | +0.722 | +0.333 | +0.889 | +0.534 | +0.556 |
| rarity, pooled · sum over endpoints | +0.303 | +0.889 | +0.429 | +0.833 | +0.565 | +0.604 |
| rarity, combined · max | +0.333 | +0.500 | +0.333 | +0.833 | +0.565 | +0.513 |
| rarity, combined · sum over modes | +0.242 | +0.722 | +0.333 | +0.778 | +0.565 | +0.528 |
| rarity, combined · sum over endpoints | +0.303 | +0.889 | +0.429 | +0.778 | +0.565 | +0.593 |
| spread across candidates · max | +0.303 | +0.611 | +0.524 | +0.667 | +0.443 | +0.509 |
| spread across candidates · sum over modes | +0.152 | +0.722 | +0.619 | +0.778 | +0.443 | +0.543 |
| spread across candidates · sum over endpoints | +0.182 | +0.722 | +0.524 | +0.778 | +0.412 | +0.524 |

**Recovery weight: recovery-weighted, combined**

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| none · max | +0.667 | +0.500 | +0.714 | +0.761 | +0.473 | +0.623 |
| none · sum over modes | +0.333 | +0.722 | +0.429 | +0.817 | +0.443 | +0.549 |
| none · sum over endpoints | +0.394 | +0.722 | +0.524 | +0.778 | +0.473 | +0.578 |
| rarity, own · max | +0.424 | +0.444 | +0.429 | +0.889 | +0.534 | +0.544 |
| rarity, own · sum over modes | +0.303 | +0.667 | +0.333 | +0.778 | +0.626 | +0.541 |
| rarity, own · sum over endpoints | +0.424 | +0.944 | +0.429 | +0.833 | +0.595 | +0.645 |
| rarity, pooled · max | +0.455 | +0.611 | +0.333 | +0.889 | +0.565 | +0.571 |
| rarity, pooled · sum over modes | +0.303 | +0.722 | +0.333 | +0.833 | +0.565 | +0.551 |
| rarity, pooled · sum over endpoints | +0.364 | +0.889 | +0.429 | +0.833 | +0.504 | +0.604 |
| rarity, combined · max | +0.515 | +0.444 | +0.333 | +0.833 | +0.565 | +0.538 |
| rarity, combined · sum over modes | +0.333 | +0.833 | +0.333 | +0.778 | +0.565 | +0.569 |
| rarity, combined · sum over endpoints | +0.364 | +0.944 | +0.429 | +0.778 | +0.565 | +0.616 |
| spread across candidates · max | +0.394 | +0.667 | +0.524 | +0.667 | +0.443 | +0.539 |
| spread across candidates · sum over modes | +0.333 | +0.722 | +0.619 | +0.778 | +0.473 | +0.585 |
| spread across candidates · sum over endpoints | +0.303 | +0.778 | +0.619 | +0.778 | +0.473 | +0.590 |

**Recovery weight: unrecovered instances only**

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| none · max | +0.753 | +0.535 | +0.951 | +0.761 | +0.835 | +0.767 |
| none · sum over modes | +0.406 | +0.833 | +0.878 | +0.817 | +0.800 | +0.747 |
| none · sum over endpoints | +0.677 | +0.833 | +0.714 | +0.778 | +0.862 | +0.773 |
| rarity, own · max | +0.879 | +0.500 | +0.714 | +0.889 | +0.718 | +0.740 |
| rarity, own · sum over modes | +0.636 | +0.667 | +0.810 | +0.778 | +0.779 | +0.734 |
| rarity, own · sum over endpoints | +0.727 | +0.667 | +0.810 | +0.833 | +0.809 | +0.769 |
| rarity, pooled · max | +0.636 | +0.611 | +0.810 | +0.889 | +0.687 | +0.727 |
| rarity, pooled · sum over modes | +0.727 | +0.667 | +0.810 | +0.833 | +0.687 | +0.745 |
| rarity, pooled · sum over endpoints | +0.667 | +0.778 | +0.905 | +0.722 | +0.687 | +0.752 |
| rarity, combined · max | +0.818 | +0.389 | +0.810 | +0.833 | +0.718 | +0.714 |
| rarity, combined · sum over modes | +0.636 | +0.722 | +0.810 | +0.833 | +0.718 | +0.744 |
| rarity, combined · sum over endpoints | +0.667 | +0.722 | +0.905 | +0.833 | +0.748 | +0.775 |
| spread across candidates · max | +0.727 | +0.667 | +0.619 | +0.667 | +0.718 | +0.679 |
| spread across candidates · sum over modes | +0.758 | +0.611 | +0.810 | +0.722 | +0.657 | +0.711 |
| spread across candidates · sum over endpoints | +0.697 | +0.778 | +0.810 | +0.722 | +0.809 | +0.763 |

**What it measures.** How much goes wrong at the two ends of a trace, with three choices: whether recovered endpoints
count (and how much), whether rare or distinctive codes weigh more, and how a task's endpoint codes add up. With no
weight and *max*, it is incidence on $P'$; with no weight and a sum, it counts the endpoint codes.

**Variables.**

- $o_c(m,p)$ = the number of $c$'s tasks with code $m$ at endpoint $p$; $u_c(m,p)$ = how many of those endpoints are
  unrecovered; $N_c(p)=\sum_m o_c(m,p)$.
- **Recovery weight $q$.** An unrecovered endpoint has $q=1$. A recovered one has: *no recovery*, 1 (verdicts not read);
  *recovery-weighted, own*, $u_c(m,p)/o_c(m,p)$ shrunk across $c$'s codes at that position; *recovery-weighted, pooled*,
  $\sum_c u_c(m,p)/\sum_c o_c(m,p)$, one rate for every candidate; *recovery-weighted, combined*, $c$'s own rate shrunk toward
  the pooled rate across candidates; *unrecovered instances only*, the endpoints are taken from the unrecovered instances,
  so every endpoint has $q=1$. The first four take endpoints from every instance.
- **Mode weight $w$.** *none*, 1; *rarity, own*, $-\ln\big(o_c(m,p)/N_c(p)\big)$, so a code common in this candidate's
  endpoints weighs little and a rare one a lot; *rarity, pooled*, $-\ln\big(\sum_c o_c(m,p)/\sum_c N_c(p)\big)$, the rarity
  among all candidates; *rarity, combined*, $-\ln$ of $c$'s share shrunk toward the pooled share across candidates;
  *spread across candidates*, $\sigma/\mu$ over candidates of the per-task rate $o_c(m,p)/T$, the same for every candidate
  (a code that separates the candidates weighs more).
- **Combiner.** *max*: $V=\max v$; *sum over modes*: $V=\sum_m\max_p v(m,p)$, a code on both endpoints counted once;
  *sum over endpoints*: $V=\sum v$ over every (endpoint, code) pair, a one-instance trace counted once.
- **Shrinkage** (empirical Bayes, beta-binomial method of moments), for groups $g$ with counts $(k_g,n_g)$: pooled rate
  $p_0=\sum k_g/\sum n_g$ with $N=\sum n_g$ over $G$ groups; observed spread $v=\sum_g (n_g/N)(k_g/n_g-p_0)^2$; spread beyond
  binomial noise $\tau^2=v-p_0(1-p_0)G/N$; if $\tau^2\le0$ every group gets $p_0$, otherwise $\alpha=\max\big(0,\,p_0(1-p_0)/\tau^2-1\big)$
  and the shrunk rate is $(k_g+\alpha p_0)/(n_g+\alpha)$. No constant is set by hand.

**Steps.**

1. Prepare the endpoints (above), from every instance or from unrecovered instances as the recovery weight says.
2. Count $o_c(m,p)$, $u_c(m,p)$, $N_c(p)$ for every candidate; compute $q$ and $w$ for every (code, position).
3. For each (endpoint, code) pair of a task, $v=w_c(m,p)\cdot q$ ($q=1$ for an unrecovered endpoint).
4. Combine into $V(c,t)$ with the chosen combiner; $S(c)=\frac1T\sum_t V(c,t)$.

#### Setup 1: entropy of the endpoint codes (no recovery)

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| rarity over both endpoints pooled | +0.121 | +0.444 | +0.333 | +0.833 | +0.107 | +0.368 |

**What it measures.** The number of endpoint codes per task times how evenly they spread: a candidate whose endpoint failures are many and varied scores worst.

**Steps.**

1. Endpoints of every instance of $P'(c,t)$; endpoint codes $E(c,t)=M(\mathrm{first})\cup M(\mathrm{last})$.
2. $n_c(m)=\sum_t\mathbf 1[m\in E(c,t)]$, $N_c=\sum_m n_c(m)$, $\pi_c(m)=n_c(m)/N_c$.
3. $w_c(m)=-\ln\pi_c(m)$.
4. $V(c,t)=\sum_{m\in E(c,t)}w_c(m)$; $S(c)=\frac1T\sum_tV(c,t)=\frac{N_c}{T}\,H(\pi_c)$ with $H(\pi)=-\sum_m\pi(m)\ln\pi(m)$.

#### Mode filters

Remove some codes from the endpoints, then score the share of tasks with an endpoint code left. Three inputs × nine
rules = 27 settings, one row each. (No filter equals incidence on $P'$, unrecovered incidence on $P'$, and the
first-and-last flag, 3.1.)

**Input: endpoints of every instance (no recovery)**

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| across candidates: drop the top 1 mode | +0.147 | +0.535 | +0.683 | +0.629 | +0.065 | +0.412 |
| across candidates: drop the top 2 modes | -0.561 | +0.648 | +0.514 | +0.572 | +0.318 | +0.298 |
| across candidates: drop the top 3 modes | +0.295 | +0.457 | -0.109 | +0.548 | +0.202 | +0.278 |
| across candidates: drop modes above mean + 1 SD | +0.388 | +0.400 | +0.514 | +0.572 | +0.109 | +0.396 |
| across candidates: drop modes above mean + 1.5 SD | -0.561 | +0.377 | +0.794 | +0.629 | +0.109 | +0.270 |
| per candidate: drop the top 1 mode | +0.140 | +0.572 | +0.582 | +0.667 | -0.202 | +0.352 |
| per candidate: drop the top 2 modes | +0.156 | +0.535 | +0.514 | +0.667 | -0.188 | +0.337 |
| per candidate: drop modes above mean + 1 SD | +0.047 | +0.254 | +0.293 | +0.667 | -0.171 | +0.218 |
| per candidate: drop modes above mean + 1.5 SD | +0.078 | +0.286 | +0.732 | +0.667 | -0.185 | +0.316 |

**Input: recovery checked on the endpoints (an endpoint counts only if unrecovered)**

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| across candidates: drop the top 1 mode | +0.698 | +0.457 | +0.586 | +0.572 | +0.656 | +0.594 |
| across candidates: drop the top 2 modes | +0.114 | +0.725 | +0.056 | +0.572 | +0.656 | +0.425 |
| across candidates: drop the top 3 modes | +0.369 | +0.530 | -0.700 | +0.588 | +0.667 | +0.291 |
| across candidates: drop modes above mean + 1 SD | +0.268 | +0.686 | +0.056 | +0.592 | +0.656 | +0.452 |
| across candidates: drop modes above mean + 1.5 SD | +0.114 | +0.783 | +0.159 | +0.572 | +0.656 | +0.457 |
| per candidate: drop the top 1 mode | +0.540 | +0.857 | +0.683 | +0.667 | +0.689 | +0.687 |
| per candidate: drop the top 2 modes | +0.331 | +0.650 | +0.056 | +0.667 | +0.592 | +0.459 |
| per candidate: drop modes above mean + 1 SD | +0.401 | +0.650 | +0.651 | +0.667 | +0.731 | +0.620 |
| per candidate: drop modes above mean + 1.5 SD | +0.678 | +0.648 | +0.878 | +0.667 | +0.721 | +0.718 |

**Input: endpoints of the unrecovered instances**

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks (the bar)* | *+0.779* | *+0.444* | *+0.551* | *+0.743* | *+0.445* | *+0.592* |
| across candidates: drop the top 1 mode | +0.750 | +0.800 | +0.794 | +0.572 | +0.794 | +0.742 |
| across candidates: drop the top 2 modes | +0.791 | +0.592 | +0.370 | +0.572 | +0.753 | +0.615 |
| across candidates: drop the top 3 modes | +0.574 | +0.423 | +0.000 | +0.588 | +0.531 | +0.423 |
| across candidates: drop modes above mean + 1 SD | +0.574 | +0.592 | +0.370 | +0.572 | +0.807 | +0.583 |
| across candidates: drop modes above mean + 1.5 SD | +0.782 | +0.592 | +0.951 | +0.572 | +0.794 | +0.738 |
| per candidate: drop the top 1 mode | +0.699 | +0.667 | +0.823 | +0.667 | +0.813 | +0.734 |
| per candidate: drop the top 2 modes | +0.858 | +0.629 | +0.394 | +0.667 | +0.613 | +0.632 |
| per candidate: drop modes above mean + 1 SD | +0.625 | +0.629 | +0.411 | +0.667 | +0.849 | +0.636 |
| per candidate: drop modes above mean + 1.5 SD | +0.524 | +0.704 | +0.951 | +0.667 | +0.835 | +0.736 |

**What it measures.** The share of tasks with an endpoint failure left after ignoring the most common codes, the
ones every candidate (or this candidate) shows anyway, on the idea that they say little about which candidate is better.

**Variables.** $n_p(m)$ = how many tasks have code $m$ at endpoint $p$, counted over every candidate (*across
candidates*) or over the candidate's own tasks (*per candidate*). *Top k*: drop the $k$ codes with the largest $n_p(m)$
($k=1,2,3$). *Mean + k SD*: drop every code with $n_p(m)>\mu_p+k\sigma_p$, the mean and population SD of the counts over
the codes seen at $p$ ($k=1,1.5$). $k$ is a fixed constant in both rules. The rules were chosen by looking at Models·HoVer.

**Steps.**

1. Prepare the endpoints for the input (from every instance, or from the unrecovered instances).
2. For each position $p\in\{\mathrm{first},\mathrm{last}\}$ count $n_p(m)$ (across candidates or per candidate).
3. Choose the codes to drop, $D_p$, with the rule.
4. $S(c)=\frac1T\sum_t\mathbf 1\big[\exists p: M(p)\setminus D_p\neq\emptyset\big]$; with *recovery checked on the endpoints*, endpoint
   $p$ must also be unrecovered.

## 4. Reading a score as a solve rate

For the formulas that are a share of tasks, $1-S(c)$ is the share of judged tasks the traces say were solved, and can
be compared with the actual solve rate as a number. Mean over candidates of $|(1-S(c))-\mathrm{gen}_c|$, in percentage
points; the gold row is the judged tasks' own pass rate against the generalization pass rate (the part of the gap that
is the task draw).

| | GEPA·HoVer | Models·HoVer | TB 2.0 | LCB | SWE | mean |
|---|---:|---:|---:|---:|---:|---:|
| *gold on the judged tasks* | 3.7 | 7.6 | 11.6 | 4.5 | 9.6 | 7.4 |
| incidence, every instance | 55.3 | 43.9 | 41.8 | 5.1 | 73.1 | 43.8 |
| incidence, unrecovered instances | 3.5 | 15.4 | 10.2 | 5.1 | 7.8 | 8.4 |
| last-turn incidence, every instance | 19.0 | 37.5 | 10.2 | 5.1 | 20.7 | 18.5 |
| last-turn incidence, unrecovered instances | 8.4 | 18.5 | 7.9 | 5.1 | 19.9 | 12.0 |
| profile risk | 8.1 | 12.8 | 4.1 | 5.4 | 11.7 | 8.4 |

## 5. What is not here

- Benchmarks whose candidates cannot be told apart, so no ranking can be graded on them: livebenchmath, IFBench (500-task
  judging pool), the HotpotQA and IFBench GEPA pools of August, and the NewGEPAChanges panel3 r11 pools (`INDEX.md`).
- The 2026-09-09 sweep's other variants (other propagation discounts and inclusion–exclusion variants, co-occurrence and
  prevalence weightings, the terminal-step score) and the formulas from before the 2026-08-27 reset (`legacy/`).
- τ²-bench banking and BFCL v4 multi-turn: judged and recovered locally but not published; their numbers for the best
  formulas are in `results/BEST.md`.
- The paper's new benchmarks (`paper/benchmarks/`), which have no judge runs yet.
- Choosing a best formula from this document is an in-sample choice: the best row of 134 on the same benchmarks is
  optimistic by roughly its gap to the next rows.

Generated by `docs/scripts/formulas_master.py`.
