# hover / models — cases

Nine models, tax-15, judge pointjudge (set a `pointjudge-1-sp15`, set b `pointjudge-3`), 100 judged tasks. Here no trace method tracks gold (amplitude +0.056, incidence +0.200 vs gold-gen on the 100). A trace is four module turns; gold is whether the three supporting Wikipedia titles came back from the harness's three retrievals.

| category | what it shows | cases |
|---|---|---:|
| A | the judge finds 6–10 points on runs that retrieved every gold title: the codes describe how the modules write, not whether they find the entities | 6 |
| B | runs that missed a gold title with nothing to quote: the miss happens inside the harness's retrieval, not in a module's text | 6 |
| C | the hand-authored 'conclusion unlicensed by the evidence' code, the only one skewed to failures (80 fail / 47 pass) | 4 |
| D | the candidate with the most points per trace (5.35) sits mid-table on gold; the one with the fewest (2.60) is second — amplitude ranks them backwards | 4 |
| E | what containment sees: a clean hop-2/hop-3 query after a bad summary, on a run that passed and on one that failed anyway | 4 |

## Cases

| # | trace | task | candidate | gold | codes | category | note |
|---|---|---|---|---|---|---|---|
| 1 | `6aff31cc` | d1eabe20-52ec-45e4-9d2c-9878786fb33a | deepseek-v4-flash-0731 | pass | SP_02, SP_06×2, SP_07, SP_09×3, SP_15×4 | A | 12 points on a passing run; all three gold titles retrieved; heaviest codes SP_15×4, SP_09×3 |
| 2 | `a6e5c516` | 57bb6412-f034-45d5-a1de-87a726c79e38 | deepseek-v4-flash-0731 | pass | SP_01×2, SP_02×3, SP_05, SP_06, SP_09×3 | A | 10 points on a passing run; all three gold titles retrieved; heaviest codes SP_02×3, SP_09×3 |
| 3 | `6d03afcd` | 289d364e-6712-4db7-aaec-71dc911a50ff | glm-5.3-flash | pass | SP_04×2, SP_05×2, SP_07, SP_08×2, SP_15×4 | A | 10 points on a passing run; all three gold titles retrieved; heaviest codes SP_15×4, SP_04×2 |
| 4 | `e4ce1f0f` | d1eabe20-52ec-45e4-9d2c-9878786fb33a | mistral-small-2603 | pass | SP_06, SP_13×2, SP_15×4 | A | 9 points on a passing run; all three gold titles retrieved; heaviest codes SP_15×4, SP_13×2 |
| 5 | `7ce218b9` | 6668033c-7c45-4d60-803d-08b782e22277 | minimax-m3 | pass | SP_01×4, SP_03×2, SP_06, SP_09, SP_11 | A | 9 points on a passing run; all three gold titles retrieved; heaviest codes SP_01×4, SP_03×2 |
| 6 | `9f2813ba` | e56b8344-2c8d-4fb8-8dee-417c984e64ae | deepseek-v4-flash-0731 | pass | SP_01×3, SP_04, SP_05, SP_06, SP_08, SP_14×2 | A | 9 points on a passing run; all three gold titles retrieved; heaviest codes SP_01×3, SP_14×2 |
| 7 | `4547c46a` | 498d5ba5-be22-49c1-a5cd-0fe3265af3b5 | claude-haiku-4.5 | fail | — | B | 0 point(s); missed gold title(s): 2012 Open Sud de France – Doubles, Heather Watson, Édouard Roger-Vasselin — the retrieval miss leaves no mark the reader can quote |
| 8 | `736e2d9a` | 79c729ca-c0d0-4271-ac83-e851149b4f6b | claude-haiku-4.5 | fail | — | B | 0 point(s); missed gold title(s): Robinsons Galleria, SM Megamall — the retrieval miss leaves no mark the reader can quote |
| 9 | `87565f0d` | 1bf83050-23e6-4324-9ce6-8bfdc9253c1e | gemini-3.1-flash-lite | fail | — | B | 0 point(s); missed gold title(s): D.C. Cab — the retrieval miss leaves no mark the reader can quote |
| 10 | `d4977181` | 805657a4-35df-4289-8b28-76aa6164b2d0 | mimo-v2.5 | fail | — | B | 0 point(s); missed gold title(s): Best Foot Forward (musical), Gene Kelly — the retrieval miss leaves no mark the reader can quote |
| 11 | `08957338` | 6ab9ec05-e68a-4522-bf1f-3025f4f8855b | mistral-small-2603 | fail | SP_06 | B | 1 point(s); missed gold title(s): Donny Green, Massachusetts Institute of Technology, University of Virginia — the retrieval miss leaves no mark the reader can quote |
| 12 | `12104b21` | 8eb56beb-17de-4add-9c2e-d8fe56974384 | seed-2.0-mini | fail | SP_06 | B | 1 point(s); missed gold title(s): Helen Hunt — the retrieval miss leaves no mark the reader can quote |
| 13 | `02fe697e` | 289d364e-6712-4db7-aaec-71dc911a50ff | gemini-3.1-flash-lite | fail | SP_05×2, SP_06, SP_14×2, SP_15×4 | C | SP_15 at turn 1 (summarize1): The agent treats the absence of information in the provided passage as confirmation that the location was not establishe; missed Monfragüe |
| 14 | `0698a6d2` | 61804913-fe4f-4c50-927f-82a480bc0e11 | mimo-v2.5 | fail | SP_02×2, SP_04×2, SP_06, SP_07, SP_09, SP_15 | C | SP_15 at turn 1 (summarize1): The agent asserts that Roger Donaldson is not French based on his son being from New Zealand, an ungrounded assertion no; missed Roger Donaldson |
| 15 | `07ab5476` | 498d5ba5-be22-49c1-a5cd-0fe3265af3b5 | deepseek-v4-flash-0731 | fail | SP_01×4, SP_05, SP_06, SP_07, SP_09, SP_15×2 | C | SP_15 at turn 3 (summarize2): The agent asserts Soares as the matching player in the same passage where it goes on to admit the decisive tournament is; missed 2012 Open Sud de France – Doubles, Heather Watson, Édouard Roger-Vasselin |
| 16 | `089c5e18` | 79c729ca-c0d0-4271-ac83-e851149b4f6b | gemini-3.1-flash-lite | fail | SP_01×2, SP_05, SP_06×2, SP_15 | C | SP_15 at turn 3 (summarize2): The agent declares the multi-part claim fully verified even though neither the hop-2 passages nor its own context ever a; missed Galleria Corporate Center |
| 17 | `6dad3d14` | c03026e1-36f5-4736-ae34-e6c0262acf72 | deepseek-v4-flash-0731 | pass | SP_01, SP_02, SP_05, SP_06, SP_09×2 | D | same task, both pass; deepseek carries 5 points (SP_09×2, SP_01×1) — deepseek's per-trace point count is the highest of the nine, its gold mid-table |
| 18 | `a0d64332` | c03026e1-36f5-4736-ae34-e6c0262acf72 | claude-haiku-4.5 | pass | — | D | same task, both pass; haiku carries 0 points (none) — deepseek's per-trace point count is the highest of the nine, its gold mid-table |
| 19 | `0498568d` | e0a7bd6a-43f4-4d42-8d91-e9eef7feebca | deepseek-v4-flash-0731 | pass | SP_02×2, SP_06, SP_09×3, SP_13, SP_15 | D | same task, both pass; deepseek carries 8 points (SP_09×3, SP_02×2) — deepseek's per-trace point count is the highest of the nine, its gold mid-table |
| 20 | `59fab361` | e0a7bd6a-43f4-4d42-8d91-e9eef7feebca | claude-haiku-4.5 | pass | SP_02, SP_05, SP_06 | D | same task, both pass; haiku carries 3 points (SP_02×1, SP_05×1) — deepseek's per-trace point count is the highest of the nine, its gold mid-table |
| 21 | `5c5ac239` | 498d5ba5-be22-49c1-a5cd-0fe3265af3b5 | gemini-3.1-flash-lite | fail | SP_01×5 | E | all 5 points at turns ≤ 2, turns 3–4 clean → every firing is 'contained'; outcome fail (missed Heather Watson, Édouard Roger-Vasselin) — containment reads clean later turns as recovery, but a clean query can still retrieve nothing |
| 22 | `6906e4ca` | 6668033c-7c45-4d60-803d-08b782e22277 | mimo-v2.5 | fail | SP_04, SP_05 | E | all 2 points at turns ≤ 2, turns 3–4 clean → every firing is 'contained'; outcome fail (missed Harper Lee) — containment reads clean later turns as recovery, but a clean query can still retrieve nothing |
| 23 | `c3f5ccb6` | d531f665-56bf-4b2a-824e-0391417be9d1 | deepseek-v4-flash-0731 | pass | SP_06, SP_07 | E | all 2 points at turns ≤ 2, turns 3–4 clean → every firing is 'contained'; outcome pass — containment reads clean later turns as recovery, but a clean query can still retrieve nothing |
| 24 | `e15efd31` | 7665e72c-f18b-43b7-8d41-e056e884241f | claude-haiku-4.5 | pass | SP_01×2, SP_05 | E | all 3 points at turns ≤ 2, turns 3–4 clean → every firing is 'contained'; outcome pass — containment reads clean later turns as recovery, but a clean query can still retrieve nothing |

## What the cases say

Points land on passing and failing runs alike: 403 of 407 passing traces carry a point, mean 3.5 points on a pass vs 4.0 on a fail. Two codes — SP_05 (redundant next-hop query) and SP_06 (meta/evaluative query) — account for the bulk and fire on 271/305 (pass/fail) and 196/271 traces: they describe the *form* of the query text, and a query in bad form retrieves the right page as often as not. What decides gold is whether a title the claim never names gets retrieved, and that happens in the harness, between turns, where nothing is quotable (B). The one code with a failure skew, SP_15, is the hand-authored one (C). D shows the ranking consequence: deepseek writes verbose, marker-heavy output that draws the most points of any model while sitting mid-table on gold. E shows why containment cannot rescue it: a clean later turn is not a recovered retrieval.
