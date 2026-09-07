"""Render a trace as explicitly delineated agent turns.

A reader asked to account for every turn needs to see, without ambiguity, where
one agent's turn ends and the next begins, and for each turn: which agent it
was, the instructions that agent had, what it received, and what it produced.
The flat `--- role ---` rendering left all of that implicit, and the reader
confounded one agent's instructions with another's.

A turn is opened by a system message (the agent's instructions), takes the user
message(s) that follow as its input, and is closed by the assistant message
that is its output. Messages outside any turn are the environment: the task
statement, retrieval events, or an output assembled by the harness.
"""
from __future__ import annotations

import json

from new_pipeline.generation.contracts import agent_name

TURN_OPEN = "===== TURN {k} · agent: {agent} ====="
TURN_CLOSE = "===== end of turn {k} ====="
INSTR = "--- instructions given to this agent ---"
INPUT = "--- input this agent received ---"
OUTPUT = "--- output this agent produced ---"
ENV = "===== ENVIRONMENT · not an agent turn ====="
HARNESS = ("===== OUTPUT WITHOUT PRECEDING INSTRUCTIONS · produced by the "
           "harness, or by an agent whose instructions were not recorded; "
           "not an agent turn =====")

FORMAT_NOTE = f"""Each trace is a sequence of blocks. `{ENV}` blocks are the
task statement, tool or retrieval results, and other material produced by the
environment rather than by an agent. Each agent turn is enclosed in
`===== TURN k · agent: NAME =====` ... `===== end of turn k =====` and holds three
sections: `{INSTR}` (that agent's own instructions), `{INPUT}` (what it was
handed), `{OUTPUT}` (what it produced). A `{HARNESS[:40]}...` block is an output
assembled by the harness and is not a turn."""


def _text(content) -> str:
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


def render_turns(trace: dict, agents: list | None = None) -> tuple[str, list]:
    """Return (rendered text, turns) where turns = [{"turn": k, "agent": name,
    "block": <that turn's rendered block>}]. The block is what a per-turn call
    is shown: the agent's instructions, its input, its output, nothing else,
    because by the contract rule nothing else bears on that turn."""
    agents = list(agents or [])
    parts, turns = [], []
    k, sys_idx = 0, 0
    open_turn = None

    def flush(output: str | None):
        nonlocal open_turn
        t = open_turn
        block = "\n".join([
            TURN_OPEN.format(k=t["turn"], agent=t["agent"]),
            INSTR, t["instr"],
            INPUT, "\n\n".join(t["inputs"]) if t["inputs"] else "(nothing recorded)",
            OUTPUT, output if output is not None else "(no output recorded)",
            TURN_CLOSE.format(k=t["turn"]),
        ])
        parts.append(block)
        turns.append({"turn": t["turn"], "agent": t["agent"], "block": block})
        open_turn = None

    for m in trace.get("messages") or []:
        role, content = m.get("role"), _text(m.get("content"))
        if role == "system":
            if open_turn is not None:
                flush(None)
            k += 1
            open_turn = {"turn": k, "agent": agent_name(content, sys_idx, agents),
                         "instr": content, "inputs": []}
            sys_idx += 1
        elif role == "assistant":
            if open_turn is not None:
                flush(content)
            else:
                parts.append(f"{HARNESS}\n{content}")
        else:
            if open_turn is not None:
                open_turn["inputs"].append(content)
            else:
                parts.append(f"{ENV}\n{content}")
    if open_turn is not None:
        flush(None)
    return "\n\n".join(parts), turns
