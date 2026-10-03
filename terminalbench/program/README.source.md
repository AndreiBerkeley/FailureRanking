# program — Terminus 2

Every candidate is the same agent, Terminus 2 (harbor `terminus-2` 2.0.0), the
Terminal-Bench reference agent, with a different model behind it. One agent in a
loop: it reads the terminal output of its previous command batch, writes an
analysis and a plan, and emits the next batch of keystrokes (each with a wait
duration) that the harness types into a bash session in the task's container.
The loop ends when the agent marks the task complete or the harness stops it
(agent timeout 900 s). Then the verifier's hidden tests inspect the container's
final state and give reward 0 or 1.

`structure.json` is the description the pipeline reads: the trace format, the
loop, the tools seen (`bash_command`, `mark_task_complete`) and the
`success_rule` the judge's passes and the recovery reader are shown — the task
is scored on the container's final state against the task description; the
agent's own claims of completion are not evidence.
