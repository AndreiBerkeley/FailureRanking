# Methods that read failure modes

The formulas that use which codes fired, or how many distinct codes fired, not only whether a trace has a failure
instance. Three experiments: Models·HoVer (judged set b), Models·Terminal-Bench 2.0 and Models·LiveCodeBench on its
50-task split. GEPA·HoVer is left out of these tables; its numbers for every method are in `best_methods.md` and
`first_last_study.md`. SWE-bench is not included: the endpoint formulas need its formatting codes chosen first.

Each number is Kendall tau-b against the generalization set's pass rates, tied pairs dropped; every score is lower-is-better.
The steps of every formula are in `formulas.md` (baselines, recovery-dependent formulas, and the section on the first and
last failure instance).

**One row per family.** A family is a formula plus the variants that change only one setting of it: a weight, a constant,
a cut-off, or whether a count is the candidate's own or pooled over candidates. The row shows the member with the highest
mean over the three experiments; the other members are listed under the table. The pick is made on the same three
experiments it is reported on, so a shown row's mean is optimistic by roughly its gap to the next member. *Endpoint*
formulas read only each trace's first and last failure instance, after deleting formatting codes.

## Without recovery

| method | Models·HoVer (9×50) | Models·TB (7×19) | Models·LCB (9×50) | mean | how it works |
|---|---:|---:|---:|---:|---|
| *gold on the judged tasks (the bar)* | *+0.444* | *+0.579* | *+0.765* | *+0.596* | share of judged tasks the candidate passed |
| incidence after removing formatting codes | +0.515 | +0.867 | +0.771 | +0.718 | delete formatting codes; share of tasks with any instance left |
| endpoint codes counted | +0.667 | +0.684 | +0.778 | +0.710 | per task: codes on the first instance + codes on the last; mean |
| mode filter on the endpoints | +0.588 | +0.647 | +0.697 | +0.644 | ignore the candidate's most frequent code at each endpoint position; share of tasks whose first or last instance still has another code |
| worst mode | +0.257 | +1.000 | +0.576 | +0.611 | for each code, the share of tasks on which it fired; score = the largest share |
| amplitude | +0.000 | +0.895 | +0.882 | +0.592 | per task: number of distinct codes; mean |
| breadth | -0.059 | +0.455 | +1.000 | +0.465 | number of distinct codes the candidate triggers on any task |
| patterns | -0.167 | +0.714 | +0.793 | +0.447 | number of distinct code sets among the candidate's tasks |
| *incidence (instances only, reference)* | *+0.333* | *+0.647* | *+0.771* | *+0.584* | share of tasks with any instance |
| *last-turn incidence (instances only, reference)* | *+0.310* | *+0.333* | *+0.771* | *+0.472* | share of tasks with an instance on the final turn |

Next members of each family by mean tau over the three experiments:

- **endpoint codes counted** (shown: no weight, sum over endpoints): own rarity weight, sum over endpoints +0.693; no weight, sum over modes +0.652; pooled rarity weight, sum over endpoints +0.606; 7 more in the appendix
- **mode filter on the endpoints** (shown: per candidate: drop the top 1 mode): across candidates: drop modes above mean + 1.5 SD +0.641; across candidates: drop the top 1 mode +0.630; per candidate: drop modes above mean + 1.5 SD +0.619; 5 more in the appendix
- **amplitude** (shown: amplitude): damped PIE, β=0.5 +0.529; containment +0.500; step-amplitude +0.494

## With recovery

