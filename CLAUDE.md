# FailureRank — Ranking Candidates from Non-Gold Failure Evidence

## Mission

Andrei's PhD-track research (advisor Mert, UC Berkeley). Given N candidate
agent systems and M tasks, rank and score the candidates using only
structured failure evidence extracted from execution traces — **no gold
answers anywhere in the scoring path**. Pipeline: failure identification →
recovery analysis → aggregation into a candidate score.

## Two boundaries — never cross them

These took months to converge on; proposals violating them are rejected:

1. **The contribution is NOT the taxonomy or the judge.** Those are
   inherited, replaceable instruments (AdaMAST/MAST taxonomies,
   taxonomy-conditioned annotators). The contribution is *what gets
   measured* and *how measurements aggregate* into candidate quality,
   conditioned on the evaluation scenario. Never propose "build a better
   judge" — already considered and rejected.
2. **The LLM never emits the verdict.** It asserts local, falsifiable
   micro-claims; the verdict/score is computed deterministically over that
   structure. This separates the work from ordinary LLM-as-a-judge.

## The framework (Andrei's notes, 2026-08-07 — the working structure)

### Layer 1 — instrument trust (error sources bounding any score)
1. **Trace-subset quality** — distance between the scored subset's
   failure-mode distribution and the general test/use population.
2. **Judge quality** — failure modes missed or improperly assigned.
3. **Recovery quality** — false positives / false negatives in recovery
   detection.
4. **Taxonomy quality** — coverage + clarity + relevance of failure modes.

### Layer 2 — the effect of a failure mode
A function over these rubrics (scenario-dependent; some may be ignored):
1. **Unique task appearances** (dedup per task) as % of evaluated tasks.
2. **Total recovery per task** — unique tasks where ALL appearances of the
   mode recovered, as % of evaluated tasks.
3. **Partial recovery per task** as % of evaluated tasks.
4. **Mode–recovery relations** — co-occurrence effects (if A and B appear
   together 10% of the time and always recover then, how does that modulate
   each mode's individual effect).
5. **Human/gold-authored rules** — e.g. "mode X ⇒ task always failed";
   supersedes the other rubrics.
6. **Coefficients & variance of appearance** — estimated on equal splits of
   the training set, to know what distribution to expect on generalization.

### Layer 3 — candidate score
1. Combination of the per-mode effects.
2. Weighted by evidence volume — the number of tasks evaluated on.

### Conditioning axis — the estimand (scenario picks the formula)
N eval tasks used for scoring; M test tasks; K seeds:
1. **Best on the N tasks themselves** → N × best-of-N judging events.
2. **Best expected across K seeds, observing one seed** → de-noising;
   rubric 6 central.
3. **Best on unseen M from evidence on N** → generalization; discount
   high-variance modes even with large in-sample effect.
Combinations (e.g. 2+3) likely reduce to scenario 3's ranking. Each
scenario probably needs a different formula, at least in part.

## Root documents (the project's four anchors + this brief)

AUTHORITY DIRECTION: these local .mds are the single source of truth —
Andrei updates the external Google Doc FROM them; nothing syncs inward.
Keep them current above all else.

- `IDEA.md` — the general presentation: abstract, pipeline, scenarios,
  component-isolation study, supervision regimes, core contribution.
- `TIMELINE.md` — the experiment ledger: exact date/time, experiment
  setup, and paths to that experiment's logs/results/traces. Currently
  EMPTY by Andrei's decision — its content and format will be decided
  with him later. Do not write to it unprompted; no official run exists
  until it has a timeline entry.
- `LITERATURE.md` — the library, filed by purpose (candidate failure
  evaluation, reliability measurement, generalization & ranking,
  statistical foundations, mathematical foundations, …). Every paper read
  gets filed with: link, main idea, gold availability, why we care.
- `PARKING.md` — untested methods and ideas we can't pursue on the spot
  but must not lose. Dated entries; promotion into actual method changes
  or experiments happens via TIMELINE.md.

## Resolved questions (per IDEA.md — don't reopen)

- **Gold boundary:** both supervision regimes are studied explicitly —
  gold-calibrated (gold helps learn evidence→quality offline; selection
  stays outcome-free) and fully gold-free (gold only for research
  evaluation). See IDEA.md §6.
- **Scoring semantics:** scores are computed independently per candidate,
  deterministically, from structured annotations; ranking derived after.
  E001's exact formulas are frozen in TIMELINE.md.

## Open before E001 launches (Andrei decides; surface, don't resolve)

- Benchmark + trace source (from-zero rule; candidate option: Track 1's
  SWE-Bench artifacts once available). δ grid, split sizes, K.
- How Andrei's six effect rubrics (above) map onto post-E001 experiments —
  E001 deliberately uses only prevalence + complete recovery.

## Workspace layout — clean/trials split (strict)

- `core/` — CLEAN. The formalization, scoring implementation,
  instrument-quality metrics. Paper-grade, tested, reviewed. Nothing lands
  here without Andrei's approval of the design it implements.
- `experiments/` — OFFICIAL runs only, one folder per timeline entry:
  `experiments/E<nnn>-<slug>/{config,logs,traces,results}/`. Every folder
  corresponds to a TIMELINE.md entry, created at launch.
- `trials/` — EXPLORATION. Anything goes, but logging is mandatory: every
  trial is `trials/YYYY-MM-DD-<slug>/` with a `README.md` stating
  hypothesis, setup, result, conclusion (even negative). `trials/INDEX.md`
  gets one line per trial. An unlogged trial is a rule violation.
- `data/` — immutable inputs (trace bundles, taxonomies, manifests);
  provenance recorded in `data/SOURCES.md`.
- `docs/` — formalization drafts, findings; `PROGRESS.md` and
  `DECISIONS.md` at repo root, same conventions as the GEPA track.

## From-zero rule

Everything starts from zero. Prior experiment folders
(`~/Desktop/certification_analysis`, `~/Desktop/GEPA_Experiments`) are
IGNORED — no data, code, or results inherited from them. The AdaMAST
public repo remains available as the taxonomy/annotation instrument (a
tool, not a prior experiment). Track 1 (`~/Desktop/GEPA`) will produce
multi-candidate SWE-Bench traces + a certified taxonomy + gold outcomes —
a candidate input for E001; keep trace-format compatibility in mind.

## Hard rules

1. **Never launch billed runs** (anything spending API tokens). Prepare
   code + exact command in a ```bash block with a cost estimate; Andrei
   launches. Free offline work (parsing existing traces, unit tests,
   simulations over recorded data, schema checks) is fine to run directly.
2. Git repo at the workspace root from the first commit; small clean
   commits; the history is part of the artifact.
3. Gold labels in existing data may be used ONLY to *validate* rankings
   after the fact or to calibrate rubrics 5–6 offline — never inside the
   scoring path. Enforce the separation structurally (separate modules,
   and a test proving the scoring path never reads gold fields).
