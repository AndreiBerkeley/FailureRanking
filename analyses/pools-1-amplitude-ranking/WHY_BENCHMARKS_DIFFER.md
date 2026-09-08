# Why a counting method agrees with gold on one benchmark and not another

2026-09-08. Reads `brute_all.json` together with three per-benchmark measurements.

## What "beats gold 50" compares

The `vs gold 50` column is agreement with gold on the same 50 tasks the judge read. The ceiling,
gold 50 vs gold generalization, is how far that 50-task gold predicts the wider pool. A method
that exceeds the ceiling in the gold-50 column has agreed with a ranking that does not itself
transfer; the transferable comparison is the `vs generalization` column against the ceiling, and
nothing exceeds the ceiling on any benchmark.

## Three conditions, measured

| condition | hover/tax-18 | hover/tax-10 | ifbench | hotpotqa |
|---|---:|---:|---:|---:|
| (a) codes see failure: extra codes per task on failing vs passing tasks, within candidate | +0.10 | **+0.42** | **+0.58** | **−0.17** |
| (b) gold 50 predicts generalization (ceiling) | +0.78 | +0.78 | 0.00 | +0.36 |
| (c) confound: tau(gold 50, instruction length) | +0.81 | +0.81 | +0.03 | +0.37 |

**IFBench.** (a) is strong: constraint violations are exactly what the judge can see, and a failing
trace carries 0.58 more codes than a passing one. So on the same 50 tasks a candidate with more
failing traces has more codes, and combinations-all reaches +0.43 against gold 50. But (b) is zero:
the 50-task gold spread is 0.19 and the 400-task spread is 0.056, so the ranking the method
recovers is sample noise, and against generalization it gives −0.03. Same-task agreement, no
transfer. The judge is right about traces and there is nothing about candidates to be right about.

**HotpotQA.** (a) is inverted: codes fire *more* on passing tasks. The mechanism that decides gold,
a correct answer given as a sentence, has no code, while the format codes fire on the rich-instruction
candidates whether or not the task fails. Every counting method is therefore negative, −0.4 to
−0.7. The one positive cell, breadth at +0.53 against gold 50, rests on two codes that fired twice
each in 600 traces: whether a candidate shows 5 or 6 distinct codes is decided by four firings.

**HoVer.** (a) holds under tax-10 (+0.42, up from +0.10 under tax-18, so the re-levelling made the
judge see failure), and (b) is the only real ceiling. What cancels it is (c): gold tracks
instruction length at +0.81, the exposure-driven codes track it the other way, and the sum lands
near zero.

## The trivial baseline everything must beat

Instruction word count, longer is better, as a score:

| | vs gold 50 | vs generalization |
|---|---:|---:|
| hover | +0.81 (p<.001) | **+0.64 (p=.003)** |
| ifbench | +0.03 | 0.00 |
| hotpotqa | +0.37 | −0.08 |

On HoVer, counting the words in a candidate's instructions beats every brute method against the
generalization gold, and is the only significant positive number on that benchmark. Any method that
claims to rank HoVer from traces has to beat +0.64, and has to do so without reading the
instructions' length.

## What decides success

Whether the taxonomy contains the mechanism that actually drives gold. IFBench: yes, and the
candidates do not differ. HotpotQA: no, the deciding mechanism is uncoded and the coded ones are
exposure artefacts. HoVer: yes, contaminated by exposure.
