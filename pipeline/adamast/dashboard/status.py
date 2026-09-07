"""Program-health inspection for AdaMAST trace_output directories."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from adamast.core.config import add_config_argument, config_value, load_adamast_config
from adamast.core.evidence import EVIDENCE_FILE
from adamast.core.program import MANIFEST_NAME, ProgramWorkspace
from adamast.core.project_scope import project_key
from adamast.core.traces import TraceStore
from adamast.hosts.interactive.defaults import default_interactive_trace_output


def program_health(trace_output: Path | str) -> dict[str, Any]:
    root = Path(trace_output).expanduser().resolve()
    manifest_path = root / MANIFEST_NAME
    if manifest_path.is_file():
        workspace = ProgramWorkspace(root)
        stale_sessions = workspace.reconcile_stale_sessions()
        manifest = workspace.load()
    else:
        stale_sessions = []
        manifest = {}
    evidence = _read_json(root / EVIDENCE_FILE)
    decisions = _recent_decisions(root)
    generation = manifest.get("generation") or {}
    refinement = manifest.get("refinement") or {}
    usage = manifest.get("usage") or {}
    return {
        "monitor": _resolve_monitor(manifest, root),
        "trace_output": str(root),
        "manifest_exists": manifest_path.is_file(),
        "program_id": manifest.get("program_id"),
        "repo": manifest.get("repo"),
        "adamast_model": manifest.get("adamast_model"),
        "active_taxonomy_id": manifest.get("taxonomy_id") or "mast",
        "active_sessions": manifest.get("active_sessions", []),
        "reconciled_stale_sessions": stale_sessions,
        "pending_traces": TraceStore(root / "pending").count(),
        "generation": {
            "state": generation.get("state", "unknown"),
            "last_error": generation.get("last_error"),
            "retry_after_count": generation.get("retry_after_count"),
        },
        "refinement": {
            "state": refinement.get("state", "unknown"),
            "last_error": refinement.get("last_error"),
            "rounds_completed": refinement.get("rounds_completed", 0),
            "traces_since_refinement": refinement.get("traces_since_refinement", 0),
            "trace_refs": len(refinement.get("trace_refs", [])),
        },
        "evidence": {
            "checkpoint_count": len(evidence.get("checkpoints", []))
            if isinstance(evidence, dict)
            else 0,
            "taxonomy_count": len(evidence.get("taxonomies", {}))
            if isinstance(evidence, dict)
            else 0,
        },
        "usage": {
            "totals": usage.get("totals") or {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            },
            "recent_events": (usage.get("events") or [])[-10:],
        },
        "recent_decisions": decisions,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Show AdaMAST program health. With no trace_output, auto-target the "
            "most relevant session under the routing root and list recent ones."
        )
    )
    add_config_argument(parser)
    parser.add_argument("trace_output", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--open",
        action="store_true",
        help="reopen the resolved session's live monitor tab in a browser",
    )
    args = parser.parse_args(argv)
    try:
        config = load_adamast_config(args.config)
        # An explicit CLI argument keeps the historical single-program behavior.
        if args.trace_output:
            return _emit_single(args.trace_output, args)
        # Otherwise the routing root (whole AdaMAST home) is the target. It comes
        # from adamast.json when set, else the default interactive home.
        configured = config_value(args, config, "trace_output")
        routing_root = (
            Path(configured).expanduser().resolve()
            if configured
            else default_interactive_trace_output().expanduser().resolve()
        )
        # A config that names one program directly (it has a manifest) stays on
        # the single-program path for backward compatibility.
        if (routing_root / MANIFEST_NAME).is_file():
            return _emit_single(str(routing_root), args)
        return _emit_navigate(navigate(routing_root), args)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _emit_single(trace_output: Path | str, args: argparse.Namespace) -> int:
    health = program_health(trace_output)
    if args.json:
        print(json.dumps(health, indent=2, ensure_ascii=False))
    else:
        print(_render_text(health))
    _maybe_open(health, args)
    return 0


def _emit_navigate(nav: dict[str, Any], args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps(nav, indent=2, ensure_ascii=False))
    else:
        print(_render_navigate(nav))
    if nav.get("default"):
        _maybe_open(nav["default"], args)
    elif args.open:
        print(
            "No live monitor to open; start a session to launch one.",
            file=sys.stderr,
        )
    return 0


def _maybe_open(health: dict[str, Any], args: argparse.Namespace) -> None:
    if not args.open:
        return
    links = (health.get("monitor") or {}).get("links") or []
    if links:
        import webbrowser

        webbrowser.open(links[0]["url"])
    else:
        print(
            "No live monitor to open; start a session to launch it.",
            file=sys.stderr,
        )


def navigate(
    routing_root: Path | str,
    *,
    cwd: Path | str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Auto-target a default session under a routing root, plus recent ones.

    Callers who do not know a concrete program path get a usable landing view:
    the most relevant session (CWD-aware, then most-recently-active) resolved to
    full health, and a short list of other recent sessions to switch between.
    """
    root = Path(routing_root).expanduser().resolve()
    summaries = [_summarize_program(program) for program in _enumerate_programs(root)]
    ranked = sorted(
        summaries,
        key=lambda item: (item["live"], item["activity_unix"]),
        reverse=True,
    )
    default = _select_default(summaries, cwd)
    return {
        "mode": "navigate",
        "routing_root": str(root),
        # Nothing here does not always mean nothing anywhere: a host launched
        # without ADAMAST_HOME in its environment (GUI app launches do not
        # inherit a shell profile) records its programs under a different root
        # than a terminal that has it set. Point at the other root instead of
        # reporting an empty home.
        "elsewhere": None if summaries else _sessions_elsewhere(root),
        "default": (
            program_health(default["trace_output"]) if default else None
        ),
        "recent_sessions": ranked[:limit],
    }


