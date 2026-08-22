"""Segment interfaces and the option registry for the FailureRank grid.

The pipeline (docs/SEGMENTS.md, renumbered with Andrei 2026-08-18):

  1. Judge mappings   (static)  the portable mapping + resolution
                                preprocessor; edits belong in trust.
  2. Counting         (axis)    what we consider per task from a failure
                                mode: unique / flagged / total.
  3. Relationships    (axis)    what we consider between failure modes:
                                none / pairs / groups / signatures / order.
  4. Trust            (axis, optional)  instrument self-testimony weights.
  5. Feedback         (axis, optional)  gold or recovery consequences —
                                the only axis allowed to read training
                                gold; doing so marks scenario 1.
  6. Formula          (axis)    how instances become a task burden: the
                                within-task combination and its pricing.
  7. Ranking          (static)  HIGHER SCORE IS BETTER. The runner turns
                                each task burden into quality (1 - burden)
                                and the candidate score is mean quality;
                                ties share average rank.

Axis contracts (enforced by the grid runner):

  counting       task records -> base instances (per-mode items; ids like
                 "A.6", "A.6|repeated", possibly repeated under total).
  relationships  (base instances, task records) -> final instance list
                 (may add group items "A.6+C.2", replace with signature
                 "sig:...", or pass through unchanged).
  trust          instance + records -> weight in [0, 1]; absent = 1.
  feedback       instance + candidate context -> influence in [0, 1];
                 absent = 1.
  formula        entries (item, weight, influence, value) + candidate
                 context -> one task burden. All overlap policy lives
                 here. Across-task aggregation is fixed (mean quality).

Options declare `requires`/`provides` capability tags; the grid skips
configurations whose requirements are unmet. Registries ship EMPTY —
methods are installed explicitly after review (core/run.build_registry).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

AXES = (
    "counting",        # segment 2
    "relationships",   # segment 3
    "trust",           # segment 4 (optional)
    "feedback",        # segment 5 (optional)
    "formula",         # segment 6
)
OPTIONAL_AXES = frozenset({"trust", "feedback"})

#: Fixed segment-7 convention, applied by the bench, never varied.
RANKING_CONVENTION = {
    "direction": "higher_is_better",
    "ties": "average_rank",
}


@dataclass(frozen=True)
class Option:
    """One registered method for one axis."""

    axis: str
    name: str
    fn: Callable[..., Any]
    requires: frozenset[str] = field(default_factory=frozenset)
    provides: frozenset[str] = field(default_factory=frozenset)
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


class Registry:
    """Holds the known options per axis. Instantiable for isolated tests;
    the module-level DEFAULT starts empty."""

    def __init__(self) -> None:
        self._options: dict[str, dict[str, Option]] = {a: {} for a in AXES}

    def register(
        self,
        axis: str,
        name: str,
        fn: Callable[..., Any],
        requires: frozenset[str] | set[str] = frozenset(),
        provides: frozenset[str] | set[str] = frozenset(),
        params: dict[str, Any] | None = None,
        description: str = "",
    ) -> Option:
        if axis not in AXES:
            raise ValueError(f"unknown axis {axis!r}; expected one of {AXES}")
        if name in self._options[axis]:
            raise ValueError(f"option {name!r} already registered for {axis!r}")
        option = Option(
            axis=axis,
            name=name,
            fn=fn,
            requires=frozenset(requires),
            provides=frozenset(provides),
            params=dict(params or {}),
            description=description,
        )
        self._options[axis][name] = option
        return option

    def get(self, axis: str, name: str) -> Option:
        try:
            return self._options[axis][name]
        except KeyError:
            known = sorted(self._options.get(axis, {}))
            raise KeyError(
                f"no option {name!r} for axis {axis!r}; registered: {known}"
            ) from None

    def options(self, axis: str) -> list[Option]:
        return list(self._options[axis].values())

    def names(self, axis: str) -> list[str]:
        return sorted(self._options[axis])

    def is_empty(self) -> bool:
        return all(not opts for opts in self._options.values())


#: The shared registry. Deliberately empty at import.
DEFAULT = Registry()
