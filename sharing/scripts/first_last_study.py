#!/usr/bin/env python3
"""first_last_study.md: the first-and-last failure-instance study (run 2026-09-28), regenerated on the four main
experiments.

    python3 sharing/scripts/first_last_study.py --out sharing/first_last_study.md

Every score here reads only each trace's first and last failure instance, after removing the instances whose
codes are all formatting codes. Part A compares that with reading every instance; Part B tries fixed mode filters
(pooled across candidates or per candidate); Part C is a grid of weightings in which every weight is estimated
from the data; Part D is one fully specified setup without recovery. Same loaders, gold and tau code as
results_tables.py. Offline; no model call.
"""
from __future__ import annotations
import argparse, math, statistics as st, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from results_tables import MAIN, load, taub, topk  # noqa: E402

# Formatting codes: codes about the shape of the output (field markers, required sections, output format)
# rather than its content. Chosen by reading each taxonomy on 2026-09-28; LiveCodeBench's has none.
FMT = {"gepa_hover": {"SP_09", "SP_10", "SP_13"}, "models_hover": {"SP_04", "SP_08", "SP_09", "SP_10", "SP_11"},
       "models_tb": {"SP_01", "SP_02", "SP_03"}, "models_lcb": set()}
TAXONOMY = {"gepa_hover": "GEPA_Candidates_HoVer_taxonomy.json", "models_hover": "Models_HoVer_taxonomy.json",
            "models_tb": "Models_TerminalBench_taxonomy.json", "models_lcb": "Models_LiveCodeBench_taxonomy.json"}
SHORT = {"gepa_hover": "GEPA·HoVer", "models_hover": "Models·HoVer", "models_tb": "Models·TB", "models_lcb": "Models·LCB"}
f3 = lambda x: "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:+.3f}"


# ------------------------------------------------------------------ data
class Exp:
    def __init__(self, exp):
        self.key, self.title = exp["key"], exp["title"]
        self.active, self.tasks, pts, last, GJ, GG, _ = load(exp)
        self.T = len(self.tasks)
        self.gg = {c: sum(GG[c].values()) / len(GG[c]) for c in self.active}
        self.gj = {c: sum(GJ[c][t] for t in self.tasks) / self.T for c in self.active}
        self.bar = taub({c: -self.gj[c] for c in self.active}, self.gg, self.active)[0]
        F = FMT[self.key]
        self.pts = pts
        # step 1: drop formatting codes; an instance with no other code is dropped, an uncoded instance stays
        self.nofmt = {(c, t): [(s, [m for m in cs if m not in F], r) for s, cs, r in pts[c][t] if any(m not in F for m in cs)]
                      for c in self.active for t in self.tasks}

    def score(self, s):
        tau, n = taub(s, self.gg, self.active)
        return tau, bool(topk(s, self.gg, self.active, 1)), n


def endpoints(ps):
    """step 2: order by (turn, position in the judge's listing); first and last; one instance is both."""
    if not ps:
        return None
    o = sorted(range(len(ps)), key=lambda i: (ps[i][0], i))
    return ps[o[0]], ps[o[-1]]


# ------------------------------------------------------------------ Part A
def part_a(E):
    rows = {}
    for x in E:
        A, T = x.active, x.T
        unrec = lambda ps: any(not p[2] for p in ps)
        def ends_flag(c, t, need_unrec):
            e = endpoints(x.nofmt[c, t])
            return bool(e) and (not need_unrec or not e[0][2] or not e[1][2])
        M = {
            "incidence, every instance (no recovery)": {c: sum(bool(x.pts[c][t]) for t in x.tasks) / T for c in A},
            "incidence, formatting removed (no recovery)": {c: sum(bool(x.nofmt[c, t]) for t in x.tasks) / T for c in A},
            "unrecovered incidence, every instance": {c: sum(unrec(x.pts[c][t]) for t in x.tasks) / T for c in A},
            "unrecovered incidence, formatting removed": {c: sum(unrec(x.nofmt[c, t]) for t in x.tasks) / T for c in A},
            "first & last, recovery checked on the two endpoints": {c: sum(ends_flag(c, t, True) for t in x.tasks) / T for c in A},
        }
        for k, s in M.items():
            rows.setdefault(k, {})[x.key] = x.score(s)
        rows.setdefault("_removed", {})[x.key] = (sum(len(x.pts[c][t]) for c in A for t in x.tasks),
                                                  sum(len(x.pts[c][t]) - len(x.nofmt[c, t]) for c in A for t in x.tasks))
    return rows