def _sessions_elsewhere(searched: Path) -> dict[str, Any] | None:
    """Find programs under a plausible *other* routing root, or return None.

    Only the roots AdaMAST itself would pick are considered: the environment's
    root (``ADAMAST_HOME``) and the plain user home. When they differ, one of
    them can hold every program while the other looks empty.
    """
    candidates = {
        default_interactive_trace_output().expanduser().resolve(),
        (Path.home() / ".adamast" / "interactive").resolve(),
    }
    for candidate in sorted(candidates):
        if candidate == searched:
            continue
        found = _enumerate_programs(candidate)
        if found:
            return {"routing_root": str(candidate), "programs": len(found)}
    return None


def _enumerate_programs(routing_root: Path) -> list[Path]:
    """Find every program manifest under a routing root, cheaply and bounded."""
    if not routing_root.is_dir():
        return []
    found: list[Path] = []
    patterns = (
        "projects/*/groups/*/program",
        ".adamast-conversation-branches/*/program",
    )
    for pattern in patterns:
        for program in sorted(routing_root.glob(pattern)):
            if (program / MANIFEST_NAME).is_file():
                found.append(program)
    return found


def _summarize_program(program_dir: Path) -> dict[str, Any]:
    manifest_path = program_dir / MANIFEST_NAME
    manifest = _read_json(manifest_path)
    recorded = manifest.get("monitor") or {}
    project_id = _program_project_key(program_dir) or recorded.get("project_id")
    conversation_id = (
        recorded.get("conversation_id")
        or (manifest.get("branch") or {}).get("conversation_id")
        or _first_session_id(manifest)
    )
    return {
        "trace_output": str(program_dir),
        "project_id": project_id,
        "conversation_id": conversation_id,
        "live": bool(manifest.get("active_sessions")),
        "activity_unix": _program_activity(manifest, manifest_path),
        "monitor": _resolve_monitor(manifest, program_dir),
    }


def _select_default(
    summaries: list[dict[str, Any]],
    cwd: Path | str | None,
) -> dict[str, Any] | None:
    if not summaries:
        return None
    # CWD-aware: a session for the current project wins over a busier stranger.
    key = project_key(cwd)
    scoped = [item for item in summaries if item["project_id"] == key]
    pool = scoped or summaries
    return max(pool, key=lambda item: (item["live"], item["activity_unix"]))


def _program_project_key(program_dir: Path) -> str | None:
    parts = program_dir.parts
    if "projects" in parts:
        index = parts.index("projects")
        if index + 1 < len(parts):
            return parts[index + 1]
    return None


def _first_session_id(manifest: dict[str, Any]) -> str | None:
    for item in manifest.get("active_sessions", []):
        if isinstance(item, dict) and item.get("session_id"):
            return str(item["session_id"])
    return None


def _program_activity(manifest: dict[str, Any], manifest_path: Path) -> float:
    """Most-recent activity timestamp: heartbeats/usage, else manifest mtime."""
    times: list[float] = []
    for item in manifest.get("active_sessions", []):
        if not isinstance(item, dict):
            continue
        for field in ("heartbeat_at_unix", "started_at_unix"):
            value = item.get(field)
            if isinstance(value, int | float):
                times.append(float(value))
    events = (manifest.get("usage") or {}).get("events") or []
    if events and isinstance(events[-1], dict):
        value = events[-1].get("timestamp_unix")
        if isinstance(value, int | float):
            times.append(float(value))
    if times:
        return max(times)
    try:
        return manifest_path.stat().st_mtime
    except OSError:
        return 0.0


