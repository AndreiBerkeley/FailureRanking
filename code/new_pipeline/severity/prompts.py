"""The study-1 rater prompt. One call per rater; every code rated in one pass."""

LEVELS = ["inconsequential", "intermediate", "severe", "critical"]
ORD = {l: i for i, l in enumerate(LEVELS)}

PROMPT = """You are rating the GENERAL IMPORTANCE of each failure mode in a taxonomy, from a corpus
of execution traces in which those failure modes were found.

DEFINITION OF IMPORTANCE

The importance of a failure mode is how much one occurrence of it, on its own, reduces the
chance that the program's final output is correct.

Apply it as: suppose this were the only thing that went wrong in the trace — how likely is it
that the task still succeeds?

Consequences this failure CAUSED — including later failures it set in motion — count as its
own. "On its own" means: do not charge it for failures that would have happened anyway.

Rate the MECHANISM in general, from all its occurrences in the corpus, not any single one.
Do not rate by how bad the mistake looks; rate by what it costs the final output.

THE FOUR LEVELS — each is a test on what happened downstream

  critical         more than one hop is lost: from this point the task can no longer succeed
  severe           one hop is lost: that retrieval ran on the wrong thing, or did not run
  intermediate     part of a hop: the retrieval was weakened but still aimed at the right thing
  inconsequential  nothing downstream changed

THE PROGRAM

{program}

Its final output is the union of documents returned by the three retrievals. Nothing the
agents write is itself the output; what they write matters only through the queries it
produces and the documents those queries retrieve.

AGENT SPECIFICATIONS (each agent runs under exactly this, in every trace)

{instructions}

THE TAXONOMY

{taxonomy}

WHERE EACH CODE WAS FOUND
T-numbers are traces, t-numbers are turns. Every trace appears in full below, with all of its
findings — evidence and problem — listed at its head, so you can separate one code's effect
from the others' on the same trace.

{index}

THE CORPUS ({n_traces} traces)

{traces}

WHAT TO RETURN

Return ONLY a JSON object:

{{"ratings": [
   {{"code": "SP_01",
     "level": "<one of: critical | severe | intermediate | inconsequential>",
     "cited": ["T07", "T23", ...],
     "mechanism": "<one sentence: what this mode typically costs the final output, and why>",
     "support": "<ok | low | none>"}},
   ... one entry for every code in the taxonomy ...
]}}

Rules:
- Every code gets exactly one entry, including codes with few or no findings. For those, rate
  from the definition and the program, and set support to "low" (under 5 findings) or "none".
- "cited" must list the T-numbers you relied on, and each must be a trace on which that code
  was actually found. A rating with no valid citation will be rejected.
- The mechanism sentence must name what happened downstream in the cited traces.
"""
