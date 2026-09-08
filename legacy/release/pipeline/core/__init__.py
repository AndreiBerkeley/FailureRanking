"""FailureRank core: the segmented scoring framework and its grid runner.

See docs/SEGMENTS.md for the frozen segment specification. The option
registries ship empty; methods are registered one at a time after review.
"""

from .segments import AXES, DEFAULT, OPTIONAL_AXES, RANKING_CONVENTION, Registry

__all__ = [
    "AXES",
    "DEFAULT",
    "OPTIONAL_AXES",
    "RANKING_CONVENTION",
    "Registry",
]