| method | Models·HoVer (9×50) | Models·TB (7×19) | Models·LCB (9×50) | mean | how it works |
|---|---:|---:|---:|---:|---|
| *gold on the judged tasks (the bar)* | *+0.444* | *+0.579* | *+0.765* | *+0.596* | share of judged tasks the candidate passed |
| unrecovered endpoint codes counted | +0.833 | +0.900 | +0.829 | +0.854 | drop recovered instances; per task: distinct codes across the first and last remaining instance (a code on both counts once); mean |
| mode filter on unrecovered endpoints | +0.714 | +1.000 | +0.697 | +0.804 | drop recovered; at each endpoint position, count how often each code appears over the candidate's tasks; ignore codes above mean + 1.5 SD of those counts; share of tasks with a code left at either endpoint |
| endpoints weighted by the recovery rate | +0.556 | +1.000 | +0.771 | +0.776 | endpoints of all instances; an unrecovered endpoint code weighs 1, a recovered one weighs how often the candidate leaves that code at that position unrecovered; per task: the largest weight; mean |
| profile risk | +0.722 | +0.810 | +0.771 | +0.768 | for each code, the share of the candidate's instances with it that went unrecovered; per task: the largest such share among the task's codes; mean |
| unrecovered amplitude | +0.765 | +0.700 | +0.829 | +0.764 | drop recovered; per task: number of distinct codes; mean |
| recovery-weighted amplitude | +0.833 | +0.619 | +0.829 | +0.760 | for each (turn, code) unit, ρ = share of the tasks where it fired on which it was fully recovered; weight 1 − ρ²; score = Σ over units of weight × tasks fired ÷ T |
| unrecovered patterns | +0.588 | +0.474 | +0.857 | +0.640 | drop recovered; patterns on what is left |
| unrecovered breadth | +0.481 | +0.333 | +1.000 | +0.605 | drop recovered; breadth on what is left |
| unrecovered worst mode | +0.588 | +0.579 | +0.576 | +0.581 | drop recovered; worst mode on what is left |
| *unrecovered incidence (instances only, reference)* | *+0.543* | *+1.000* | *+0.771* | *+0.771* | share of tasks with any unrecovered instance |

Next members of each family by mean tau over the three experiments:

- **unrecovered endpoint codes counted** (shown: no weight, sum over modes): combined rarity weight, sum over endpoints +0.820; pooled rarity weight, sum over endpoints +0.802; combined rarity weight, sum over modes +0.788; 6 more in the appendix
- **mode filter on unrecovered endpoints** (shown: endpoints of unrecovered instances, per candidate: drop modes above mean + 1.5 SD): endpoints of unrecovered instances, across candidates: drop the top 1 mode +0.765; endpoints of unrecovered instances, per candidate: drop the top 1 mode +0.761; recovery checked on the endpoints, per candidate: drop the top 1 mode +0.760; 14 more in the appendix
- **endpoints weighted by the recovery rate** (shown: own recovery rate, no weight, max): own recovery rate, own rarity weight, max +0.743; own recovery rate, pooled rarity weight, sum over endpoints +0.735; own recovery rate, combined rarity weight, sum over endpoints +0.735; 41 more in the appendix
- **unrecovered amplitude** (shown: unrecovered amplitude): unrecovered damped PIE, β=0.5 +0.751; unrecovered step-amplitude +0.740; unrecovered containment +0.670
- **recovery-weighted amplitude** (shown: recovery-weighted amplitude, γ=2): recovery-weighted amplitude, γ=3 +0.747; recovery-weighted amplitude, γ=1 +0.742

## Appendix: every cell of the first-and-last grid

Recovery weight × mode weight × combiner, as defined in `formulas.md`; 75 cells, sorted by mean within each recovery weight.

