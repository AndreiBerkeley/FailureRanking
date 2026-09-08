"""The default gold-free pipeline path (trust and feedback skipped).

The framework registries ship empty; core/run.build_registry installs the
reviewed options. The default configuration is the plain unique-modes
amplitude expressed in the renumbered pipeline:

    counting:      unique
    relationships: none
    trust:         skipped
    feedback:      skipped
    formula:       uncapped_sum (quality = 1 - sum; can go below 0,
                   which deliberately flags the missing within-task cap)
"""

from __future__ import annotations

from .grid import Configuration

DEFAULT_CONFIGURATION = Configuration.from_mapping(
    {
        "counting": "unique",
        "relationships": "none",
        "formula": "uncapped_sum",
    }
)