# ------------------------------------------------------------------ Part B
RULES = [("no filter", None, None),
         ("across candidates: drop the top 1 mode", "pool", ("top", 1)), ("across candidates: drop the top 2 modes", "pool", ("top", 2)),
         ("across candidates: drop the top 3 modes", "pool", ("top", 3)),
         ("across candidates: drop modes above mean + 1 SD", "pool", ("sd", 1.0)), ("across candidates: drop modes above mean + 1.5 SD", "pool", ("sd", 1.5)),
         ("per candidate: drop the top 1 mode", "own", ("top", 1)), ("per candidate: drop the top 2 modes", "own", ("top", 2)),
         ("per candidate: drop modes above mean + 1 SD", "own", ("sd", 1.0)), ("per candidate: drop modes above mean + 1.5 SD", "own", ("sd", 1.5))]


def drop_set(cnt, how):
    kind, k = how
    if kind == "top":
        return {m for m, _ in cnt.most_common(k)}
    vals = list(cnt.values())
    if not vals:
        return set()
    mu, sd = st.mean(vals), st.pstdev(vals)
    return {m for m, n in cnt.items() if n > mu + k * sd}


def tied(cnt, how):
    kind, k = how
    mc = cnt.most_common()
    return kind == "top" and len(mc) > k and mc[k - 1][1] == mc[k][1]


def part_b(E):
    """inputs: 'none' (endpoints of all instances, no recovery), 'after' (same endpoints, an endpoint counts only if
    unrecovered), 'first' (endpoints of the unrecovered instances only)."""
    out, ties = {}, {}
    for x in E:
        for inp in ("none", "after", "first"):
            FL = {}
            for c in x.active:
                for t in x.tasks:
                    ps = x.nofmt[c, t] if inp != "first" else [p for p in x.nofmt[c, t] if not p[2]]
                    e = endpoints(ps)
                    FL[c, t] = None if not e else ((set(e[0][1]), e[0][2]), (set(e[1][1]), e[1][2]))
            pooled = {0: Counter(), 1: Counter()}; own = {c: {0: Counter(), 1: Counter()} for c in x.active}
            for (c, t), v in FL.items():
                if v:
                    for p in (0, 1):
                        pooled[p].update(v[p][0]); own[c][p].update(v[p][0])
            for name, scope, how in RULES:
                if scope is None:
                    drop = {c: (set(), set()) for c in x.active}; nt = 0
                elif scope == "pool":
                    drop = {c: (drop_set(pooled[0], how), drop_set(pooled[1], how)) for c in x.active}
                    nt = int(any(tied(pooled[p], how) for p in (0, 1)))
                else:
                    drop = {c: (drop_set(own[c][0], how), drop_set(own[c][1], how)) for c in x.active}
                    nt = sum(1 for c in x.active if any(tied(own[c][p], how) for p in (0, 1)))
                need = inp == "after"
                s = {c: sum(1 for t in x.tasks if FL[c, t] and any((FL[c, t][p][0] - drop[c][p]) and (not need or not FL[c, t][p][1])
                                                                     for p in (0, 1))) / x.T for c in x.active}
                out[x.key, inp, name] = x.score(s); ties[x.key, inp, name] = nt
    return out, ties


