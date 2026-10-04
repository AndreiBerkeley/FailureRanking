"""The few helpers recovery uses from elsewhere in FailureRank's new_pipeline, copied verbatim so this

folder runs on its own: agent_name (generation/contracts.py), TURN_LAYOUT, PROGRAM_RULE and program_block

(pointjudge/prompts.py), counts_from_points (pointjudge/judge.py), salvage (generation/run.py)."""
from __future__ import annotations

import json
import re

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

TURN_LAYOUT = """## HOW THE TRACE IS LAID OUT

The trace is a sequence of blocks. Blocks headed
`===== ENVIRONMENT · not an agent turn =====` are the task statement, tool or
retrieval results, and other material produced by the environment. Each agent
turn is enclosed in `===== TURN k · agent: NAME =====` ... `===== end of turn k
=====` and holds `--- instructions given to this agent ---`, `--- input this
agent received ---`, and `--- output this agent produced ---`. A block headed
`===== OUTPUT WITHOUT PRECEDING INSTRUCTIONS ... =====` was assembled by the
harness and is not a turn. A turn is judged against its own instructions and
its own input; a mistake already present in a turn's input belongs to the
earlier turn that produced it. The instructions section declares the agent's
input and output fields as well as its task; producing a declared output field
(such as a `reasoning` field listed under "Your output fields") is required,
not a deviation, even when a later sentence names only some of the fields. The
`[[ ## name ## ]]` markers that open each output field are likewise the
harness's own output format, declared in the same instructions section and
needed to parse the output; using them, rather than a plainer layout described
elsewhere in the instructions (`reasoning: ...`, `**query**: ...`), is required,
not a deviation, and is never a failure."""

PROGRAM_RULE = """## HOW THIS PROGRAM'S OUTPUT IS SCORED

{rule}

Judge each step's work against this. A step has obtained something only when what
the output is scored on came back; material that is merely about it does not count."""

def program_block(structure) -> str:
    """The program's success rule as one prompt section, from `success_rule` in the
    benchmark's structure.json; empty when the structure declares none. It is a fact
    about how the program is scored, not an outcome, so every pass may see it: without
    it a reader judges 'what was needed' by its own reading of the task."""
    rule = ((structure or {}).get("success_rule") or "").strip()
    return PROGRAM_RULE.format(rule=rule) if rule else ""

def counts_from_points(points) -> dict:
    """The scoring surface: {code: distinct steps at which it was found}.

    One occurrence per distinct step, the same count rule the panel judge states
    to its annotators, so a count from this judge and a count from that one mean
    the same thing. Two points on one step carrying the same code are one
    occurrence of that code at that step; the two points survive separately in
    `points`, where anything that wants them can read them."""
    seen = {}
    for p in points:
        for c in p.get("codes") or []:
            seen.setdefault(c, set()).add(p["turn"])
    return {c: len(t) for c, t in sorted(seen.items())}


def salvage(raw: str):
    """Parse a response that embeds verbatim trace text, tolerating the two ways
    that reliably breaks.

    A reader asked to quote exact spans must put arbitrary characters inside JSON
    strings. Trace text carries backslashes (mathematical notation especially),
    which arrive as invalid escapes; and a long quote can leave the response cut
    off mid-string. Both cost the whole batch under a strict parse, when most of
    the findings in it are intact and recoverable.

    Salvage never invents content. It repairs escaping, and it truncates to the
    last complete entry -- so what is returned is a prefix of what was said, and
    the shortfall is visible to the coverage check downstream.
    """
    import re
    try:
        return json.loads(raw), None
    except Exception as first:
        pass
    fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw)   # lone backslash -> escaped
    try:
        return json.loads(fixed), "repaired invalid escapes"
    except Exception:
        pass
    # cut back to the last complete trace object and close the structure
    for cut in range(len(fixed), 0, -1):
        if fixed[cut - 1] != "}":
            continue
        for tail in ("]}", "}]}", "}]}]}"):
            try:
                d = json.loads(fixed[:cut] + tail)
                if isinstance(d, dict) and d.get("traces"):
                    return d, f"truncated response salvaged at {cut}/{len(raw)} chars"
            except Exception:
                continue
    return None, None