| recovery weight | mode weight | combiner | Models·HoVer | Models·TB | Models·LCB | mean |
|---|---|---|---:|---:|---:|---:|
| no recovery | no weight | max | +0.515 | +0.867 | +0.771 | +0.718 |
| no recovery | no weight | sum over endpoints | +0.667 | +0.684 | +0.778 | +0.710 |
| no recovery | own rarity weight | sum over endpoints | +0.722 | +0.524 | +0.833 | +0.693 |
| no recovery | no weight | sum over modes | +0.543 | +0.529 | +0.882 | +0.652 |
| no recovery | pooled rarity weight | sum over endpoints | +0.556 | +0.429 | +0.833 | +0.606 |
| no recovery | combined rarity weight | sum over endpoints | +0.611 | +0.429 | +0.778 | +0.606 |
| no recovery | combined rarity weight | max | +0.444 | +0.524 | +0.833 | +0.601 |
| no recovery | pooled rarity weight | max | +0.389 | +0.524 | +0.889 | +0.601 |
| no recovery | own rarity weight | max | +0.389 | +0.429 | +0.889 | +0.569 |
| no recovery | own rarity weight | sum over modes | +0.556 | +0.333 | +0.778 | +0.556 |
| no recovery | pooled rarity weight | sum over modes | +0.444 | +0.333 | +0.889 | +0.556 |
| no recovery | combined rarity weight | sum over modes | +0.556 | +0.333 | +0.778 | +0.556 |
| no recovery | spread weight | sum over endpoints | +0.444 | +0.429 | +0.778 | +0.550 |
| no recovery | spread weight | sum over modes | +0.333 | +0.238 | +0.778 | +0.450 |
| no recovery | spread weight | max | +0.333 | +0.048 | +0.667 | +0.349 |
| recovery-weighted, own | no weight | max | +0.556 | +1.000 | +0.771 | +0.776 |
| recovery-weighted, own | own rarity weight | max | +0.722 | +0.619 | +0.889 | +0.743 |
| recovery-weighted, own | pooled rarity weight | sum over endpoints | +0.944 | +0.429 | +0.833 | +0.735 |
| recovery-weighted, own | combined rarity weight | sum over endpoints | +1.000 | +0.429 | +0.778 | +0.735 |
| recovery-weighted, own | own rarity weight | sum over endpoints | +0.889 | +0.429 | +0.833 | +0.717 |
| recovery-weighted, own | no weight | sum over endpoints | +0.722 | +0.524 | +0.778 | +0.675 |
| recovery-weighted, own | combined rarity weight | sum over modes | +0.889 | +0.333 | +0.778 | +0.667 |
| recovery-weighted, own | combined rarity weight | max | +0.722 | +0.429 | +0.833 | +0.661 |
| recovery-weighted, own | spread weight | sum over endpoints | +0.778 | +0.429 | +0.778 | +0.661 |
| recovery-weighted, own | no weight | sum over modes | +0.722 | +0.429 | +0.829 | +0.660 |
| recovery-weighted, own | spread weight | sum over modes | +0.667 | +0.524 | +0.778 | +0.656 |
| recovery-weighted, own | pooled rarity weight | sum over modes | +0.722 | +0.333 | +0.889 | +0.648 |
| recovery-weighted, own | own rarity weight | sum over modes | +0.722 | +0.429 | +0.778 | +0.643 |
| recovery-weighted, own | pooled rarity weight | max | +0.611 | +0.429 | +0.889 | +0.643 |
| recovery-weighted, own | spread weight | max | +0.611 | +0.619 | +0.667 | +0.632 |
| recovery-weighted, pooled | own rarity weight | sum over endpoints | +0.889 | +0.429 | +0.833 | +0.717 |
| recovery-weighted, pooled | pooled rarity weight | sum over endpoints | +0.889 | +0.429 | +0.833 | +0.717 |
| recovery-weighted, pooled | no weight | sum over endpoints | +0.833 | +0.524 | +0.778 | +0.712 |
| recovery-weighted, pooled | spread weight | sum over modes | +0.722 | +0.619 | +0.778 | +0.706 |
| recovery-weighted, pooled | combined rarity weight | sum over endpoints | +0.889 | +0.429 | +0.778 | +0.698 |
| recovery-weighted, pooled | no weight | sum over modes | +0.833 | +0.429 | +0.829 | +0.697 |
| recovery-weighted, pooled | no weight | max | +0.556 | +0.714 | +0.771 | +0.680 |
| recovery-weighted, pooled | spread weight | sum over endpoints | +0.722 | +0.524 | +0.778 | +0.675 |
| recovery-weighted, pooled | pooled rarity weight | sum over modes | +0.722 | +0.333 | +0.889 | +0.648 |
| recovery-weighted, pooled | pooled rarity weight | max | +0.611 | +0.333 | +0.889 | +0.611 |
| recovery-weighted, pooled | combined rarity weight | sum over modes | +0.722 | +0.333 | +0.778 | +0.611 |
| recovery-weighted, pooled | spread weight | max | +0.611 | +0.524 | +0.667 | +0.601 |
| recovery-weighted, pooled | own rarity weight | sum over modes | +0.667 | +0.333 | +0.778 | +0.593 |
| recovery-weighted, pooled | own rarity weight | max | +0.389 | +0.429 | +0.889 | +0.569 |
| recovery-weighted, pooled | combined rarity weight | max | +0.500 | +0.333 | +0.833 | +0.556 |
| recovery-weighted, combined | own rarity weight | sum over endpoints | +0.944 | +0.429 | +0.833 | +0.735 |
| recovery-weighted, combined | spread weight | sum over endpoints | +0.778 | +0.619 | +0.778 | +0.725 |
| recovery-weighted, combined | pooled rarity weight | sum over endpoints | +0.889 | +0.429 | +0.833 | +0.717 |
| recovery-weighted, combined | combined rarity weight | sum over endpoints | +0.944 | +0.429 | +0.778 | +0.717 |
| recovery-weighted, combined | spread weight | sum over modes | +0.722 | +0.619 | +0.778 | +0.706 |
| recovery-weighted, combined | no weight | sum over endpoints | +0.722 | +0.524 | +0.778 | +0.675 |
| recovery-weighted, combined | no weight | max | +0.500 | +0.714 | +0.771 | +0.662 |
| recovery-weighted, combined | no weight | sum over modes | +0.722 | +0.429 | +0.829 | +0.660 |
| recovery-weighted, combined | combined rarity weight | sum over modes | +0.833 | +0.333 | +0.778 | +0.648 |
| recovery-weighted, combined | pooled rarity weight | sum over modes | +0.722 | +0.333 | +0.833 | +0.630 |
| recovery-weighted, combined | spread weight | max | +0.667 | +0.524 | +0.667 | +0.619 |
| recovery-weighted, combined | pooled rarity weight | max | +0.611 | +0.333 | +0.889 | +0.611 |
| recovery-weighted, combined | own rarity weight | sum over modes | +0.667 | +0.333 | +0.778 | +0.593 |
| recovery-weighted, combined | own rarity weight | max | +0.444 | +0.429 | +0.889 | +0.587 |
| recovery-weighted, combined | combined rarity weight | max | +0.444 | +0.333 | +0.833 | +0.537 |
| unrecovered instances only | no weight | sum over modes | +0.833 | +0.900 | +0.829 | +0.854 |
| unrecovered instances only | combined rarity weight | sum over endpoints | +0.722 | +0.905 | +0.833 | +0.820 |
| unrecovered instances only | pooled rarity weight | sum over endpoints | +0.778 | +0.905 | +0.722 | +0.802 |
| unrecovered instances only | combined rarity weight | sum over modes | +0.722 | +0.810 | +0.833 | +0.788 |
| unrecovered instances only | no weight | sum over endpoints | +0.833 | +0.714 | +0.778 | +0.775 |
| unrecovered instances only | no weight | max | +0.543 | +1.000 | +0.771 | +0.771 |
| unrecovered instances only | own rarity weight | sum over endpoints | +0.667 | +0.810 | +0.833 | +0.770 |
| unrecovered instances only | pooled rarity weight | max | +0.611 | +0.810 | +0.889 | +0.770 |
| unrecovered instances only | pooled rarity weight | sum over modes | +0.667 | +0.810 | +0.833 | +0.770 |
| unrecovered instances only | spread weight | sum over endpoints | +0.778 | +0.810 | +0.722 | +0.770 |
| unrecovered instances only | own rarity weight | sum over modes | +0.667 | +0.810 | +0.778 | +0.751 |
| unrecovered instances only | spread weight | sum over modes | +0.611 | +0.810 | +0.722 | +0.714 |
| unrecovered instances only | own rarity weight | max | +0.500 | +0.714 | +0.889 | +0.701 |
| unrecovered instances only | combined rarity weight | max | +0.389 | +0.810 | +0.833 | +0.677 |
| unrecovered instances only | spread weight | max | +0.667 | +0.619 | +0.667 | +0.651 |

