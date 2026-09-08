#!/usr/bin/env python3
"""Deterministic core of the FALAT-derived recovery instrument (SPEC.md).

Input: Stage-1 failure-point occurrences + LLM-asserted typed edges.
Output: per-occurrence recovery verdict (persisted / recovered), causal
position, and sigma — all pure graph computation; no model calls.

Objects
-------
occurrence: {"id": str, "step": int}
edge:       {"src": id, "dst": id | "OUTPUT", "label": one of LABELS,
             "consume_step": int}   # step at which dst consumed src's
                                    # output; defaults to dst's step
                                    # (OUTPUT: infinity)

Rules (SPEC.md "Deterministic recovery rules")
----------------------------------------------
- follow_up / error_shift propagate influence; redundancy, no_influence,
  dead_end do not; correction marks src as fixed at consume_step.
- An influence edge (a->b) is LIVE iff a has no correction consumed at a
  step strictly before b consumed a's output
  (corrected_at(a) is None or corrected_at(a) >= consume_step(a->b)).
- PERSISTED iff a live influence path reaches OUTPUT; else RECOVERED.
- Occurrences with no outgoing edges at all fall back to
  default_when_unlinked ("persisted" = conservative default).
- Positions and sigma = l/(r+l) are computed on the live influence
  subgraph among persisted occurrences (PARKING.md 2026-08-07 package);
  diagnostics only — NOT consumed by Phi v0.1.
"""

import math

OUTPUT = "OUTPUT"
LABELS = {"follow_up", "redundancy", "no_influence", "error_shift",
          "correction", "dead_end"}
INFLUENCE = {"follow_up", "error_shift"}


def _validate(occurrences, edges, on_step_violation="raise"):
    """`on_step_violation`:
    'raise'      — a backward edge is an error (original strict behaviour).
    'trust_edge' — the model's asserted direction wins over our step
                   anchors. A backward edge almost always means the two
                   occurrences' step anchors were assigned in the wrong
                   order, not that causality runs backwards; dropping
                   such edges severs chains and silently converts
                   propagating failures into "recoveries".
    """
    steps = {o["id"]: o["step"] for o in occurrences}
    if len(steps) != len(occurrences):
        raise ValueError("duplicate occurrence ids")
    for e in edges:
        if e["label"] not in LABELS:
            raise ValueError(f"unknown label {e['label']!r}")
        if e["src"] not in steps:
            raise ValueError(f"edge src {e['src']!r} is not an occurrence")
        if e["dst"] != OUTPUT:
            if e["dst"] not in steps:
                raise ValueError(f"edge dst {e['dst']!r} is not an occurrence")
            if steps[e["src"]] >= steps[e["dst"]] and on_step_violation == "raise":
                raise ValueError(
                    f"edge {e['src']}->{e['dst']} violates step ordering")
    return steps


def _consume_step(edge, steps):
    if "consume_step" in edge and edge["consume_step"] is not None:
        return edge["consume_step"]
    return math.inf if edge["dst"] == OUTPUT else steps[edge["dst"]]


def analyze(occurrences, edges, default_when_unlinked="persisted",
            on_step_violation="raise"):
    """Return {occurrence_id: {"status", "position", "sigma"}} plus a
    summary dict under the key "_summary"."""
    steps = _validate(occurrences, edges, on_step_violation)

    corrected_at = {}
    for e in edges:
        if e["label"] == "correction":
            s = _consume_step(e, steps)
            prev = corrected_at.get(e["src"])
            corrected_at[e["src"]] = s if prev is None else min(prev, s)

    def live(e):
        if e["label"] not in INFLUENCE:
            return False
        c = corrected_at.get(e["src"])
        return c is None or c >= _consume_step(e, steps)

    out_edges = {o["id"]: [] for o in occurrences}
    has_any_edge = {o["id"]: False for o in occurrences}
    for e in edges:
        has_any_edge[e["src"]] = True
        if live(e):
            out_edges[e["src"]].append(e["dst"])

    # persisted iff a live influence path reaches OUTPUT.
    # Trusting model-asserted direction allows cycles, so the traversal
    # must be cycle-safe: a node currently on the stack contributes
    # nothing (its own resolution is still pending) rather than looping.
    memo = {}
    on_stack = set()

    def reaches_output(u):
        if u == OUTPUT:
            return True
        if u in memo:
            return memo[u]
        if u in on_stack:
            return False
        on_stack.add(u)
        result = any(reaches_output(v) for v in out_edges[u])
        on_stack.discard(u)
        memo[u] = result
        return result

    results = {}
    for o in occurrences:
        oid = o["id"]
        if not has_any_edge[oid]:
            status = default_when_unlinked
        else:
            status = "persisted" if reaches_output(oid) else "recovered"
        results[oid] = {"status": status, "position": None, "sigma": None}

    # positions + sigma among persisted occurrences (live influence edges
    # between persisted occurrences only; edges to OUTPUT excluded)
    persisted = {i for i, r in results.items() if r["status"] == "persisted"}
    succ = {i: [] for i in persisted}
    pred = {i: [] for i in persisted}
    for e in edges:
        if (live(e) and e["src"] in persisted and e["dst"] != OUTPUT
                and e["dst"] in persisted):
            succ[e["src"]].append(e["dst"])
            pred[e["dst"]].append(e["src"])

    def depth(node, nbrs, best, seen=None):
        # longest/shortest path to a node with no neighbours; cycle-safe
        # because trusted model edges are not guaranteed acyclic
        seen = set() if seen is None else seen
        if not nbrs[node] or node in seen:
            return 0
        seen = seen | {node}
        vals = [1 + depth(n, nbrs, best, seen) for n in nbrs[node]
                if n not in seen]
        return best(vals) if vals else 0

    for i in persisted:
        is_root, is_leaf = not pred[i], not succ[i]
        if is_root and is_leaf:
            pos, sigma = "isolated", 1.0
        elif is_root:
            pos, sigma = "root", 1.0
        elif is_leaf:
            pos, sigma = "leaf", 0.0
        else:
            r = depth(i, pred, min)   # nearest root
            l = depth(i, succ, max)   # farthest leaf
            pos, sigma = "middle", l / (r + l)
        results[i].update(position=pos, sigma=sigma)

    results["_summary"] = {
        "persisted": len(persisted),
        "recovered": sum(1 for i, r in results.items()
                         if i != "_summary" and r["status"] == "recovered"),
        "unlinked": sum(1 for i, ok in has_any_edge.items() if not ok),
    }
    return results


def task_mode_recovery(occurrence_modes, results):
    """Per-mode full-recovery flags for one task.

    occurrence_modes: {occurrence_id: mode}. Returns {mode: status} with
    status in {"fully_recovered", "unrecovered"} — every occurrence of
    the mode must be recovered (v0 strict semantics)."""
    modes = {}
    for oid, mode in occurrence_modes.items():
        ok = results[oid]["status"] == "recovered"
        modes[mode] = modes.get(mode, True) and ok
    return {m: ("fully_recovered" if ok else "unrecovered")
            for m, ok in modes.items()}
