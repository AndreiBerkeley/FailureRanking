# mappings — what the judge found in each trace

A mapping is the judge's reading of one capture under one taxonomy: for every
trace, which failure codes occurred and how many times. It is the evidence the
analyses in `../../../analyses/` are built from, and the only thing about a
trace that a scoring path reads.

| mapping | taxonomy | capture | judged | status |
|---|---|---|---:|---|
| [`map-1`](./map-1/README.md) | `tax-7` | `cap-2` (sample) | 600 / 600 | complete |
| [`map-2`](./map-2/README.md) | `tax-7` | `cap-3` (domain) | 2,136 / 6,000 | partial, 36% |
| [`map-3`](./map-3/README.md) | `tax-18` | `cap-2` (sample) | 600 / 600 | complete |
| [`map-4`](./map-4/README.md) | `tax-18` | `cap-3` (domain) | 2,187 / 6,000 | partial, 36% |

`map-1` and `map-3` read the same 600 traces under the two taxonomies; `map-2`
and `map-4` read the same subset of the domain traces. Comparing a sample
mapping with its domain mapping is checkpoint 1's first experiment.

A mapping is a frozen snapshot of a judge run. If a partial run is later
completed, the completed run is a new mapping; the partial one stays because
analyses cite it. Numbered ids survive a second judge configuration on the
same taxonomy and capture; this table says which is which.
