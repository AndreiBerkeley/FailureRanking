# models-1-judged-50 — the 50 judging tasks read by the judge

Seed 1 of the nested sample-size sweep, reproduced exactly: the 500 judging tasks of
`models-1` sorted, shuffled with `random.Random(1)`, first 50 taken. Nine models x 50 tasks x
repeat 0 = 450 traces.

The draw is pinned because it matters: at 50 tasks the five seeds of that sweep gave Kendall tau
against the generalization ranking of +0.41, +0.46, +0.18, +0.30 and +0.53. Which fifty you take
moves the answer more than how many you take, so the mapping records its own.