# ------------------------------------------------------------------ Part C
def eb(groups):
    """Empirical-Bayes shrinkage of rates k_g / n_g toward the pooled rate; strength from the between-group
    dispersion (beta-binomial method of moments). Returns {g: shrunk rate}."""
    gs = {g: kn for g, kn in groups.items() if kn[1] > 0}
    if not gs:
        return {}
    K = sum(k for k, n in gs.values()); N = sum(n for k, n in gs.values()); p0 = K / N
    if p0 in (0.0, 1.0) or len(gs) < 2:
        return {g: p0 for g in gs}
    var_obs = sum((n / N) * (k / n - p0) ** 2 for k, n in gs.values())
    tau2 = var_obs - p0 * (1 - p0) * len(gs) / N
    if tau2 <= 0:
        return {g: p0 for g in gs}                                  # no excess dispersion: full pooling
    alpha = max(0.0, p0 * (1 - p0) / tau2 - 1)
    return {g: (k + alpha * p0) / (n + alpha) for g, (k, n) in gs.items()}


def grid(x):
    A, T = x.active, x.T
    EP = {}
    for c in A:
        for t in x.tasks:
            ps = x.nofmt[c, t]
            for pop, sel in (("all", ps), ("unrec", [p for p in ps if not p[2]])):
                e = endpoints(sel)
                EP[pop, c, t] = None if not e else [(0, e[0]), (1, e[1])]
    res = {}
    for pop in ("all", "unrec"):
        occ = {c: Counter() for c in A}; unr = {c: Counter() for c in A}; tot = {c: Counter() for c in A}
        for c in A:
            for t in x.tasks:
                for pos, (s, ms, r) in (EP[pop, c, t] or []):
                    for m in ms:
                        occ[c][m, pos] += 1; tot[c][pos] += 1
                        if not r:
                            unr[c][m, pos] += 1
        keys = sorted({k for c in A for k in occ[c]})
        q = {"own": {}, "pooled": {}, "combined": {}}
        for c in A:
            q["own"][c] = {}
            for pos in (0, 1):
                for m, v in eb({m: (unr[c][m, p], occ[c][m, p]) for (m, p) in occ[c] if p == pos}).items():
                    q["own"][c][m, pos] = v
        pooledq = {k: sum(unr[c][k] for c in A) / max(1, sum(occ[c][k] for c in A)) for k in keys}
        for c in A:
            q["pooled"][c] = pooledq; q["combined"][c] = {}
        for k in keys:
            for c, v in eb({c: (unr[c][k], occ[c][k]) for c in A}).items():
                q["combined"][c][k] = v
        W = {"none": {c: defaultdict(lambda: 1.0) for c in A}, "rarity, own": {}, "rarity, pooled": {}, "rarity, combined": {}, "spread across candidates": {}}
        for c in A:
            W["rarity, own"][c] = {(m, p): -math.log(occ[c][m, p] / tot[c][p]) for (m, p) in occ[c]}
        ptot = {p: sum(tot[c][p] for c in A) for p in (0, 1)}
        share = {(m, p): sum(occ[c][m, p] for c in A) / ptot[p] for (m, p) in keys}
        for c in A:
            W["rarity, pooled"][c] = {k: -math.log(v) for k, v in share.items()}; W["rarity, combined"][c] = {}
        for (m, p) in keys:
            for c, v in eb({c: (occ[c][m, p], tot[c][p]) for c in A}).items():
                if occ[c][m, p]:
                    W["rarity, combined"][c][m, p] = -math.log(v)
        cv = {}
        for (m, p) in keys:
            rates = [occ[c][m, p] / T for c in A]; mu = st.mean(rates)
            cv[m, p] = (st.pstdev(rates) / mu) if mu > 0 else 0.0
        for c in A:
            W["spread across candidates"][c] = cv
        arms = {"all": ["no recovery", "recovery-weighted, own", "recovery-weighted, pooled", "recovery-weighted, combined"],
                "unrec": ["unrecovered instances only"]}[pop]
        for arm in arms:
            for wname in W:
                for comb in ("max", "sum over modes", "sum over endpoints"):
                    sc = {}
                    for c in A:
                        total = 0.0
                        for t in x.tasks:
                            e = EP[pop, c, t]
                            if not e:
                                continue
                            contrib = []
                            for pos, (s, ms, r) in e:
                                for m in ms:
                                    rw = q[arm.split(", ")[1]][c].get((m, pos), pooledq.get((m, pos), 0.0)) if (arm.startswith("recovery-weighted") and r) else 1.0
                                    contrib.append((pos, m, W[wname][c][m, pos] * rw))
                            if comb == "max":
                                total += max(v for _, _, v in contrib)
                            elif comb == "sum over modes":
                                best = {}
                                for pos, m, v in contrib:
                                    best[m] = max(best.get(m, 0.0), v)
                                total += sum(best.values())
                            else:
                                single = e[0][1] is e[1][1]
                                total += sum(v for pos, m, v in contrib if not (single and pos == 1))
                        sc[c] = total / T
                    res[arm, wname, comb] = x.score(sc)
    return res


