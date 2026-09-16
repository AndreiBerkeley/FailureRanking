# livecodebench / models — cases

Nine models, tax-2, judge `pointjudge-2` on the 150 judging tasks. On this benchmark the trace methods track gold (amplitude +0.889 vs gold-gen on the 150); these cases show the mechanism and its edges. Every trace is one turn: problem in, program out; the judge's points quote the program.

| category | what it shows | cases |
|---|---|---:|
| A | 22 of 878 passing traces carry a point (the judge never sees outcomes): mostly complexity warnings (SP_02) and implementation defects the tests did not exercise | 6 |
| B | 33 of 472 failing traces have no point: 9 are one task whose checker rejects every valid answer, the rest are runtime/TLE/subtle wrong answers the reader did not catch | 7 |
| C | a failing trace per code where both readers found the same point — what a code looks like when it works | 8 |
| D | the 3 of 627 points the decider could place nowhere under tax-2 | 3 |
| E | passers silent, failers coded — the per-task pattern that lets amplitude and incidence track gold | 8 |

## Cases

| # | trace | task | candidate | gold | codes | category | note |
|---|---|---|---|---|---|---|---|
| 1 | `b9f1e728` | 2849 | minimax-m3 | pass | SP_02 | A | judge: The solution recomputes the imbalance count from scratch for every subarray inside an O(n^2) double loop over all subarrays, yielding O(n^3) time complexity (wi |
| 2 | `59b1fbf9` | 3024 | deepseek-v4-flash-0731 | pass | SP_02 | A | judge: The DP transition is iterated k times with a simple loop instead of using matrix exponentiation or closed-form computation, giving O(k) time which exceeds limit |
| 3 | `273e13a4` | 3166 | gpt-5.4-nano | pass | SP_08 | A | judge: possible(k) only enforces that no group exceeds max_size=ceil(n/k) (a necessary condition) but never checks that each value's frequency can actually be decompos |
| 4 | `7b1b56bb` | 3166 | gemini-3.1-flash-lite | pass | SP_07 | A | judge: The validity check only verifies b <= q but omits verifying b >= 0, so cases where q*s exceeds f (yielding a negative implied count of size-(s+1) groups) are in |
| 5 | `4bd6ff6e` | 3291 | claude-haiku-4.5 | pass | SP_08 | A | judge: The agent assumes elements sharing a set-bit count can be freely permuted regardless of intervening elements with different set-bit counts, when in fact adjacen |
| 6 | `0195e1ac` | 3361 | mistral-small-2603 | pass | SP_07 | A | judge: When s_list[0] is '?' and s_list[1] is '2' or '3', the code sets s_list[0] to '1', producing hour '12' or '13' which exceeds the valid maximum hour of 11. |
| 7 | `2d753ec5` | abc343_a | gpt-5.4-nano | fail | — | B | abc343_a asks for *any* digit ≠ A+B; the checker compares to the sample's digit, so all nine models 'fail' — gold error, judge correctly silent |
| 8 | `4aa96d3a` | abc343_a | seed-2.0-mini | fail | — | B | abc343_a asks for *any* digit ≠ A+B; the checker compares to the sample's digit, so all nine models 'fail' — gold error, judge correctly silent |
| 9 | `21d66ec0` | 2833 | minimax-m3 | fail | — | B | harness: Error during testing: No module named 'sortedcontainers' (0/1 tests before stop); the judge read the program and saw nothing |
| 10 | `18c53bc0` | 2849 | gemini-3.1-flash-lite | fail | — | B | harness: Runtime Error (2/3 tests before stop); the judge read the program and saw nothing |
| 11 | `1e9fbe53` | 3550 | minimax-m3 | fail | — | B | harness: Time Limit Exceeded (4/5 tests before stop); the judge read the program and saw nothing |
| 12 | `43032638` | 3591 | claude-haiku-4.5 | fail | — | B | harness: Wrong Answer (0/1 tests before stop); the judge read the program and saw nothing |
| 13 | `b02cc1ad` | abc312_e | minimax-m3 | fail | — | B | harness: Wrong answer at output_line_idx=0: 0 != 2 (1/2 tests before stop); the judge read the program and saw nothing |
| 14 | `6e44eb25` | 2784 | minimax-m3 | fail | SP_01, SP_08 | C | SP_01, both readers; harness: Error during testing: invalid syntax (<s; judge: The turn's output ends mid-comment inside a never-finished derivation, with no function body, return statement, or closi |
| 15 | `5bcf7dde` | 2784 | claude-haiku-4.5 | fail | SP_02, SP_06 | C | SP_02, both readers; harness: Wrong Answer; judge: The final solution uses a nested loop over all pairs (i, j) with n up to 1e5, giving O(n^2) time complexity that will ex |
| 16 | `c3665b6a` | 3024 | seed-2.0-mini | fail | SP_03, SP_07 | C | SP_03, both readers; harness: Wrong Answer; judge: The transition matrix is built symmetrically from a single cnt value with row sums equal to n (a+b = cnt + (n-cnt) = n), |
| 17 | `228f800f` | 2849 | mistral-small-2603 | fail | SP_04 | C | SP_04, both readers; harness: Wrong Answer; judge: The incremental update to `imbalance` when a new distinct value is added is mathematically wrong: it omits the required  |
| 18 | `70d6c3f2` | 2828 | mistral-small-2603 | fail | SP_07 | C | SP_07, both readers; harness: Wrong Answer; judge: After finding the first non-'a' character, the code decrements every character up to the end of the string instead of st |
| 19 | `b2a28f65` | 3114 | gpt-5.4-nano | fail | SP_08 | C | SP_08, both readers; harness: Wrong Answer; judge: In compute_left the algorithm needs a LIFO (monotonic stack) check against the most‑recently‑pushed segment to preserve  |
| 20 | `70067283` | 2833 | glm-5.3-flash | fail | SP_09 | C | SP_09, both readers; harness: Wrong Answer; judge: The window-contraction step reuses the single 'left' pointer that was just advanced forward to expand the window, instea |
| 21 | `be1673f3` | 3402 | claude-haiku-4.5 | fail | SP_08, SP_10 | C | SP_10, both readers; harness: Wrong Answer; judge: The agent's own trace of Example 1 contradicts its formula's output (7 vs the stated 15), and instead of revising the fl |
| 22 | `7c9f046e` | arc186_b | mimo-v2.5 | fail | SP_05, SP_08 | D | unplaced: The taxonomy has no entry for a self-check performed against a structure inconsistent with the agent's own code (as opposed to an acknowledged contrad |
| 23 | `caf5599b` | 3781 | claude-haiku-4.5 | fail | SP_02 | D | unplaced: No taxonomy code covers a crash caused by exceeding the language runtime's recursion-depth limit (a stack-depth/engineering failure) as distinct from  |
| 24 | `dd1ccc6a` | abc373_g | claude-haiku-4.5 | fail | SP_02 | D | unplaced: No taxonomy mode covers a mismatch between the required output-delimiter format and the format actually produced; this is an instruction-compliance/ou |
| 25 | `4c65391c` | 3721 | mimo-v2.5 | fail | SP_09 | E | task 3721: fails; The loop unpacks events_sorted elements in the wrong order, binding the event-type string (e[0]) to  |
| 26 | `4d1840e9` | 3721 | seed-2.0-mini | fail | SP_09 | E | task 3721: fails; The sort key uses only the timestamp, so at equal timestamps the code relies on the input array's or |
| 27 | `0b01a128` | 3721 | claude-haiku-4.5 | pass | — | E | task 3721: passes, no point |
| 28 | `3f0f9e86` | 3721 | deepseek-v4-flash-0731 | pass | — | E | task 3721: passes, no point |
| 29 | `2f0b4f52` | abc340_d | gpt-5.4-nano | fail | SP_08 | E | task abc340_d: fails; The solver processes stages in a single forward pass assuming dp[i] is finalized once reached, but s |
| 30 | `b917b09f` | abc340_d | mistral-small-2603 | fail | SP_08 | E | task abc340_d: fails; The code performs a single forward pass assuming dp[i] is finalized once i is reached in increasing  |
| 31 | `5ac7f373` | abc340_d | deepseek-v4-flash-0731 | pass | — | E | task abc340_d: passes, no point |
| 32 | `7296da22` | abc340_d | glm-5.3-flash | pass | — | E | task abc340_d: passes, no point |

## What the cases say

The judge is outcome-blind and almost never fires on a passing program: 856 of 878 passing traces are silent, 439 of 472 failing traces carry a point. That asymmetry is the whole result — a per-candidate count of points is a per-candidate count of failures with ~5% noise either way. The A cases are that noise on the passing side: complexity warnings (a judged O(n²) that the tests never stressed) and implementation defects on paths the tests do not reach. The B cases are the noise on the failing side, and a third of them are not noise at all: `abc343_a` accepts any digit ≠ A+B and the benchmark's exact-match checker rejects eight of the nine valid answers, so the judge's silence is right and the gold is wrong. The C cases are the codes doing their job; the E cases show the pattern per task.

## Why it is still not perfect

Amplitude reaches +0.889 against gold-gen on the 150 judged tasks, not +1, and a random 50 lands anywhere between +0.667 and +0.941. The reasons are visible in the cases and in the per-model counts:

| model | gold-gen | fails / 150 | points | points per failing trace | silent failures | points on passing traces |
|---|---:|---:|---:|---:|---:|---:|
| gemini-3.1-flash-lite | 0.751 | 36 | 50 | 1.31 | 2 | 3 |
| glm-5.3-flash | 0.694 | 42 | 44 | 1.02 | 5 | 1 |
| deepseek-v4-flash-0731 | 0.690 | 42 | 55 | 1.24 | 2 | 3 |
| mimo-v2.5 | 0.654 | 48 | 59 | 1.23 | 3 | 0 |
| gpt-5.4-nano | 0.650 | 54 | 74 | 1.28 | 3 | 5 |
| minimax-m3 | 0.601 | 53 | 59 | 1.00 | 8 | 6 |
| seed-2.0-mini | 0.566 | 54 | 85 | 1.54 | 3 | 2 |
| claude-haiku-4.5 | 0.542 | 68 | 87 | 1.21 | 6 | 5 |
| mistral-small-2603 | 0.453 | 75 | 114 | 1.49 | 1 | 2 |

1. **Amplitude counts points, not failures, and points per failing trace differ by model** — from 1.00 (minimax) to 1.54 (seed). glm and deepseek both fail 42 of 150 and are tied on gold-gen (0.694 vs 0.690), but deepseek's failures draw 55 points to glm's 44: the judge finds more to quote in some models' programs than in others', and that is not a difference in how often they fail. Incidence removes this and matches amplitude on the 150 (+0.889).
2. **Failures the reader cannot see from the program.** Of the 33 silent failures, 9 are the checker's error (B), and the rest are mostly things a reading cannot settle: a time limit that depends on constant factors (C `1e9fbe53`, `43032638`), a runtime error on the third hidden test, a module the sandbox does not have (`21d66ec0`), a recursion depth the language enforces (D `caf5599b`). They are not evenly spread — minimax has 8 silent failures in 53, mistral 1 in 75 — so they shift candidates relative to each other.
3. **Points on passing programs are not evenly spread either** — gpt-5.4-nano and minimax carry 5–6 points on passing traces, mimo none. Most are complexity warnings (SP_02): the judge predicts a time limit the tests did not enforce.
4. **Gold-gen has its own noise.** Two candidate pairs are within 0.004 pass rate on the 755 tasks (mimo / gpt-5.4-nano, deepseek / glm) — a coin flip for any method, including gold-50 — and 85 of the 755 tasks are failed by all nine models, 8 of them because the statement allows several answers and the checker accepts one (`arc190_a`, `abc311_c`, `abc343_e`, …), the same defect as `abc343_a`.
5. **Fifty tasks is a small sample of nine models a few passes apart.** Adjacent models differ by 1–3 passes on a random 50; which side of a pair a draw lands on is the draw, for the trace methods and for gold-50 alike — hence the spread of the ten draws, and hence gold-50's own +0.657 to +0.941.
