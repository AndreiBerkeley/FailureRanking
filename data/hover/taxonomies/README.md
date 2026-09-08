# taxonomies — failure-mode vocabularies for the HoVer program

A taxonomy is a list of failure codes, each with a definition and the evidence
it rests on. It is what the judge holds when it reads a trace. Both taxonomies
here were induced from traces in `cap-1` with no run outcome in view.

| taxonomy | codes | how it was made |
|---|---:|---|
| [`tax-7`](tax-7/README.md) | 7 | generated from cap-1 traces by the taxonomy generator |
| [`tax-18`](tax-18/README.md) | 18 | tax-7 with five codes split into parts that occur independently in the data |
| [`tax-19`](tax-19/README.md) | 18 | tax-18 with the format codes' boundaries amended by hand: the harness's field markers are not failures |
| [`tax-20`](tax-20/README.md) | 10 | tax-19 re-levelled so no code depends on a clause only some candidates have; specifics moved into per-code evidence |

The same failure points in a trace, grouped two ways. `runs/` holds the three
instrument runs that produced them.
