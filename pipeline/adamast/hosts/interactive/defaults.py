"""Defaults shared by interactive Codex and Claude Code installations."""

from __future__ import annotations

from pathlib import Path

from adamast.core.home import adamast_home
from adamast.core.program import INTERACTIVE_SESSION_MODEL

# Re-exported alias: the runtime owns the sentinel because begin_session
# must recognize it when reconciling against recorded program state.
INTERACTIVE_ADAMAST_MODEL = INTERACTIVE_SESSION_MODEL

# Re-exported so host code has one import site for interactive defaults; the
# canonical definition lives in adamast.core.home.
__all__ = ["INTERACTIVE_ADAMAST_MODEL", "adamast_home", "default_interactive_trace_output"]


def default_interactive_trace_output(home: Path | None = None) -> Path:
    """Return the shared project-scoped store used by user-level hooks.

    Resolves under ``ADAMAST_HOME`` when it is set, so the routing root moves
    with the documented base directory like the taxonomy store, the trace root,
    and the project-root cache already do.

    ``home`` is an explicit *user home* directory (``.adamast/interactive`` is
    appended to it) and bypasses ``ADAMAST_HOME`` entirely. Prefer calling with
    no argument: passing ``Path.home()`` is what previously pinned every
    installer to the real home regardless of the environment.
    """
    if home is not None:
        return home / ".adamast" / "interactive"
    return adamast_home() / "interactive"