# ------------------------------------------------------------------ Part D
def setup1(x):
    E = {}
    for c in x.active:
        for t in x.tasks:
            e = endpoints(x.nofmt[c, t])
            E[c, t] = set() if not e else set(e[0][1]) | set(e[1][1])
    score, ident = {}, 0.0
    for c in x.active:
        n = Counter(m for t in x.tasks for m in E[c, t]); N = sum(n.values())
        w = {m: -math.log(k / N) for m, k in n.items()}
        score[c] = sum(sum(w[m] for m in E[c, t]) for t in x.tasks) / x.T
        H = sum(-(k / N) * math.log(k / N) for k in n.values())
        ident = max(ident, abs(score[c] - (N / x.T) * H))
    assert ident < 1e-9, ident
    return x.score(score)


# ------------------------------------------------------------------ report
METHOD = r"""
# The first-and-last failure-instance study

Run on 2026-09-28 and regenerated here on the four main experiments (LiveCodeBench on its 50-task judged split).
The question: does a trace's *first* and *last* failure instance carry the ranking signal, so that a score can
ignore everything between them? Every score below is computed per candidate from its own traces, then compared
with the generalization set exactly as in `formulas.md` (Kendall tau-b, ties dropped; top-1). Exploratory: none
of these formulas is a recorded method, and Part B's rules were chosen on Models·HoVer.

## Inputs and the two preparation steps

For candidate *c* on judged task *t* the judge left a list of failure instances
`P(c,t) = [(s_i, M_i, r_i)]`: the turn `s_i`, the set of codes `M_i`, and the recovery verdict `r_i`
(`r_i = 1` if corrected or contained, `0` if unrecovered). `F` is the experiment's set of formatting codes:

| experiment | formatting codes removed |
|---|---|
@FMT_TABLE@

**Step 1, remove formatting.** For every instance keep `M_i' = M_i \ F`; drop the instance if `M_i'` is empty.
An instance no code fit keeps its pseudo-code `(uncoded)`, which is never in `F`.

    P'(c,t) = [ (s_i, M_i \ F, r_i)  for every i with M_i \ F ≠ ∅ ]

**Step 2, take the endpoints.** Order `P'(c,t)` by turn, and within a turn by the judge's listing order. The
first element is `first(c,t)`, the last is `last(c,t)`. A trace with one instance has `first = last`. A trace
with none has no endpoints and contributes 0 to every score.

## Part A: endpoints against every instance

Each row is a share of the T judged tasks (lower is better):

1. incidence, every instance: `(1/T) Σ_t 1[P(c,t) ≠ ∅]`
2. incidence, formatting removed: `(1/T) Σ_t 1[P'(c,t) ≠ ∅]`. This is also the endpoint flag without recovery,
   because a trace has endpoints exactly when `P'(c,t)` is non-empty.
3. unrecovered incidence, every instance: `(1/T) Σ_t 1[∃ i ∈ P(c,t): r_i = 0]`
4. unrecovered incidence, formatting removed: the same on `P'(c,t)`. Taking endpoints of the unrecovered
   instances gives the same flag.
5. first & last, recovery checked on the endpoints: `(1/T) Σ_t 1[r(first(c,t)) = 0 or r(last(c,t)) = 0]`. Only
   the two endpoints' verdicts are read; an unrecovered instance in the middle does not count.

@PART_A@

## Part B: fixed mode filters

A filter removes some modes from the endpoints, then the score is the share of tasks with an endpoint left.

1. For each position `p ∈ {first, last}` count how often each mode appears there:
   `n_p(m) = Σ_t 1[m ∈ M(p(c,t))]`, either **across candidates** (summed over every candidate, one count per
   mode) or **per candidate** (each candidate's own counts).
2. Choose the modes to drop at that position, `D_p`:
   *top k*: the k modes with the largest `n_p(m)`;
   *mean + k SD*: every mode with `n_p(m) > μ_p + k·σ_p`, where `μ_p` and `σ_p` are the mean and population
   standard deviation of the counts `{n_p(m)}` over the modes seen at that position.
3. Score: `(1/T) Σ_t 1[ ∃ p: M(p(c,t)) \ D_p ≠ ∅ (and, with recovery, r(p(c,t)) = 0) ]`.

Three inputs: **no recovery** (endpoints of `P'`); **recovery after** (same endpoints, an endpoint counts only
if it is unrecovered); **recovery first** (endpoints of the unrecovered instances of `P'`). † marks a tie at the
top-k cut-off (for per-candidate rules, in at least one candidate), where the dropped set is partly arbitrary.
Resolved pairs are shown when fewer than 85% of the pairs are resolved.

@PART_B@

## Part C: a grid in which every weight is estimated from the data

A task's value combines its endpoints' modes through three choices; the score is the mean task value,
`S(c) = (1/T) Σ_t V(c,t)`. All 5 × 5 × 3 = 75 combinations were run.

**Endpoint occurrences.** For position `p` and mode `m`, `o_c(m,p)` is how many of *c*'s tasks have `m` at that
endpoint, `u_c(m,p)` how many of those endpoints were unrecovered, and `N_c(p) = Σ_m o_c(m,p)`.

**Shrinkage used below (empirical Bayes, beta-binomial method of moments).** Given groups g with counts
`(k_g, n_g)`:

1. pooled rate `p₀ = Σ_g k_g / Σ_g n_g`, with `N = Σ_g n_g` and G groups;
2. observed spread `v = Σ_g (n_g/N)·(k_g/n_g − p₀)²`;
3. spread beyond binomial noise `τ² = v − p₀(1−p₀)·G/N`;
4. if `τ² ≤ 0` every group gets `p₀`; otherwise `α = max(0, p₀(1−p₀)/τ² − 1)`;
5. shrunk rate `(k_g + α·p₀) / (n_g + α)`.

No constant is set by hand: α comes from the data.

**Recovery weight `q` (5 arms).** An unrecovered endpoint has weight 1. A recovered endpoint has weight
`q = ` the consequence rate of its (mode, position), the share of such endpoints left unrecovered:

| arm | recovered endpoint weighs |
|---|---|
| no recovery | 1 (verdicts ignored) |
| recovery-weighted, own | `q_c(m,p)`: c's own rate `u_c/o_c`, shrunk across c's modes at that position |
| recovery-weighted, pooled | `q(m,p) = Σ_c u_c(m,p) / Σ_c o_c(m,p)`, one rate for every candidate |
| recovery-weighted, combined | c's rate shrunk toward the pooled rate across candidates |
| unrecovered instances only | endpoints are taken from the unrecovered instances, so every endpoint weighs 1 |

**Mode weight `w` (5 levels).**

| level | `w_c(m,p)` |
|---|---|
| none | 1 |
| rarity, own | `−ln( o_c(m,p) / N_c(p) )` |
| rarity, pooled | `−ln( Σ_c o_c(m,p) / Σ_c N_c(p) )` |
| rarity, combined | `−ln` of c's share shrunk across candidates |
| spread across candidates | `σ/μ` of the per-task rates `o_c(m,p)/T` over candidates, the same for every candidate |

**Combiner (3 levels).** With `v = w·q` for each (endpoint, mode) pair of the task:
*max*: `V = max v`; *sum over modes*: `V = Σ_m max_p v(m,p)` (a mode at both endpoints counts once);
*sum over endpoints*: `V = Σ v` (a one-instance trace counted once).

**Leave one experiment out.** For each experiment, pick the cell with the best mean tau on the other three and
report its tau on the held-out one. This is the only honest estimate of how a cell chosen from this grid would do
on a new experiment.

@PART_C@

## Part D: Setup 1, rarity-weighted endpoint modes without recovery

1. `P'(c,t)` as above (step 1) and its endpoints (step 2).
2. Endpoint modes `E(c,t) = M(first(c,t)) ∪ M(last(c,t))`.
3. Mode counts `n_c(m) = Σ_t 1[m ∈ E(c,t)]`, total `N_c = Σ_m n_c(m)`, shares `π_c(m) = n_c(m)/N_c`.
4. Weight `w_c(m) = −ln π_c(m)`: a mode common for this candidate weighs little, a rare one weighs more.
5. Task value `V(c,t) = Σ_{m ∈ E(c,t)} w_c(m)`; score `S(c) = (1/T) Σ_t V(c,t)`.

Summing step 5 over tasks gives `S(c) = (N_c/T) · H(π_c)`, with `H(π) = −Σ_m π(m) ln π(m)` the entropy of the
candidate's endpoint-mode distribution: the score is the number of endpoint modes per task times how evenly they
spread. The script checks the identity on every candidate.

@PART_D@
"""