def _resolve_monitor(manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    """Re-derive the live monitor link from persisted, port-independent coords.

    The port a monitor binds to changes between runs, so a saved URL goes
    stale. Instead we resolve the server's *current* URL from its live state
    file and rebuild the project/conversation deep link on demand.
    """
    recorded = manifest.get("monitor") or {}
    monitor_root = recorded.get("root") or str(root)
    project_id = recorded.get("project_id")
    conversation_id = recorded.get("conversation_id")
    monitor: dict[str, Any] = {
        "root": monitor_root,
        "project_id": project_id,
        "conversation_id": conversation_id,
        "live_url": None,
        "links": [],
    }
    try:
        from adamast.dashboard.server import monitor_deep_link, resolve_monitor_url

        base_url = resolve_monitor_url(monitor_root, monitor_mode=bool(recorded))
    except Exception:
        return monitor
    if not base_url:
        return monitor
    monitor["live_url"] = base_url
    monitor["links"] = [
        {
            "conversation_id": conversation_id,
            "url": monitor_deep_link(
                base_url,
                project_id=project_id,
                conversation_id=conversation_id,
            ),
        }
    ]
    return monitor


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _recent_decisions(root: Path, *, limit: int = 10) -> list[str]:
    lines: list[str] = []
    for name in ("decisions.log", "codex-decisions.log"):
        path = root / name
        try:
            lines.extend(path.read_text(encoding="utf-8").splitlines())
        except OSError:
            continue
    return lines[-limit:]


def _render_text(health: dict[str, Any]) -> str:
    generation = health["generation"]
    refinement = health["refinement"]
    lines = [
        f"trace_output: {health['trace_output']}",
        f"program_id: {health.get('program_id') or '(no manifest)'}",
        f"repo: {health.get('repo') or '(none)'}",
        f"active_taxonomy_id: {health['active_taxonomy_id']}",
        f"active_sessions: {len(health['active_sessions'])}",
        f"pending_traces: {health['pending_traces']}",
        (
            "generation: "
            f"{generation['state']} last_error={generation.get('last_error')!r}"
        ),
        (
            "refinement: "
            f"{refinement['state']} rounds={refinement['rounds_completed']} "
            f"since={refinement['traces_since_refinement']} "
            f"last_error={refinement.get('last_error')!r}"
        ),
        (
            "evidence: "
            f"{health['evidence']['checkpoint_count']} checkpoints across "
            f"{health['evidence']['taxonomy_count']} taxonomy record(s)"
        ),
        (
            "usage: "
            f"calls={health['usage']['totals'].get('calls', 0)} "
            f"input_tokens={health['usage']['totals'].get('input_tokens', 0)} "
            f"output_tokens={health['usage']['totals'].get('output_tokens', 0)} "
            f"cost_usd={health['usage']['totals'].get('cost_usd', 0.0)}"
        ),
    ]
    monitor = health.get("monitor") or {}
    if monitor.get("live_url"):
        lines.append(f"monitor: {monitor['live_url']}")
        for link in monitor.get("links", []):
            conversation = link.get("conversation_id") or "(program)"
            lines.append(f"  {conversation}: {link['url']}")
    elif monitor.get("root"):
        lines.append("monitor: no live server (start a session to launch it)")
    if health["recent_decisions"]:
        lines.append("recent_decisions:")
        lines.extend(f"  {line}" for line in health["recent_decisions"])
    return "\n".join(lines)


def _render_navigate(nav: dict[str, Any]) -> str:
    lines = [f"routing_root: {nav['routing_root']}"]
    default = nav.get("default")
    if not default:
        lines.append("")
        lines.append("No AdaMAST sessions found under this routing root yet.")
        elsewhere = nav.get("elsewhere")
        if elsewhere:
            count = elsewhere["programs"]
            noun = "program exists" if count == 1 else "programs exist"
            lines.append("")
            lines.append(
                f"But {count} {noun} under {elsewhere['routing_root']}."
            )
            lines.append(
                "ADAMAST_HOME decides which root is used, and a host launched "
                "from a desktop app does not inherit your shell environment, so "
                "the two can disagree. Pass that path explicitly, or align "
                "ADAMAST_HOME between your shell and your host."
            )
        else:
            lines.append("Start a Claude Code or Codex session to create one.")
        return "\n".join(lines)
    lines.append("")
    lines.append("default session (auto-targeted):")
    lines.extend(f"  {line}" for line in _render_text(default).splitlines())
    recent = nav.get("recent_sessions") or []
    if recent:
        default_target = default.get("trace_output")
        lines.append("")
        lines.append("recent sessions:")
        for item in recent:
            marker = "*" if item["trace_output"] == default_target else "-"
            monitor_links = (item.get("monitor") or {}).get("links") or []
            url = monitor_links[0]["url"] if monitor_links else "(no live monitor)"
            project = item.get("project_id") or "(unknown project)"
            conversation = item.get("conversation_id") or "(no conversation)"
            live = "live" if item.get("live") else "idle"
            lines.append(f"  {marker} [{live}] {project} / {conversation}: {url}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
