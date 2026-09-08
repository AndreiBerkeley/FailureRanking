# results — what methods produce

`results/<benchmark>/<mapping>/<method>/` holds scores and validation for one method on one judge
mapping. No traces, mappings or taxonomies live here: those are evidence and belong in `data/`.
Each `scores.json` records the formula, what it read, the per-candidate scores and the validation
against a named target, so a number can be traced without rerunning anything.
