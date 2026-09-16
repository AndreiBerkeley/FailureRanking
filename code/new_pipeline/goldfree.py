#!/usr/bin/env python3
"""One definition of "gold-free", shared by every stage that touches a trace.

The invariant: no candidate, judge, taxonomy generation, refinement or gate ever
sees a task outcome. Two separate things have to hold, and only one of them is
enforceable here.

ENFORCEABLE  no outcome-bearing field reaches a model prompt. That is what this
module does, at the corpus boundary, by key-name pattern rather than a fixed
list so a new field in a future trace format is dropped by default instead of
leaking silently.

NOT ENFORCEABLE HERE  that the candidate never saw the gold answer at inference
time. That is a property of how the traces were captured, upstream of us.

WHY A PATTERN AND NOT A LIST
The vendored pipeline derives `final_verdict` from a `reward` field and injects
it into three prompt sites (agreement.py:1152, 1471, 1753), and one parser
writes `reward=<value>` directly into trajectory text (draft.py:3963). Our trace
format happens not to populate `reward`, so `final_verdict` degrades to a
constant and none of that fires. That is an accident of format, not a guarantee.
Stripping at the boundary makes it a guarantee for any format.

Measured on the live corpora before this existed: 0 real leaks across all six
corpora. Every keyword hit was ordinary prose -- "accept" in a geometry proof,
"gold medals" and "gold prospectors" in retrieved documents. Keyword scanning
alone is not evidence of absence, which is why the strip is structural.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

OUTCOME_KEY_PATTERN = re.compile(
    r"outcome|score|reward|passed|pass_fail|correct|gold|label|eval|ground_truth|"
    r"verdict|is_right|success", re.I)

# Default-deny plus a narrow, explicit allowlist. Narrowing the PATTERN instead
# would reintroduce the leak risk the pattern exists to remove, so a field that
# merely matches the pattern without carrying an outcome is named here and
# justified, one by one.
SAFE_KEYS = {
    "evaluation_repeat",   # which repeat this trace is, 0-4. An index, not a result.
}

# Candidate-authored content is never filtered: it is the evidence being judged,
# and a candidate writing "the correct answer is 5" is behaviour, not a leak.
CONTENT_KEYS = {"messages", "trace", "raw_trajectory", "agent_outputs"}


def strip(obj, _path=""):
    """Drop every outcome-bearing key. Returns (cleaned, [removed paths])."""
    removed = []

    def walk(o, path):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                p = f"{path}.{k}" if path else str(k)
                if k in CONTENT_KEYS:
                    out[k] = v                      # candidate's own work, verbatim
                elif k in SAFE_KEYS:
                    out[k] = walk(v, p)
                elif OUTCOME_KEY_PATTERN.search(str(k)):
                    removed.append(p)
                else:
                    out[k] = walk(v, p)
            return out
        if isinstance(o, list):
            return [walk(v, f"{path}[]") for v in o]
        return o

    return walk(obj, _path), removed


def strip_file(src: Path, dst: Path) -> list[str]:
    """Write a gold-free copy of one trace. Idempotent."""
    clean, removed = strip(json.loads(Path(src).read_text()))
    Path(dst).write_text(json.dumps(clean, ensure_ascii=False, indent=2))
    return removed


def offending_keys(trace: dict) -> list[str]:
    """Outcome-bearing keys present in a trace, ignoring candidate content."""
    _, removed = strip(trace)
    return removed


def assert_gold_free(corpus: Path, label: str = "") -> int:
    """Hard-fail if any trace in a corpus still carries an outcome field."""
    bad = {}
    files = sorted(Path(corpus).glob("*.json"))
    for p in files:
        try:
            keys = offending_keys(json.loads(p.read_text()))
        except Exception:                                      # noqa: BLE001
            continue
        if keys:
            bad[p.name] = keys
    if bad:
        sample = list(bad.items())[:3]
        raise SystemExit(
            f"gold leak in {label or corpus}: {len(bad)} of {len(files)} traces "
            f"carry outcome fields, e.g. {sample}")
    return len(files)
