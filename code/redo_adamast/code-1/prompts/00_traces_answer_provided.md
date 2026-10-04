THE TRACES AND THE CORRECT ANSWER

Each trace comes with the correct final answer to its task, shown as
CORRECT ANSWER at the top of the trace. The agent system never saw it; you
do. Use it to find where the run went wrong: compare what each step found,
decided and concluded with what the task needed.

A failure is still a wrong action, not a wrong answer. With the answer in
view, a step is also a failure when it led the run away from the answer
while a better choice was open to it at that point, given what it was told
and what it had received.

  Example: asked for a museum's opening hours, the agent searches, sees the
  museum's own site among the results, opens a travel blog instead, and
  copies the hours from it. The blog is out of date. The failure is
  choosing the blog over the museum's own site that was in front of it.
  (mode: not using the primary source)

A step that was reasonable given what it had is not a failure only because
the run later went wrong. A run can reach the right answer and still
contain failures, so read every trace with the same care.