## Appendix: every mode filter

Rules and inputs as defined in `formulas.md`; sorted by mean within each input.

| input | rule | Models·HoVer | Models·TB | Models·LCB | mean |
|---|---|---:|---:|---:|---:|
| endpoints of every instance (no recovery) | per candidate: drop the top 1 mode | +0.588 | +0.647 | +0.697 | +0.644 |
| endpoints of every instance (no recovery) | across candidates: drop modes above mean + 1.5 SD | +0.394 | +0.882 | +0.647 | +0.641 |
| endpoints of every instance (no recovery) | across candidates: drop the top 1 mode | +0.543 | +0.700 | +0.647 | +0.630 |
| endpoints of every instance (no recovery) | per candidate: drop modes above mean + 1.5 SD | +0.294 | +0.867 | +0.697 | +0.619 |
| endpoints of every instance (no recovery) | across candidates: drop the top 2 modes | +0.657 | +0.556 | +0.588 | +0.600 |
| endpoints of every instance (no recovery) | per candidate: drop the top 2 modes | +0.543 | +0.556 | +0.697 | +0.598 |
| endpoints of every instance (no recovery) | across candidates: drop modes above mean + 1 SD | +0.412 | +0.556 | +0.588 | +0.519 |
| endpoints of every instance (no recovery) | per candidate: drop modes above mean + 1 SD | +0.257 | +0.300 | +0.697 | +0.418 |
| endpoints of every instance (no recovery) | across candidates: drop the top 3 modes | +0.471 | -0.125 | +0.600 | +0.315 |
| recovery checked on the endpoints | per candidate: drop the top 1 mode | +0.882 | +0.700 | +0.697 | +0.760 |
| recovery checked on the endpoints | per candidate: drop modes above mean + 1.5 SD | +0.657 | +0.900 | +0.697 | +0.751 |
| recovery checked on the endpoints | per candidate: drop modes above mean + 1 SD | +0.724 | +0.684 | +0.697 | +0.702 |
| recovery checked on the endpoints | across candidates: drop the top 1 mode | +0.471 | +0.600 | +0.588 | +0.553 |
| recovery checked on the endpoints | across candidates: drop modes above mean + 1.5 SD | +0.818 | +0.176 | +0.588 | +0.528 |
| recovery checked on the endpoints | per candidate: drop the top 2 modes | +0.724 | +0.067 | +0.697 | +0.496 |
| recovery checked on the endpoints | across candidates: drop the top 2 modes | +0.758 | +0.067 | +0.588 | +0.471 |
| recovery checked on the endpoints | across candidates: drop modes above mean + 1 SD | +0.706 | +0.067 | +0.600 | +0.458 |
| recovery checked on the endpoints | across candidates: drop the top 3 modes | +0.562 | -0.857 | +0.655 | +0.120 |
| endpoints of unrecovered instances | per candidate: drop modes above mean + 1.5 SD | +0.714 | +1.000 | +0.697 | +0.804 |
| endpoints of unrecovered instances | across candidates: drop the top 1 mode | +0.824 | +0.882 | +0.588 | +0.765 |
| endpoints of unrecovered instances | per candidate: drop the top 1 mode | +0.697 | +0.889 | +0.697 | +0.761 |
| endpoints of unrecovered instances | across candidates: drop modes above mean + 1.5 SD | +0.600 | +1.000 | +0.588 | +0.729 |
| endpoints of unrecovered instances | per candidate: drop the top 2 modes | +0.647 | +0.467 | +0.697 | +0.604 |
| endpoints of unrecovered instances | per candidate: drop modes above mean + 1 SD | +0.647 | +0.444 | +0.697 | +0.596 |
| endpoints of unrecovered instances | across candidates: drop the top 2 modes | +0.600 | +0.412 | +0.588 | +0.533 |
| endpoints of unrecovered instances | across candidates: drop modes above mean + 1 SD | +0.600 | +0.412 | +0.588 | +0.533 |
| endpoints of unrecovered instances | across candidates: drop the top 3 modes | +0.429 | +0.000 | +0.655 | +0.361 |

Generated by `scripts/mode_methods.py` from the recorded judge and recovery runs; no model call.
