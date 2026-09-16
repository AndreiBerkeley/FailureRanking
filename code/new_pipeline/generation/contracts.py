#!/usr/bin/env python3
"""Stage 0b: extract each agent's contract from the traces. No model calls.

The system messages ARE the instructions, verbatim. Extracting them costs nothing
and gives every later stage the thing a failure is measured against.

Clauses are addressable because bounded-absence evidence cites one: a failure that
IS an absence cannot be quoted, so it names the requirement it did not satisfy.
Splitting is mechanical -- sentence or bullet -- and never paraphrased, so a
clause id always points at text that is really in the prompt.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FIELD = re.compile(r"`([^`]+)`")


def _fields(text: str, start: str, *ends: str) -> list:
    i = text.find(start)
    if i < 0:
        return []
    j = len(text)
    for e in ends:
        k = text.find(e, i + len(start))
        if 0 <= k < j:
            j = k
    return FIELD.findall(text[i + len(start):j])


def _clauses(instructions: str) -> list:
    """Split the instruction body into addressable requirements, verbatim."""
    # The signature block and the interaction template are not requirements --
    # they are the interface. Different programs end them differently, so take
    # the LAST marker present: the body follows all the boilerplate, and falling
    # back to the whole message turns field declarations into clauses. A bounded
    # absence would then cite "1. `passages` (str):" as the requirement it failed.
    MARKERS = ("# Instructions",
               "In adhering to this structure, your objective is:",
               "All interactions will be structured in the following way")
    body, best = instructions, -1
    for marker in MARKERS:
        i = instructions.find(marker)
        if i < 0:
            continue
        end = i + len(marker)
        if marker.startswith("All interactions"):
            # boilerplate: the template block follows it; body starts after the
            # last [[ ## ... ## ]] placeholder
            k = instructions.rfind("]]")
            end = k + 2 if k > end else end
        if end > best:
            best, body = end, instructions[end:]
    if best < 0:
        m = re.search(r"^Component:.*$", instructions, re.M)
        if m:
            body = instructions[m.end():]
    parts = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or set(s) <= set("-=_ "):
            continue
        s = re.sub(r"^[-*•]\s*", "", s)
        # a bullet is one clause; a prose line may hold several sentences
        for piece in re.split(r"(?<=[.!?])\s+(?=[A-Z])", s):
            piece = piece.strip()
            if len(piece) > 15:
                parts.append(piece)
    return [{"id": f"c{n}", "text": t} for n, t in enumerate(parts, 1)]


def agent_name(system_message: str, idx: int, agents: list) -> str:
    """Identity of the agent a system message belongs to: from 'Component:'
    where present, else positionally against the structure's agent list, since
    system messages appear in execution order. One rule, shared by contract
    extraction and trace rendering, so a contract and a rendered turn never
    disagree about who an agent is."""
    m = re.search(r"^Component:\s*(.+)$", system_message, re.M)
    name = m.group(1).strip() if m else (
        agents[idx] if idx < len(agents) else f"agent_{idx}")
    return name.replace(".predict", "")


def _from_messages(msgs: list, agents: list, roles: dict) -> list:
    """Build one contract per agent from a single trace's system messages."""
    seen, out = {}, []
    sysm = [m.get("content") or "" for m in msgs if m.get("role") == "system"]
    for idx, s in enumerate(sysm):
        name = agent_name(s, idx, agents)
        if name in seen:
            continue
        seen[name] = True
        out.append({
            "agent": name,
            "instructions": s,
            "declared_inputs": _fields(s, "Your input fields are:",
                                       "Your output fields are:"),
            "declared_outputs": _fields(s, "Your output fields are:",
                                        "All interactions", "Component:"),
            "clauses": _clauses(s),
        })
    # Role by name where the structure agrees with the traces, else by position:
    # system messages appear in execution order, and so does the agent list.
    for i, c in enumerate(out):
        c["role"] = roles.get(c["agent"])
        if c["role"] is None and i < len(agents):
            c["role"] = roles.get(agents[i])
    return out


def extract_all(corpus: Path, structure: dict) -> dict:
    """One contract set per candidate: {candidate_index: [contracts]}.

    Candidates in an optimised pool carry different instructions for the same
    agent, so there is no single contract for a corpus. The earlier single-set
    extractor took whichever trace sorted first and applied that candidate's
    prompts to every other candidate's traces. A candidate's prompts are fixed
    across its traces, so its first trace is enough.
    """
    agents = list(structure["discovered_agents"]["agents"])
    roles = structure["discovered_agents"].get("agent_to_role") or {}
    out = {}
    for p in sorted(corpus.glob("*.json")):
        d = json.loads(p.read_text())
        ci = (d.get("metadata") or {}).get("candidate_index")
        if ci in out:
            continue
        out[ci] = _from_messages(d.get("messages") or [], agents, roles)
    return out


def extract(corpus: Path, structure: dict) -> list:
    """ONE candidate's contracts: those of the first trace in filename order.
    Only correct for a single-candidate corpus. Use extract_all otherwise."""
    agents = list(structure["discovered_agents"]["agents"])
    roles = structure["discovered_agents"].get("agent_to_role") or {}
    for p in sorted(corpus.glob("*.json")):
        d = json.loads(p.read_text())
        return _from_messages(d.get("messages") or [], agents, roles)
    return []


def _render_one(c: dict, header: str, max_clause_chars: int) -> list:
    lines = [header,
             f"  receives: {c['declared_inputs']}",
             f"  must produce: {c['declared_outputs']}",
             "  requirements it was given:"]
    used = 0
    for cl in c["clauses"]:
        if used + len(cl["text"]) > max_clause_chars:
            lines.append(f"    [... {len(c['clauses'])} clauses total, "
                         "remainder omitted for length ...]")
            break
        lines.append(f"    [{cl['id']}] {cl['text']}")
        used += len(cl["text"])
    lines.append("")
    return lines


def render(contracts: list, max_clause_chars: int = 4000) -> str:
    """One candidate's contracts, for a batch whose traces all belong to it."""
    lines = []
    for c in contracts:
        role = f"   (role: {c['role']})" if c.get("role") else ""
        lines += _render_one(c, f"### agent: {c['agent']}{role}", max_clause_chars)
    return "\n".join(lines)


def render_all(by_cand: dict, max_clause_chars: int = 4000) -> str:
    """Every distinct instruction set per agent, with the candidates that share
    it. For stages that see all candidates at once and must not be told that
    one candidate's rules bound the others."""
    cands = sorted(by_cand, key=lambda k: (k is None, k))
    if not cands:
        return ""
    agents = [c["agent"] for c in by_cand[cands[0]]]
    lines = [f"{len(cands)} candidates. The same agent received DIFFERENT "
             "instructions under different candidates; a requirement binds only "
             "the candidates listed beside it.", ""]
    for pos, agent in enumerate(agents):
        versions = {}   # instructions text -> (contract, [candidates])
        for ci in cands:
            cs = by_cand[ci]
            if pos >= len(cs):
                continue
            c = cs[pos]
            versions.setdefault(c["instructions"], (c, []))[1].append(ci)
        for k, (c, who) in enumerate(versions.values(), 1):
            role = f"   (role: {c['role']})" if c.get("role") else ""
            lines += _render_one(
                c, f"### agent: {agent}{role}  -- version {k} of {len(versions)}, "
                   f"candidates {who}", max_clause_chars)
    return "\n".join(lines)
