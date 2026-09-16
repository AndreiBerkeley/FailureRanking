# hover / GEPA_candidates — cases

Twelve optimizer-proposed instruction sets, tax-10, panel judge (`map-5`, `map-6`), 100 judged tasks, gold-gen on the 500-task domain. No trace method tracks gold here (amplitude −0.091, incidence −0.345, containment +0.323 vs gold-gen on the 100).

| category | what it shows | cases |
|---|---|---:|
| A | the three best instruction sets by gold-gen carry three or more codes on runs that retrieved every gold title | 6 |
| B | the bare-docstring candidate: fewest form violations, 10th of 12 on gold — the candidate that makes incidence negative | 6 |
| C | codes the taxonomy-holding panel did not agree on but the blind reader's problem mapped to | 4 |
| D | runs that missed a gold title with nothing the judge could name | 4 |
| E | everything fired at turns 1–2 with hop-2/hop-3 clean, on a pass and on a fail — what containment credits as recovery | 3 |

## Cases

| # | trace | task | candidate | gold | codes | category | note |
|---|---|---|---|---|---|---|---|
| 1 | `6e93a521` | 4e5f7db0-847b-4fa8-802d-04b0305762a2 | cand-020 | pass | RL_03, RL_04, RL_06, RL_08, RL_09, RL_10 | A | cand-020 (gold-gen 0.65, top 3) passes with 6 codes: RL_03, RL_04, RL_06, RL_08, RL_09, RL_10 |
| 2 | `7acdb95e` | 2b4db6a7-b06f-4986-8589-773a3e7c80a6 | cand-011 | pass | RL_01, RL_02, RL_04, RL_06, RL_08, RL_10 | A | cand-011 (gold-gen 0.65, top 3) passes with 6 codes: RL_01, RL_02, RL_04, RL_06, RL_08, RL_10 |
| 3 | `a74d2a15` | ea9c7263-5147-4093-b176-af2835210e96 | cand-008 | pass | RL_01, RL_04, RL_05, RL_07, RL_08, RL_09 | A | cand-008 (gold-gen 0.65, top 3) passes with 6 codes: RL_01, RL_04, RL_05, RL_07, RL_08, RL_09 |
| 4 | `ff0126b9` | fb3df58e-2edd-42dc-889b-d4e5f8808ee0 | cand-011 | pass | RL_01, RL_03, RL_04, RL_06, RL_09, RL_10 | A | cand-011 (gold-gen 0.65, top 3) passes with 6 codes: RL_01, RL_03, RL_04, RL_06, RL_09, RL_10 |
| 5 | `041d6329` | 33597196-b5b6-473b-8ee3-4a344a620c22 | cand-011 | pass | RL_01, RL_02, RL_03, RL_04, RL_10 | A | cand-011 (gold-gen 0.65, top 3) passes with 5 codes: RL_01, RL_02, RL_03, RL_04, RL_10 |
| 6 | `0c57367e` | 3ffe8652-e5d8-4e84-b2c1-02875e263423 | cand-008 | pass | RL_01, RL_05, RL_08, RL_09, RL_10 | A | cand-008 (gold-gen 0.65, top 3) passes with 5 codes: RL_01, RL_05, RL_08, RL_09, RL_10 |
| 7 | `17cb2582` | 7bc7972a-3392-4091-ab6d-2fe1a85613ca | cand-019 | fail | — | B | cand-019 (bare one-line docstrings; gold-gen 0.48, 10th of 12) — no code fired; failed, missed 2011 Teen Choice Awards. Its incidence is 0.78 against 0.92–1.00 for the rest, which is why incidence ranks it first |
| 8 | `2b6e0e3f` | 80a5af55-46b7-43d5-8eb7-e1b3af324c3b | cand-019 | fail | — | B | cand-019 (bare one-line docstrings; gold-gen 0.48, 10th of 12) — no code fired; failed, missed Shenandoah National Park. Its incidence is 0.78 against 0.92–1.00 for the rest, which is why incidence ranks it first |
| 9 | `6d617cf2` | a38e8d79-fb7f-4523-a56c-ef52025fb3b2 | cand-019 | fail | — | B | cand-019 (bare one-line docstrings; gold-gen 0.48, 10th of 12) — no code fired; failed, missed Boy Hits Car, The Invisible (band). Its incidence is 0.78 against 0.92–1.00 for the rest, which is why incidence ranks it first |
| 10 | `07457acb` | fb3df58e-2edd-42dc-889b-d4e5f8808ee0 | cand-019 | pass | — | B | cand-019 (bare one-line docstrings; gold-gen 0.48, 10th of 12) — no code fired; passed. Its incidence is 0.78 against 0.92–1.00 for the rest, which is why incidence ranks it first |
| 11 | `2c8998d5` | 702f619e-72de-4ae5-a5ec-2ea5793d9c00 | cand-019 | pass | — | B | cand-019 (bare one-line docstrings; gold-gen 0.48, 10th of 12) — no code fired; passed. Its incidence is 0.78 against 0.92–1.00 for the rest, which is why incidence ranks it first |
| 12 | `4f8d38f3` | 306b1d0a-1bd5-4ca8-bc43-3eca0935cf18 | cand-019 | pass | — | B | cand-019 (bare one-line docstrings; gold-gen 0.48, 10th of 12) — no code fired; passed. Its incidence is 0.78 against 0.92–1.00 for the rest, which is why incidence ranks it first |
| 13 | `0017df70` | 124ee215-7bdf-43b1-8b65-77eaa401f0eb | cand-020 | pass | RL_05, RL_08, RL_09 | C | open reader alone supplies RL_05, RL_08, RL_09; panel agreed on nothing; pass |
| 14 | `00a2f242` | c634d5ad-cd6d-498f-a9dd-971eafd83d07 | cand-012 | pass | RL_01, RL_08 | C | open reader alone supplies RL_01; panel agreed on RL_08; pass |
| 15 | `00f73deb` | 259b69c7-7d45-4d78-b9dd-4209890b502d | cand-012 | fail | RL_01, RL_03, RL_04, RL_05 | C | open reader alone supplies RL_01; panel agreed on RL_03, RL_04, RL_05; fail |
| 16 | `0159d215` | b1d32062-8ab5-4bc6-a0b6-2e7b7d6d04fc | cand-016 | fail | RL_01, RL_03 | C | open reader alone supplies RL_01, RL_03; panel agreed on nothing; fail |
| 17 | `00e9288c` | 574eeee6-07b1-4b45-b3e7-b8c61c9e7f07 | cand-026 | fail | — | D | cand-026 fails with no code; missed Of Montreal |
| 18 | `362ebb56` | 8215086e-68f6-4af9-9236-3cb5b46e96eb | cand-016 | fail | — | D | cand-016 fails with no code; missed Not Now John, Roger Waters |
| 19 | `3c55960d` | 832b3f78-b160-450c-844f-fe73b0a025e3 | cand-014 | fail | — | D | cand-014 fails with no code; missed The Heroes of Olympus |
| 20 | `bc1ef4fe` | 574eeee6-07b1-4b45-b3e7-b8c61c9e7f07 | cand-016 | fail | — | D | cand-016 fails with no code; missed Ima Robot |
| 21 | `0412a4e6` | 65f2db6e-17c4-4a52-9ba7-9542f0cce1a1 | cand-016 | fail | RL_04, RL_08 | E | firings only at turns [1, 2], hop-2/hop-3 queries clean → contained; fail, missed Nol Card |
| 22 | `04fd5bb3` | e56b8344-2c8d-4fb8-8dee-417c984e64ae | cand-016 | pass | RL_02, RL_04 | E | firings only at turns [1, 2], hop-2/hop-3 queries clean → contained; pass |
| 23 | `08656630` | 646ac79d-a1af-47e4-8454-a9b6e23097cf | cand-016 | pass | RL_02, RL_04, RL_08 | E | firings only at turns [1, 2], hop-2/hop-3 queries clean → contained; pass |

## What the cases say

Something fires on 1,149 of 1,200 traces (583 of 615 passing ones), so incidence is 0.92–1.00 for eleven candidates and cannot order them; the twelfth, cand-019, runs the bare one-line docstrings the optimizer started from, breaks the fewest output-form expectations (incidence 0.78) and is 10th of 12 on gold — hence incidence's negative tau (B). The A cases show the other side: the best instruction sets are long and prescriptive, and their runs carry three to five codes while retrieving every title. The codes (output form breach, missing required part, missing closing marker, work state misjudged) describe how the module writes; gold is decided by which pages the harness returns. C shows the blind reader adding codes the panel did not agree on; D the failures with nothing to quote; E what containment credits.
