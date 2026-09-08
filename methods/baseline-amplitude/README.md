# baseline-amplitude — base failure amplitude

The floor for any method that scores a candidate from failure-mode evidence. It knows which codes
the judge assigned to each trace, and nothing else: no gold, no taxonomy text, no trace content,
no relationships between codes, no recovery, no notion of where in the program a code fired.

## Formula

For candidate `c` over its `T` judged tasks:

    A(c) = (1/T) · Σ_t |codes(c, t)|        lower is better

`codes(c, t)` is a **set**, so a code cited three times in one trace counts once and a verbose judge
cannot inflate a candidate by repeating itself. Every code weighs the same. A judged task with no
code contributes 0.

Equivalently, summing over codes rather than tasks, `A(c) = Σ_m r_m(c)` where `r_m(c)` is the share
of the candidate's judged tasks on which code `m` fired. The two readings are the same number, which
is why "mode-first with equal weights" and "task-first counting" cannot be distinguished here.

**Worked example.** A candidate on 4 tasks: `{B2, C8}`, `{}`, `{C5}`, `{B2, C5, A5}` gives
`A = (2 + 0 + 1 + 3) / 4 = 1.50`. It ranks below a candidate at 0.90.

## What it cannot see

- **Clean versus unexamined.** A task with no code contributes 0 whether the program did the work
  properly or the judge failed to look. On HoVer/tax-10 that is 4% of traces, on IFBench 28%.
- **Exposure.** A code can only fire where the candidate's own instructions or the task create the
  opportunity. Codes whose opportunity scales with instruction length therefore fire more on the
  candidates that promise more; see `analyses/pools-1-amplitude-ranking/TAX10_RESULT.md`.
- **Where a firing happened.** Splitting the same evidence by (code, step) reaches +0.50 against
  the same target where this reaches +0.06.

## Inputs

| input | path |
|---|---|
| judge mapping | `data/<benchmark>/mappings/<map-N>/mapping.jsonl` |
| validation target | `data/<benchmark>/outcomes/cap-*.jsonl` restricted to a `pools-1` portion |

Repeat 0 and `status: judged` only. Gold is read after scoring, for validation.

## Run

```bash
python3 methods/baseline-amplitude/scripts/score.py --benchmark hover --mapping map-5 \
    --out results/hover/map-5/baseline-amplitude
```

## Results — HoVer, against gold on the 500-task generalization pool

| mapping | taxonomy | judged tasks | tau-b | permutation p | 95% task bootstrap |
|---|---|---:|---:|---:|---|
| `map-5` | tax-10, 10 codes | 50 | **+0.06** | 0.84 | [−0.23, +0.20] |
| `map-3` | tax-18, 18 codes | 50 | **+0.02** | 1.00 | [−0.24, +0.09] |

The bootstrap resamples the 50 judged tasks, so it measures how much of the number is the choice of
tasks. Both intervals straddle zero: on this evidence amplitude is indistinguishable from a random
ranking, on either taxonomy.

## Reference points on the same target

| | tau-b |
|---|---:|
| gold on the same 50 judged tasks (the ceiling for a 50-task block) | +0.78 |
| gold on 100 judged tasks | +0.72 |
| gold on the whole 500-task judging pool | +0.76 |
| instruction word count, longer is better | +0.64 |
| **base amplitude** | **+0.06** |
| a random ranking | 0.00 |

A method that reads failure modes has to beat +0.06 to justify the taxonomy, and +0.64 to justify
reading traces at all rather than counting words in the prompt.

## Status

Frozen 2026-09-08. One formula, no parameters, nothing fitted. When `map-6` (tax-10 on the second
50-task block) lands, this table gains a row and a pooled 100-task row; the formula does not change.
