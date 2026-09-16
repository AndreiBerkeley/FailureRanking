# tax-15 — tax-14 plus one hand-authored code

**tax-14 plus `SP_15`, and nothing else changed.** All 14 tax-14 codes carry over
byte-identical, so their rates stay directly comparable between a tax-14 pass and a
tax-15 pass, and any movement in them is attributable to `SP_15` absorbing points that
previously went elsewhere. That comparability is the reason this artifact adds exactly
one code.

## SP_15 — CONCLUSION_UNLICENSED_BY_SUPPLIED_EVIDENCE (domain)

The agent states a conclusion the supplied passages do not establish, while reading those
passages correctly and importing no outside fact. Three recurring situations: silence read
as confirmation (argument from ignorance), one verified conjunct taken to verify a whole
multi-part claim, and a confident verdict whose own reasoning admits the decisive evidence
is missing.

It is bounded against the three codes it sits between:

| not this | because |
|---|---|
| `SP_01` | that fires on an imported fact; the failure is the import, not the inference |
| `SP_02` | that fires on a misreading; there, the conclusion may follow validly from it |
| `SP_13` | that fires on **propagating** a claim asserted in an earlier turn; `SP_15` requires the agent to originate the unsupported step itself, from material containing no such claim |

The `SP_13` boundary is the load-bearing one, and it is why this is a new code rather than
a widening of `SP_13`. `SP_13`'s mechanism is inheriting an unvalidated claim — something
must exist to propagate. Argument from ignorance manufactures the claim from the absence
of its negation; nothing is inherited. Widening `SP_13` would have merged a validation
failure with an inference failure, whose remedies point in opposite directions (add a
verification step vs. calibrate inference), and would have cost the per-model rate its
ability to say which. The distinction is also mechanically testable on the trace — is
there an upstream assertion the agent picked up? — so it is cheap to judge.

## Why it was written by hand, and what must not be done with the motivating points

`SP_15` was authored on 2026-09-09, not induced by `new_pipeline`. Taxonomies are
instruments here, not the contribution, and tax-14 already carries hand amendments — but
this is a larger step than a wording amendment and is disclosed as such.

It was motivated by the 51 points `pointjudge-1` reported as fitting no tax-14 code
(`analyses/models-1-format-codes/`), 42 of which are this mechanism, spread across all
nine solver models and landing 44/51 on `summarize1`/`summarize2` where verdicts form.

**Those 51 points justify the code. They are not occurrences of it.** They came from a
reading that was not looking for this mechanism, so their rate is an undercount that is
uneven across models, and they carry no blind-reader corroboration of the kind every other
code has. Counting them would give `SP_15` a rate incomparable with the other codes and a
reliability that is simply unknown. `SP_15`'s rate must come from a judge pass run with
this taxonomy in view.

## Deliberately still uncovered

| gap | points | why not coded |
|---|---:|---|
| step-objective misconstrual | 6 | largely `SP_03`'s mechanism seen in the reasoning field; fixing it means widening `SP_03`, which would break the comparability above. Parked for `tax-16`. |
| word-level generation corruption | 2 | too rare |
| key order inside well-formed, parseable JSON | 1 | too rare; no parse consequence |
