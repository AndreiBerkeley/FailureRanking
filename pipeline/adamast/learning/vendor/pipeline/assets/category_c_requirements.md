REQUIREMENTS:
1. Each code describes an ERROR TYPE (not an error instance) — it should apply across
   many problems, not just one specific scenario
2. Each code must be DETECTABLE by a judge reading the trace — the judge should NOT need
   to solve the problem independently or know the correct answer
3. Each code must be DISTINGUISHABLE from every other code — if two codes cannot be told
   apart by a judge, merge them
4. Do NOT include system failures (A codes) or role-specific failures (B codes)
5. C codes must NEVER reference agent roles (${active_roles})
6. detection_heuristics must describe what a judge would look for in the trace text
7. Definitions should be concise and clear
8. Prioritize clarity over quantity — fewer clear codes is better than many overlapping ones

MODE STYLE CONTRACT (endpoint judgment, not feedback):
- NAME AS AN ACT, NOT A LACK. Name what the trace shows happening, never what
  was missing relative to an implied fix. If the failure is genuinely an
  omission, the definition must state the observable license: the thing was
  present in the task or upstream work, absent in the output, and the output
  presented itself as complete anyway.
- DEFINITION IS A FACT PATTERN. State what happened in the execution, as an
  observation about a finished exhibit. Do not use quality words without
  observable content: properly, adequately, poor, superficial, correctly,
  should, must. "Fails to properly verify" is invalid; "the response asserts
  constraints were checked while the trace contains no check" is valid.
- OBSERVABILITY LICENSE. A judge must be able to QUOTE trace text satisfying
  the definition. If no quotable evidence could ever satisfy it, the code is
  invalid.
- BOUNDARIES BY OBSERVABLES. when_to_use / when_not_to_use must separate the
  code from its nearest neighbors by what is visible in the trace, never by
  inferred intent and never by the outcome.
- NO REMEDY, NO ROUTING, NO ADVICE. Nothing in a name or definition says what
  should have been done, who should fix it, or how. The code records that a
  thing happened.
- NO CONSEQUENCE IN THE IDENTITY. Whether an occurrence ruined the final
  answer or was harmless is not part of the code's name or definition.
