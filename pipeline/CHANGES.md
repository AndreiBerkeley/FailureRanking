# Local changes vs upstream AdaMAST

Upstream: AdaMAST-private @ d55225fe6398730e4030c8469eacf901b8fd5fc3 (v0.2.2.1).
Prompt assets only; no Python code is modified. Rationale for each change is in
TIMELINE.md (AdaMAST pipeline audit entry) and METHODOLOGY.md.

## 1. assets/category_c_domain_seeded.md

Removed the subdomain coverage quota ("verify you have at least one code
relevant to each subdomain... add a code"), which mandated inventing one mode
per task topic regardless of evidence. This was the mechanism behind
topic-indexed, zero-support modes (livebenchmath tax-1: 16 of 27 modes died
at the grounding freeze). Replaced with an evidence rule (codes only where
sample traces exhibit the pattern; scaffolding is context, never a quota) and
a naming rule (a code names the candidate's action, never the task's subject).

## 2. assets/category_c_common_header.md

Appended four exemplar codes showing the desired shape, endpoint-judgment
flavored: Asserts_Unverified_Intermediate_Conclusion,
Requirement_Silently_Dropped, Confident_Fabrication_At_Capability_Limit,
Answer_Disconnected_From_Work. Marked illustrative-only, with an explicit
instruction not to copy them without trace evidence. Behavior-named, no task
topics, no consequences alone, no remedies.

## Unchanged on purpose

Category A lists, B-stage role guidance, boundary fields
(when_to_use / when_not_to_use), agreement gating, and all Python code.
Mode-level severity remains generated but is inadmissible downstream
(usage decision, see TIMELINE.md).

## 3. pipeline/structure.py (code change)

Step 2 (structure extraction) now honors ADAMAST_STRUCTURE_FILE: when set, the
JSON file it points to is validated for the four expected keys and returned
directly, skipping agent extraction and LLM role inference entirely. Rationale:
inference invented phantom roles on single-module programs (livebenchmath tax-1
carried Coordinator, Checker, and Pipeline_Routing modes for a program with one
module), and the B stage builds code families per discovered role, so structure
errors propagate into the vocabulary. The true program structures are known and
are supplied per benchmark from runs/taxgen-v2/structures/. Manual structure
describes the arena, not the candidates; the executions-only evidence rule is
untouched.

## 4. assets/a_failure_categories.md

Removed the "INSTRUCTION COMPLIANCE" lens from the A category list (item 6;
the tool item renumbered). Ignoring the task's constraints is quality-of-work
or reasoning territory (B/C), not infrastructure, and the double lens produced
duplicate instruction codes in ifbench tax-1 through two categories at once.
Recorded reading of the split (generality ladder): A codes vary with neither
agent nor task; B codes vary with the agent role; C codes vary with the
domain, named for the act of solving, never the topic.

## 5. assets/category_ab_requirements.md, assets/category_c_requirements.md

Appended the mode style contract (endpoint judgment, not feedback): name as an
act rather than a lack; definition is a fact pattern with quality words banned
unless observably grounded; every code carries an observability license (a
judge must be able to quote trace text satisfying it); boundaries discriminate
by observables, never intent or outcome; no remedy, routing, or advice; no
consequence in the identity.

## 6. pipeline/prompts.py (code change, B role guidance text)

The vague quality list fed to the B generator ("poor quality output,
superficial work, inappropriate method") is replaced with observable forms:
output contradicts its own input; asserts what the trace does not contain;
omits what the task or upstream stage stated; restates input without the
role's transformation.

## 7. traces/signals.py (code change)

Signals now scan only candidate-authored text: assistant messages when
present, otherwise the [ASSISTANT] sections of the flattened trajectory.
Scanning whole traces made retrieved documents fire signals ("killed" inside
a movie title counted as a process error; passage repetition flagged 100
percent of hotpotqa traces). The oom/killed error pattern is additionally
word-bounded and context-anchored ("boomers", "Boombox", "the Room" were
matching as substrings). After the change, phantom process errors on hotpotqa
fall from 73 traces to 0 and repetition from 204 to 34; livebenchmath is
unchanged, as it should be.

## 8. pipeline/check.py, assets/fix_category_{a,b,c}.md, assets/checker_terms.json

The step 8 checker re-created the coverage quota killed in step 5: it computed
"coverage gaps" (A keyword families, B roles, C subdomains) and its fix
prompts instructed "New codes for coverage gaps", inventing codes without
evidence at the final step. Gaps are now computed and logged as informational
only, never filled; the gap-invention bullet is removed from all three fix
prompts. Overlap merging and definition-quality fixes are untouched. Also
removed "format violation" from the keyword list that moves B codes into A:
violating a requested format is instruction-compliance territory, which was
removed from the A lens; "malformed output" (unparseable) stays A.

## 9. core/taxonomy_data.py (code change)

Taxonomy.from_flat now maps when_to_use / when_not_to_use from flat code
entries. Upstream dropped them, so a taxonomy fed to the reflection judge for
refinement lost exactly the boundary guidance the mode style contract depends
on for consistent application.

## CORRECTION: changes 1-9 targeted a dead code path

Changes 1 through 9 above were applied to `adamast/learning/vendor/pipeline/`,
which the CLI never loads. The live path for `adamast generate` is
cli.py -> foundation_cli.main_generate -> learning/api.py ->
**learning/pipeline/draft.py** (draft construction) and
**learning/pipeline/agreement.py** (the annotation gate). draft.py is a
self-contained 4200-line module with its own inlined copies of every prompt
and helper. The vendor tree is legacy.

All changes are now re-applied to learning/pipeline/draft.py:
manual structure hook (ADAMAST_STRUCTURE_FILE) in TraceStructureExtractor;
signals scan candidate-authored text only (_get_trajectory splits [ASSISTANT]
sections, _get_trajectory_full keeps the old behavior); oom/killed pattern
word-bounded and process-anchored; INSTRUCTION COMPLIANCE removed from the A
category list; subdomain coverage quota replaced with an evidence rule and a
behavior-not-topic naming rule; B role guidance rephrased to observables;
coverage gaps made log-only at both prompt and code level in TaxonomyChecker;
mode style contract plus the four exemplars inserted into both C headers and
the A and B stage prompts.

The vendor-tree edits are left in place (harmless, and the reasoning is
identical) but they are not what runs. generate.sh now preflights the LIVE
module and refuses to spend tokens unless every change is present.

## 10. draft.py: domain analysis retries, then fails loudly

extract_json returns {} on any parse failure, and SystemDomainAnalyzer.analyze
passed that straight through: a run whose step 1 returned nothing continued
with "Domain: Unknown, Subdomains: []", silently stripping domain grounding
from the C stage while still costing money. analyze now retries three times
and raises if no domain object is parsed, so a degraded run cannot look like a
successful one.

## Structure files: shapes the live code requires

learning/pipeline/draft.py indexes into structure_info sub-objects as dicts.
runs/taxgen-v2/structures/*.json must therefore use:
  trace_format.key_fields          list of {field_name, description}
  architecture.critical_handoffs   list of {from_agent, to_agent,
                                            what_is_passed, failure_risk}
Domain-info consumers additionally require correctness_criteria entries shaped
{criterion, description}. Passing bare strings raises AttributeError mid-run,
after tokens are spent. generate.sh preflight now instantiates CategoryGenerator
for A, B, and C and calls all nine context builders, which reproduces any such
crash for free before launch.

Note on the preflight's own history: its first version passed domain_info and
structure_info in the wrong argument order (the signature is
(client, category, domain_info, structure_info, trace_signals)), so the
architecture builder read an empty dict and reported success on a structure
file that in fact crashed the run. Fixed, with a negative test confirming a
malformed structure file is now rejected before any spend.

## 11. draft.py + agreement.py: retry transient LLM failures

Upstream call_llm logged and re-raised, with no retry anywhere in the stack,
so one transient 503 silently degraded whatever step it hit. Observed: a
hotpotqa run lost its A-code overlap-merge pass to a single 503 (the caller
catches and returns codes unchanged, so the run continued and looked fine).
Both live call_llm functions now retry up to 5 times with exponential backoff
(5s doubling) on transient conditions only (503, UNAVAILABLE, 429,
RESOURCE_EXHAUSTED, rate limit, overloaded, timeout, temporarily);
non-transient errors still raise immediately.

## 12. agreement.py: annotators were shown ~5 percent of each trace

The single most damaging defect found so far. Two cuts compounded on the
generic trace path (the one our corpora take):

  TraceParser generic fallback   raw_trajectory[:2000]
  ErrorDiscovery._format_trace   that content[:500], plus raw[:1000] excerpt

A 29,260-char hotpotqa trace reached the annotators as roughly 1,500
characters, cut mid-word. All four annotators then unanimously reported a
truncation failure, so kappa came out 1.000 on a harness artifact while our own
mechanical scan reported Truncated: 0/204. Round 1 used 1 of 22 codes on
hotpotqa and 2 of 18 on livebenchmath, dominated by the truncation code, with
zero learned rules and zero low-agreement codes because there was nothing to
disagree about.

Fix: module-level budgets (MAX_RAW_TRAJECTORY_CHARS 48000,
MAX_AGENT_OUTPUT_CHARS 16000, MAX_FINAL_ANSWER_CHARS 4000) and an `elide`
helper replacing every hard slice on the paths our traces take. Elision keeps
head and tail and inserts an explicit marker naming the evaluation harness as
the cause, so a cut we make can never again be read as the model stopping
early. The renderer also drops the duplicate section it used to emit (the
fallback path's single agent output IS the raw trajectory, so the trace was
being sent twice).

Verified offline on both corpora: annotators now receive 100 to 101 percent of
every trace, 0 of 408 traces require elision at these budgets, and traces end
on real content (a completed derivation; a final document field) rather than
mid-word.

## 13. api.py + foundation_cli.py: generation no longer runs the agreement gate

`adamast generate` is documented as producing an "agreement-gated taxonomy": it
runs draft generation and then the full four-annotator MATRS pass. Two problems
under `PIPELINE.md`.

It spends the measurement on a vocabulary that is about to change. `PIPELINE.md`
states the rule directly: "Refinement precedes certification. Certifying a
vocabulary that is about to change wastes the measurement, and the gate is the
more expensive step." Generation did exactly what that rule forbids.

And because MATRS refines as well as measures, generation was not a generation
step at all. It was a hidden refine-and-measure cycle sitting on top of the
explicit ones, so every cycle contained two refinements: ours, and MATRS's.

`generate_taxonomy(run_agreement=False)` and the `--no-agreement` CLI flag emit
the draft with `status: "draft"` and `agreement: {"skipped": true}`.
`taxonomy/stages.py` passes the flag by default.

Cost: one full agreement pass per benchmark per run. Measured on the 2026-08-29
runs, generation's own MATRS ran 5 rounds of 4 annotators plus calibration.

## 14. stages.gate: the codebook is captured rather than discarded

The agreement run produces a codebook of deliberated disambiguation rules and
anchor examples, and the kappa it reports was reached with that codebook in
every annotator's context. Generation used to attach it to `taxonomy.json`;
with change 13 generation no longer produces one, so the cycle gate is the only
source. It was previously computed and thrown away here.

`stages.gate` now keeps the pipeline object, calls `build_codebook`, and returns
the codebook in the summary; `run.py` attaches the certifying cycle's codebook
to the shipped taxonomy. Without it a downstream judge applies the codes under
easier-to-confuse conditions than the ones measured.

## 15. taxonomy/preflight.py: refuse to run a pipeline whose changes are missing

See "CORRECTION: changes 1-9 targeted a dead code path". The preflight that
caught that lived in a superseded shell script, so the pipeline module had none.
`taxonomy/preflight.py` checks that every module resolves inside `pipeline/`
(not `learning/vendor/`, not the upstream checkout) and that each local change is
present in the file actually imported, identified by a marker phrase.

Markers are whole phrases, never bare identifiers: a bare identifier is a
substring of any renamed version of itself, so appending to it would not trip
the check. That exact mistake was made and caught while writing this.

`run.py` calls `preflight.assert_ready()` before spending anything.

## 16. agreement.py: the gate measures, it does not rewrite the taxonomy

`Config.INTERNAL_REFINEMENT = False`. The agreement run used to rewrite codes
between rounds whenever kappa fell short, then report a kappa measured on the
rewrite. FailureRank hands the gate a taxonomy and ships the one it handed in,
so that number certified an artifact that does not exist.

Observed on the 2026-08-29 livebenchmath cycle-1 gate. Round 3 fell to 0.654, the
gate rewrote C.1, rounds 4 and 5 scored 1.000 on the rewritten C.1, and the
shipped taxonomy carries the original. The reported certification was `kappa 1.0`.

A round below target is now a finding about the codebook, logged and left in the
kappa history, for the pipeline's own audited panel to act on. Refinement happens
in exactly one place.

## 17. stages.gate: certify on pooled kappa, not the last round

Enabled by change 16. While the taxonomy was rewritten between rounds each round
measured a different instrument, so only the terminal round could be reported --
and rounds shrink, so the certification landed on the smallest sample the run
produces. livebenchmath certified on 5 reconciled errors after observing 37.

With the taxonomy fixed, all rounds measure one instrument and their subjects
combine. `pooled_kappa()` rebuilds the subject set from every round's saved
`typed_errors` and `assignments`, namespacing ids as trace_id + error_id exactly
as the per-round computation does. Trace ids are unique across rounds, so this is
the same statistic over more data, not an average of averages.

Recomputed over the completed cycle-1 gates:

| benchmark | last round | pooled |
|---|---|---|
| livebenchmath | 1.000 (n=5) | **0.820 (n=37)** |
| hotpotqa | 0.961 (n=17) | **0.980 (n=68)** |

The per-code detail is the point. livebenchmath's C.1 pools to **-0.007**, below
chance -- and C.1 is the code the gate rewrote. The statistic surfaces exactly
what the old one concealed.

`codes_exercised` is counted from the assignments, never from the per-code kappa
keys: a code no annotator ever assigned still receives a kappa, because everyone
agreeing it does not apply reads as agreement. Counting those would claim
evidence we do not have. Measured honestly, both gates exercised 7 codes, of 16
and 20 respectively.
