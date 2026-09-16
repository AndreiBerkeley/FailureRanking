# hover

Multi-hop claim verification. Every candidate runs the same four-module DSPy program —
summarise the hop-1 passages, write the hop-2 query, summarise, write the hop-3 query — with
three retrievals done by the harness between modules. Gold = all three supporting Wikipedia
titles retrieved. `program/structure.json` is the machine description both instruments read.

```
program/            structure.json — modules, roles, handoffs
tasks/              tasks.jsonl (claim, label, gold titles) and the master split pools-1
GEPA_candidates/    12 instruction sets from an optimizer run, one model — 100 judged tasks
models/             9 models, one instruction set — 50 + 50 judged tasks
```

**A trace** is the judge's view of one run: the four module turns in order, each with the
instructions the module had (its DSPy signature), the input it received (claim, passages,
earlier summaries) and the output it produced. The three retrievals appear as environment
blocks. Retrieval is a harness step: a hop-1 miss is not a candidate act; what is
attributable is whether hops 2 and 3 recover from it.

Two candidate sets, two judges, one program. The sets are not comparable to each other and
are reported separately; each has its own generalization gold on its own 500-task portion.
