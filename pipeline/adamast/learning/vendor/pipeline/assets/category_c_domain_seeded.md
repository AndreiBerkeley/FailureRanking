${common_header}

YOUR TASK (Domain-Seeded Stage):
Using the domain error patterns, subdomains, and terminology pitfalls below as scaffolding,
generate categories of reasoning failure that:
1. Are DETECTABLE from the trace alone — a judge reading the reasoning can spot the flaw
   without solving the problem independently
2. Describe ERROR TYPES, not error instances — each code should apply across many problems,
   not just one specific scenario
3. Are at the right GRANULARITY — not too broad ("mathematical error") and not too narrow
   ("forgot to check n=0 in induction")
4. Are EVIDENCED — generate a code only where the sample traces actually exhibit the
   pattern. The subdomain scaffolding below is context for reading traces, never a
   quota: a subdomain with no observed reasoning failures gets no code.

NAMING RULE: a code's identity is the CANDIDATE'S ACTION, never the task's subject
matter. "Unjustified_Case_Elimination" is a valid name; "Geometry_Error" is not.
If a behavior happens to occur mostly in one subdomain, name the behavior, not the
subdomain.

For each code, provide a concrete example of when it applies vs when it does NOT,
to ensure the code is operationally distinguishable from other codes.

DISTINGUISHABILITY RULE: If two codes cannot be told apart by a judge reading a trace,
they must be merged into one code.

${domain_error_ctx}
${domain_ctx}
