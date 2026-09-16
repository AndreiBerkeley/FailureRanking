# models-1-judged-50-b — second judged 50 for the models-1 set

50 tasks from the models-1 judging pool, disjoint from `models-1-judged-50`, chosen as the
one of 500 seeded random draws with the fewest candidate pairs tied on judging-pool gold
(0 of 36 pairs; the first set had 6), pass-count spread 17.0.

**Selected on gold.** The condition reads `outcomes/cap-7.jsonl` (the judging pool's own
outcomes), so gold-50 on this set separates candidates by construction — the point of the
draw, since a gold-50 with tied candidates cannot be a target for anything. The
generalization outcomes (`cap-8`) were not read. Report this wherever the set is used.

Pass counts on the 50: [36.0, 30.0, 28.0, 27.0, 24.0, 23.0, 22.0, 20.0, 19.0].

Built by `scripts/draw_judged_50_b.py`; the seed reproduces it.
