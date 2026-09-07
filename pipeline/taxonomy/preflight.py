#!/usr/bin/env python3
"""Refuse to spend money on a pipeline whose local changes are not loaded.

This exists because of a real incident, recorded in pipeline/CHANGES.md under
"CORRECTION: changes 1-9 targeted a dead code path": nine edits went into
adamast/learning/vendor/pipeline/, the CLI ran adamast/learning/pipeline/, and
two paid runs produced output from the unmodified upstream code. Nothing failed;
the results were simply not what we thought we were measuring.

Two classes of failure are checked.

RESOLUTION  every module resolves inside pipeline/, not the vendor subtree and
not the upstream checkout at ~/Desktop/AdaMAST-private.

PRESENCE    every local change is present in the file that is actually imported,
identified by a marker string from the change itself. A marker that stops
matching means the change was lost in a re-vendor, and the run stops.

Markers are whole phrases, never bare identifiers: a bare identifier is a
substring of any renamed version of itself, so appending to it would not trip
the check. Markers are semantic. A prompt reworded around one will
fail this check, which is the intended behaviour: re-confirm the change is still
there, then update the marker.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

PIPE = Path("/Users/andreicojocaru/Desktop/FailureRank/pipeline")

# module -> [(marker, what it guards)]
CHECKS: dict[str, list[tuple[str, str]]] = {
    "adamast.learning.pipeline.draft": [
        ("ADAMAST_STRUCTURE_FILE",
         "manual program structure hook, skips inference"),
        ("Text authored by the CANDIDATE only",
         "signals scan candidate text, not task or retrieved documents"),
        ("MODE STYLE CONTRACT",
         "code style contract: an act not a lack, no remedy in identity"),
    ],
    "adamast.learning.pipeline.agreement": [
        ("elided by the EVALUATION HARNESS",
         "annotators see the whole trace, not ~5 percent of it"),
        ("MAX_AGENT_OUTPUT_CHARS",
         "explicit elision budgets rather than silent truncation"),
        ("INTERNAL_REFINEMENT",
         "the gate measures and does not rewrite the taxonomy mid-run"),
    ],
    "adamast.core.taxonomy_data": [
        ('"when_to_use"',
         "from_flat carries when_to_use / when_not_to_use"),
    ],
    "adamast.learning.api": [
        ("hidden refine-and-measure cycle",
         "generation can emit a draft without an agreement pass"),
    ],
    "adamast.foundation_cli": [
        ("--no-agreement",
         "the CLI flag the pipeline passes to skip generation's gate"),
    ],
}

FORBIDDEN = ("learning/vendor/", "AdaMAST-private")


def check() -> list[str]:
    problems: list[str] = []
    for modname, markers in CHECKS.items():
        try:
            mod = importlib.import_module(modname)
        except Exception as exc:                               # noqa: BLE001
            problems.append(f"{modname}: cannot import ({exc})")
            continue

        path = Path(getattr(mod, "__file__", "") or "")
        if not path.exists():
            problems.append(f"{modname}: no file on disk")
            continue
        if PIPE not in path.parents:
            problems.append(f"{modname}: resolves OUTSIDE the vendored copy -> {path}")
            continue
        if any(bad in str(path) for bad in FORBIDDEN):
            problems.append(f"{modname}: resolves to a dead path -> {path}")
            continue

        text = path.read_text(errors="ignore")
        for marker, guards in markers:
            if marker not in text:
                problems.append(
                    f"{modname}: LOCAL CHANGE MISSING -- {guards!r} "
                    f"(marker {marker!r} not found in {path.name})")
    return problems


def assert_ready() -> None:
    problems = check()
    if problems:
        raise SystemExit(
            "preflight failed; refusing to spend on a pipeline that is not the "
            "one we think it is:\n  " + "\n  ".join(problems))


if __name__ == "__main__":
    sys.path.insert(0, str(PIPE))
    bad = check()
    if bad:
        print("PREFLIGHT FAILED")
        for b in bad:
            print("  " + b)
        raise SystemExit(1)
    n = sum(len(v) for v in CHECKS.values())
    print(f"preflight OK: {len(CHECKS)} modules resolve inside {PIPE}, "
          f"{n} local changes present")
