REQUIREMENTS:
1. Generate codes for complete coverage of all distinct system failure modes
2. Each code must represent a genuinely distinct failure — do NOT create multiple
   codes for variants of the same problem (e.g., do not have separate codes for
   "output missing" and "output empty" — those are the same failure)
3. Prefer CAUSAL codes over SYMPTOM codes. "Token limit caused truncation" is one
   code, not two separate codes for "token limit hit" and "output truncated"
4. Each code needs detection_heuristics grounded in observable signals
5. Definitions should be concise and clear
6. Follow naming rules strictly

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
