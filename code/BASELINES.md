# The baseline methods

Every entry here has been run. Each reads the judge's mapping and nothing else, produces
one number per candidate from that candidate's own traces, and isolates a single idea.
None combines two ideas, and none has a parameter that could be tuned.

## Notation, defined once

| symbol | meaning |
|---|---|
| `c` | a candidate |
| `t` | a judged task; every candidate is judged on the same ones |
| `T` | how many tasks were judged for `c` |
| `M` | the taxonomy's set of codes |
| `S` | the program's steps |
| `codes(c,t)` | the set of distinct codes the judge assigned to `c`'s trace for task `t` |
| `codes(c,t,s)` | the subset of those placed at step `s` |
| `k(c,t)` | how many distinct codes are in that set |
| `r_m(c)` | the share of `c`'s judged tasks on which code `m` fired |
| `g(c,t)` | the gold outcome of `c` on `t` |

A code cited three times in one trace counts once, so a repetitive judge cannot inflate a
candidate. A judged task with no code contributes zero; an unjudged task contributes
nothing rather than zero.

---

## 1. Gold — the reference

Not a competitor. It reads outcomes, so it can never be part of a trace-based claim. It
says how much a perfect trace reader could hope for on this many tasks.

    A_gold(c) = (1/T) · Σ_t g(c,t)                          higher is better

## 2. Amplitude — how much goes wrong

Counts codes. Does not know where they fired, what they fired with, or whether they cost
anything.

    A_amp(c) = (1/T) · Σ_t k(c,t)  =  Σ_m r_m(c)            lower is better

The two readings are the same number, which is why mode-first and task-first counting
cannot be separated at this level.

## 3. Incidence — did the task fail at all

One per failing task regardless of how much went wrong on it. Separates a candidate that
ruins a few tasks from one that lightly marks many, which amplitude adds into the same
total.

    A_inc(c) = (1/T) · Σ_t 1[ k(c,t) > 0 ]                  lower is better

## 4. Breadth — how many different things go wrong

Variety rather than volume. A candidate with one recurring weakness scores better than
one that produces every code occasionally, even at equal amplitude.

    A_bre(c) = | { m ∈ M : r_m(c) > 0 } |                   lower is better

## 5. Worst mode — the single most common failure

The peak of the profile rather than its total. Answers whether a candidate is
characterised by its most frequent weakness.

    A_wor(c) = max_{m ∈ M} r_m(c)                           lower is better

## 6. Combinations — every co-occurring subset counts

The co-occurrence reading. A task showing three codes contributes seven entries, one for
each non-empty subset, so failures landing together on one task cost more than the same
failures spread across three tasks.

    A_comb(c) = (1/T) · Σ_t ( 2^{k(c,t)} − 1 )              lower is better

**Why this rather than counting codes.** Counting each code separately is amplitude,
exactly. This grows exponentially in the per-task count, so it is the crudest form of
"failures that arrive together are worse" that is not already amplitude.

## 7. Distinct patterns — how many different code sets appear

Identity rather than size. Two candidates producing the same amount of failure can repeat
one signature combination or produce a different combination every time.

    A_pat(c) = | { codes(c,t) : t judged, codes(c,t) ≠ ∅ } |    lower is better

**Caveat.** This count grows with `T`, so it is comparable only across candidates judged
on the same number of tasks, and never across judging sets of different size.

## 8. Step-attributed amplitude — where it went wrong

The same evidence as amplitude with the location attached, so a code firing at two steps
is two units and a code firing at one step is one.

    A_step(c) = (1/T) · Σ_t | { (s,m) : s ∈ S, m ∈ codes(c,t,s) } |    lower is better

**Every step weighs the same.** No terminal step, no discount, no per-program weighting.
It answers only whether locating a failure adds anything over observing it.

**Precondition.** Every firing must carry a step. A judge that places only some of its
findings turns this into a measurement of its own placement coverage.

## 9. Recovery-discounted amplitude — did the failure cost anything

**Reads gold, and must always be declared as doing so.** It bounds how much the recovery
component can carry rather than competing with outcome-free scores.

With `app_m(c)` the judged tasks where `m` fired and `rec_m(c)` those the candidate passed
anyway:

    w_m(c)   = 1 − rec_m(c) / app_m(c)
    A_rec(c) = Σ_m w_m(c) · r_m(c)                          lower is better

A code that only ever appears on tasks the candidate still passes gets weight zero and
drops out. When nothing is ever recovered this reduces to amplitude exactly.

**Support.** Fix a minimum for `app_m(c)` and report how many codes fell below it, rather
than letting a code seen twice set a weight.

## 10. Containment-discounted amplitude — did anything follow it

The gold-free counterpart of entry 9. Entry 9 asks whether a failure cost the outcome;
this asks whether the program itself carried the trouble forward.

Let `down(s)` be the steps that consume step `s`'s output, directly or through the
harness, read off the traces rather than from anyone's reading of the program. A firing
at step `s` in task `t` is **contained** when `down(s)` is non-empty and no code fired at
any step in `down(s)` on that trace. Firings at a terminal step are never contained,
because nothing ran afterwards and observing no downstream failure says nothing.

    A_con(c) = (1/T) · Σ_t | { (s,m) : m ∈ codes(c,t,s), (s,t) not contained } |

    lower is better

**Parameter-free by construction.** A contained firing contributes zero and every other
firing contributes one. Any graded discount by how many downstream steps stayed clean
introduces a strength parameter and makes it a method rather than a baseline.

**Precondition.** As with entry 8, every firing must carry a step, and here the
dependency graph must be derived as well.

**Tension to note.** Dropping contained firings discards evidence, which cuts against the
rule that a formula should weigh everything. It is a conditional drop rather than a
selection of steps decided in advance, but the tension is real and this entry is the only
one in the list that has it.

## 11. Calibration — the floor and the ceiling

Not a method and never reported as one. Two numbers every result is read against.

- **Floor.** A random ranking, expected agreement zero.
- **Ceiling.** Gold on the judged tasks against gold on the target set. No trace-based
  score should be expected to beat the outcome measured on the same tasks.

---

## Run but not kept

These were computed and are not in the baseline set, because each is a parameterised or
combined form of something above rather than a separate idea.

| variant | why it is out |
|---|---|
| saturated blame `1 − 2^(−k)` | a parameterised interpolation between incidence and amplitude |
| capped blame `min(k,3)/3` | same, with the cap as the parameter |
| persistent modes, `r_m ≥ 0.2` | breadth with a threshold |
| recurring combinations, recurring patterns | combinations and patterns with an occurrence threshold |
| rate-weighted combinations | weights each entry by its own rate |
| mean pattern size | identical to amplitude |
| recovery with (code, step) as the unit | combines the recovery and location components |

## Reporting

Each is reported alone, on the same judged tasks, against the same target, with the same
metric. The deliverable is a table of the eleven. Any combination of two is a separate
proposal to be argued on its own.