def table_header(E, extra=""):
    return ("| | " + " | ".join(f"{SHORT[x.key]} ({len(x.active)}×{x.T})" for x in E) + " | **mean** |" + extra,
            "|---|" + "---:|" * (len(E) + 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("sharing/first_last_study.md")); a = ap.parse_args()
    E = [Exp(e) for e in MAIN if e["key"] in FMT]          # the study's four; a new experiment needs its formatting codes chosen first
    import json
    names = {}
    for x in E:
        t = json.load(open(Path(__file__).resolve().parents[1] / TAXONOMY[x.key]))
        names[x.key] = {c["id"]: c.get("name", "") for c in t["codes"]}
    fmt_rows = "\n".join(f"| {x.title} | " + (", ".join(f"`{m}` {names[x.key].get(m, '')}" for m in sorted(FMT[x.key])) or "none") + " |" for x in E)
    bar = lambda: "| *gold on the judged tasks (the bar)* | " + " | ".join(f"*{f3(x.bar)}*" for x in E) + f" | *{f3(st.mean(x.bar for x in E))}* |"
    cell = lambda r: f"{f3(r[0])}{' ·1' if r[1] else ''}"

    # A
    A = part_a(E); h = table_header(E)
    LA = ["Tau-b against the generalization set; `·1` = the formula's top candidate is the generalization set's top.", "", *h, bar()]
    for k, v in A.items():
        if k.startswith("_"):
            continue
        LA.append(f"| {k} | " + " | ".join(cell(v[x.key]) for x in E) + f" | {f3(st.mean(v[x.key][0] for x in E))} |")
    LA += ["", "Instances removed as formatting: " + "; ".join(f"{SHORT[x.key]} {A['_removed'][x.key][1]} of {A['_removed'][x.key][0]}" for x in E) + "."]

    # B
    B, ties = part_b(E)
    LB = []
    for inp, title in (("none", "No recovery"), ("after", "Recovery after: an endpoint counts only if unrecovered"), ("first", "Recovery first: endpoints of the unrecovered instances")):
        LB += [f"**{title}**", "", "| rule | " + " | ".join(SHORT[x.key] for x in E) + " | mean, 3 untuned | mean, all 4 |",
               "|---|" + "---:|" * (len(E) + 2), "| *gold on the judged tasks (the bar)* | " + " | ".join(f"*{f3(x.bar)}*" for x in E) + " | | |"]
        for name, _, _ in RULES:
            cells = []
            for x in E:
                tau, t1, n = B[x.key, inp, name]; P = len(x.active) * (len(x.active) - 1) // 2
                cells.append(f"{f3(tau)}{' ·1' if t1 else ''}" + (f" ({n}/{P})" if n < 0.85 * P else "") + (" †" if ties[x.key, inp, name] else ""))
            un = [B[x.key, inp, name][0] for x in E if x.key != "models_hover"]
            LB.append(f"| {name} | " + " | ".join(cells) + f" | {f3(st.mean(un))} | {f3(st.mean(B[x.key, inp, name][0] for x in E))} |")
        LB.append("")
    LB.append("The rules were picked by looking at Models·HoVer, so the column that tests them is the mean over the other three.")

    # C
    G = {x.key: grid(x) for x in E}
    cells = list(G[E[0].key]); tau = lambda k, c: G[k][c][0]
    mean4 = {c: st.mean(tau(x.key, c) for x in E) for c in cells}
    LC = ["**Each factor level, averaged over the other two factors** (mean tau over the four experiments; in brackets the",
          "lowest tau any cell with that level reaches on any experiment)", "", "| factor | level | mean tau | worst case |", "|---|---|---:|---:|"]
    for i, fac in enumerate(("recovery weight", "mode weight", "combiner")):
        for lv in dict.fromkeys(c[i] for c in cells):
            sub = [c for c in cells if c[i] == lv]
            LC.append(f"| {fac} | {lv} | {f3(st.mean(mean4[c] for c in sub))} | {f3(min(tau(x.key, c) for c in sub for x in E))} |")
    LC += ["", "**The twelve best cells by mean tau** (`·1` = top-1 correct)", "", "| recovery weight | mode weight | combiner | " + " | ".join(SHORT[x.key] for x in E) + " | mean |",
           "|---|---|---|" + "---:|" * (len(E) + 1)]
    for c in sorted(cells, key=lambda c: -mean4[c])[:12]:
        LC.append(f"| {c[0]} | {c[1]} | {c[2]} | " + " | ".join(cell(G[x.key][c]) for x in E) + f" | {f3(mean4[c])} |")
    LC += ["", "**Reference cells**", "", "| recovery weight | mode weight | combiner | " + " | ".join(SHORT[x.key] for x in E) + " | mean |",
           "|---|---|---|" + "---:|" * (len(E) + 1)]
    for c in [("unrecovered instances only", "none", "max"), ("no recovery", "none", "max"), ("no recovery", "none", "sum over modes"), ("unrecovered instances only", "none", "sum over modes")]:
        LC.append(f"| {c[0]} | {c[1]} | {c[2]} | " + " | ".join(cell(G[x.key][c]) for x in E) + f" | {f3(mean4[c])} |")
    LC += ["", "*unrecovered instances only · none · max* is the unrecovered incidence of Part A row 4; *no recovery · none · max* is row 2.", "",
           "**Leave one experiment out**", "", "| held out | cell chosen on the other three | its mean there | tau on the held-out experiment | bar |", "|---|---|---:|---:|---:|"]
    held = []
    for x in E:
        others = [y.key for y in E if y.key != x.key]
        best = max(cells, key=lambda c: st.mean(tau(k, c) for k in others))
        held.append(tau(x.key, best))
        LC.append(f"| {x.title} | {' · '.join(best)} | {f3(st.mean(tau(k, best) for k in others))} | {f3(tau(x.key, best))} | {f3(x.bar)} |")
    LC.append(f"| **mean** | | | **{f3(st.mean(held))}** | {f3(st.mean(x.bar for x in E))} |")

    # D
    D = {x.key: setup1(x) for x in E}
    LD = ["| experiment | candidates × judged tasks | tau vs generalization | top-1 | resolved pairs | bar |", "|---|---|---:|---|---:|---:|"]
    for x in E:
        t_, t1, n = D[x.key]
        LD.append(f"| {x.title} | {len(x.active)} × {x.T} | {f3(t_)} | {'yes' if t1 else 'no'} | {n} of {len(x.active) * (len(x.active) - 1) // 2} | {f3(x.bar)} |")
    LD.append(f"| **mean** | | **{f3(st.mean(D[x.key][0] for x in E))}** | {sum(D[x.key][1] for x in E)} of 4 | | {f3(st.mean(x.bar for x in E))} |")

    doc = METHOD.strip("\n").replace("@FMT_TABLE@", fmt_rows).replace("@PART_A@", "\n".join(LA)).replace("@PART_B@", "\n".join(LB)) \
        .replace("@PART_C@", "\n".join(LC)).replace("@PART_D@", "\n".join(LD))
    doc += "\n\nGenerated by `scripts/first_last_study.py` from the recorded judge and recovery runs; no model call.\n"
    a.out.write_text(doc); print(f"-> {a.out}")


if __name__ == "__main__":
    main()
