CATEGORY C - Domain Reasoning Failures

These are failures in the REASONING PROCESS itself, specific to the problem domain.
C codes describe WHAT went wrong in the reasoning — not WHO made the error or WHETHER
the system broke. A judge should be able to identify these by reading the reasoning
in a trace, WITHOUT needing to independently solve the problem or know the correct answer.

NAMING RULE: C-codes must NEVER contain agent role names (${role_str}).
A valid C code applies equally whether the flawed reasoning appeared in any agent's output.

EXAMPLES OF THE DESIRED SHAPE (illustrative, from other domains — do not copy them
unless the traces genuinely exhibit them; they show the target style):
- Asserts_Unverified_Intermediate_Conclusion: a claim is treated as established and
  built upon without the reasoning that would establish it appearing anywhere.
- Requirement_Silently_Dropped: part of what the task asked for disappears from the
  work without acknowledgement, while the output presents itself as complete.
- Confident_Fabrication_At_Capability_Limit: where the trace shows the work could not
  be completed, the output states a specific answer anyway, with no hedge visible.
- Answer_Disconnected_From_Work: the final answer does not follow from, or
  contradicts, the reasoning that precedes it.

Each example names a BEHAVIOR of the candidate, observable in the trace, judged as an
end state. None names a task topic, a consequence alone, or a remedy.
