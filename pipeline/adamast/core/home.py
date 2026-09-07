"""The one definition of the AdaMAST base directory.

``ADAMAST_HOME`` moves the ``~/.adamast`` base directory (see
``docs/CONFIGURATION.md``). Every root derived from it — the taxonomy store,
the trace root, the project-root cache, and the interactive routing root —
resolves through this module so they cannot disagree about what the base is.

Two behaviors are deliberate and were previously inconsistent between callers:

* An **empty or whitespace-only** value counts as unset. Reading the variable
  with ``os.environ.get("ADAMAST_HOME", default)`` returns ``""`` when it is
  set-but-empty, and ``Path("")`` is the *current working directory* — so an
  empty value silently scattered AdaMAST state into whatever directory a hook
  happened to run in.
* The result is **absolute**, and a relative value is anchored to the user's
  home directory rather than the process working directory. Hooks run under
  varying working directories, so a cwd-relative value resolves differently
  per invocation and splits one program's state across several directories.
"""

from __future__ import annotations

import os
from pathlib import Path


def adamast_home() -> Path:
    """Return the AdaMAST base directory as an absolute path.

    Read at call time rather than captured at import so a value set after
    import (tests, wrappers that relocate the home before invoking a command)
    still takes effect. Callers that need an import-time constant may snapshot
    the result, accepting that later changes will not apply to them.
    """
    return env_path("ADAMAST_HOME", Path.home() / ".adamast")


def env_path(variable: str, default: Path) -> Path:
    """Resolve one path-valued environment variable, or ``default``.

    Applies the same rules to every AdaMAST path variable so they cannot
    disagree: an empty or whitespace-only value counts as unset, and the
    result is absolute, with a relative value anchored to the user's home
    directory. ``ADAMAST_STORE_DIR`` and ``ADAMAST_TRACE_ROOT`` need this as
    much as ``ADAMAST_HOME`` does — a relative value in any of them would
    otherwise follow the working directory of whichever hook happens to run.
    """
    configured = (os.environ.get(variable) or "").strip()
    if not configured:
        return Path(default).expanduser().resolve()
    chosen = Path(configured).expanduser()
    if not chosen.is_absolute():
        # Anchor to the user's home directory, never the process working
        # directory. ``Path.resolve()`` alone only makes the value absolute
        # *relative to the current cwd*, so a relative setting still landed
        # in a different place per hook invocation — the exact split this
        # module exists to prevent.
        chosen = Path.home() / chosen
    return chosen.resolve()
