#!/usr/bin/env python3
"""Prompts, parsed out of GENERATION_v2.md at import time.

The design document is the single source. Copying the prompts into Python would
let the two drift, and a prompt that differs from the document describing it is
the hardest kind of bug to notice -- you read the document, believe it, and are
wrong. A missing section fails loudly here rather than silently shipping a stale
prompt.
"""
from __future__ import annotations

import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "GENERATION_v2.md"

SECTIONS = {
    "preamble": "## Shared preamble (every generation prompt)",
    "stage1":   "## Stage 1 — field analysis",
    "stage2a":  "### 2a — the work",
    "stage2a_ledger": "### 2a-ledger — the work, with the step ledger in the output",
    "stage2b":  "### 2b — conformance",
    "stage3":   "## Stage 3 — abstraction",
    "stage4":   "## Stage 4 — applicability",
    "stage5":   "## Stage 5 — consolidation",
    "stage6":   "## Stage 6 — rule validation",
    "stage7a":  "### 7a — reviewer checklist",
    "stage7b":  "### 7b — consolidation",
    "stage7c":  "### 7c — operations",
}


def _blocks(text: str) -> dict:
    out = {}
    for key, heading in SECTIONS.items():
        i = text.find(heading)
        if i < 0:
            raise SystemExit(f"prompts: section not found in {DOC.name}: {heading!r}")
        j = text.find("```", i)
        k = text.find("```", j + 3)
        if j < 0 or k < 0:
            raise SystemExit(f"prompts: no fenced block under {heading!r}")
        out[key] = text[j + 3:k].strip("\n")
    return out


_B = _blocks(DOC.read_text())

PREAMBLE = _B["preamble"]
STAGE1 = _B["stage1"]
STAGE2A = _B["stage2a"]
STAGE2A_LEDGER = _B["stage2a_ledger"]
STAGE2B = _B["stage2b"]
STAGE3 = _B["stage3"]
STAGE4 = _B["stage4"]
STAGE5 = _B["stage5"]
STAGE6 = _B["stage6"]
STAGE7A = _B["stage7a"]
STAGE7B = _B["stage7b"]
STAGE7C = _B["stage7c"]


# The placeholders as they are WRITTEN IN THE DOCUMENT. They are human-readable
# there, with spaces and punctuation, so a semantic key is mapped to the literal
# text rather than guessed. Guessing produced a prompt with no traces in it that
# would still have been sent.
PLACEHOLDERS = {
    "traces":       "{trace excerpts, outcome-blind}",
    "domain":       "{domain_analysis}",
    "contracts":    "{contracts}",
    "observations": "{observations}",
    "modes":        "{all modes}",
    "codes":        "{all modes and specialised codes}",
    "taxonomy":     "{the taxonomy, code by code}",
    "evidence":     "{evidence base}",
    "unmapped":     "{unmapped problems}",
    "panel":        "{panel checklists}",
    "checklist":    "{consolidated checklist}",
}

# Stage 2 is discovery and runs WITHOUT the framework preamble. Its rules exist
# to decide what belongs in a taxonomy; applied during observation they suppress
# candidates before they are written down, which is not a filter anyone can
# inspect. Measured: doing so cost about four fifths of the vocabulary.
NO_PREAMBLE = {"stage2a", "stage2a_ledger", "stage2b"}

STAGE_NEEDS = {
    "stage1": ["traces"],
    "stage2a_ledger": ["traces"],
    "stage2a": ["traces"],
    "stage2b": ["contracts", "traces"],
    "stage3": ["observations", "domain", "contracts"],
    "stage4": ["modes", "contracts", "traces"],
    "stage5": ["codes"],
    "stage6": [],
    "stage7a": ["contracts", "taxonomy", "evidence"],
    "stage7b": ["taxonomy", "panel"],
    "stage7c": ["contracts", "taxonomy", "checklist", "unmapped"],
}


def build(stage: str, **fields) -> str:
    """Preamble + stage body with placeholders filled.

    Substitution is literal, and completeness is checked on the TEMPLATE before
    anything is inserted -- never on the filled text. Trace content contains
    braces of its own (LaTeX especially), so scanning the result for leftover
    placeholders reports the candidate's own output as an unfilled field.
    """
    body = {"stage1": STAGE1, "stage2a": STAGE2A, "stage2a_ledger": STAGE2A_LEDGER,
            "stage2b": STAGE2B,
            "stage3": STAGE3, "stage4": STAGE4, "stage5": STAGE5,
            "stage6": STAGE6, "stage7a": STAGE7A, "stage7b": STAGE7B, "stage7c": STAGE7C}[stage]
    need = STAGE_NEEDS[stage]
    missing = [k for k in need if k not in fields]
    if missing:
        raise SystemExit(f"prompts.build({stage}): missing {missing}")
    extra = [k for k in fields if k not in need]
    if extra:
        raise SystemExit(f"prompts.build({stage}): unexpected {extra}")

    text = body if stage in NO_PREAMBLE else (
        PREAMBLE + "\n\n" + ("=" * 70) + "\n\n" + body)
    for key in need:
        token = PLACEHOLDERS[key]
        if token not in text:
            raise SystemExit(
                f"prompts.build({stage}): {token!r} not present in the document "
                "section; the prompt and the code disagree about its name")
        text = text.replace(token, str(fields[key]))
    for key, token in PLACEHOLDERS.items():
        if token in text:
            raise SystemExit(f"prompts.build({stage}): {token!r} left unfilled")
    return text
