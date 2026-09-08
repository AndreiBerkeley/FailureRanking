# Failure-profile stability

Does a candidate's failure distribution stay the same when it is measured on
different tasks? One report per taxonomy lives in a subdirectory here, produced
by `scripts/stability.py` from two judge runs — the 50-task judging set (N) and
the 500-task generalization set (M) — under the same taxonomy, judged by the
same instrument on the same route.

## Why every number is reported against a floor

"Stays the same" is not a claim until it is measured against what sampling alone
would do. A code firing 0.1 times per trace produces about five hits across a
candidate's 50 traces, and that count moves a long way between task samples for
reasons that have nothing to do with the candidate. The report therefore builds
its own null: the M-side profile is subsampled down to N's size a thousand
times, and the resulting spread is the band a real difference has to clear.

The script refuses to print a floor when M is not several times larger than N,
because a subsample the size of its own pool has no variance and would make
every gap look significant.

## The five sections

0. **Reliability** — split N in half and check whether a code reproduces itself
   across samples from the *same* pool. Not transfer; the ceiling transfer could
   reach. A code that fails here has no stability to lose.
1. **Per-code rates** — does each code fire at the same rate on N and on M, and
   does its ordering across candidates hold?
2. **Whole-profile shape** — L1 distance between share vectors, so volume is
   divided out and only shape is compared, against the subsampling floor.
3. **Identity** — given a candidate's profile on N, is the nearest M profile its
   own? The strongest form of "the profile is a property of the candidate rather
   than of the task sample". Chance is 1/12.
4. **Carriers** — is that identity spread across the taxonomy or carried by one
   frequent code? A signature resting on a single code is a thinner claim than
   one resting on the shape. Single codes are scored by absolute rate difference,
   because a one-element *share* vector is always `[1.0]` and would make every
   pair score zero.

## Preview from the judging set alone

Before either M run finished, half-splits of the 50 judging tasks already showed
the shape of the answer. Stability tracks firing rate:

| taxonomy | codes ≥0.25/trace | median ρ | codes <0.25/trace | median ρ | profile identity |
|---|---:|---:|---:|---:|---:|
| tax-7 | 3 | +0.875 | 4 | +0.299 | 67.0% |
| tax-18 | 5 | +0.810 | 13 | +0.560 | 78.1% |

Common codes reproduce; rare ones do not — FM_005, at 0.103 firings per trace,
anticorrelates with itself at −0.337. The whole profile is a candidate signature
at eight to nine times chance, and the finer taxonomy is better at it.

That signature is distributed rather than carried by one code. The most frequent
code alone identifies a candidate 26.0% of the time (tax-7) and 24.4% (tax-18),
against 68.0% and 73.3% for the full profile. Removing it costs tax-7 twelve
points and tax-18 essentially nothing (73.3% to 73.0%) — splitting spread the
identifying information out instead of concentrating it. And shares perform as
well as absolute rates, so the signature is in the proportions, not in how many
failures a candidate makes in total.

Inputs are judge outputs only. No gold is read on this path.
