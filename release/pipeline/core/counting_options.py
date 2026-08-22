"""Segment 2 — per-mode counting basis (reviewed 2026-08-18).

What we consider per task from a failure mode, nothing else:

  unique   each distinct code counts once per task ("A.6")
  flagged  distinct codes, marked once vs repeated ("A.6|once" /
           "A.6|repeated") — bounded within-task persistence
  total    every occurrence counts ("A.6" repeated k times)

Relationships between modes are segment 3's business.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .segments import Registry


def counting_unique(records: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted({str(r["code"]) for r in records})


def counting_flagged(records: Sequence[Mapping[str, Any]]) -> list[str]:
    counts = Counter(str(r["code"]) for r in records)
    return [
        f"{code}|repeated" if counts[code] > 1 else f"{code}|once"
        for code in sorted(counts)
    ]


def counting_total(records: Sequence[Mapping[str, Any]]) -> list[str]:
    counts = Counter(str(r["code"]) for r in records)
    return [code for code in sorted(counts) for _ in range(counts[code])]


def install_counting_options(registry: Registry) -> None:
    registry.register(
        "counting", "unique", counting_unique,
        description="each distinct failure mode counts once per task",
    )
    registry.register(
        "counting", "flagged", counting_flagged,
        description="distinct modes, marked once vs repeated",
    )
    registry.register(
        "counting", "total", counting_total,
        description="every occurrence counts",
    )
