#!/usr/bin/env python3
"""What the models-1 capture has actually cost so far, and what it is on course to cost.

    python3 data/hover/scripts/models_run_cost.py            # all portions
    python3 data/hover/scripts/models_run_cost.py --budget 35

Money is read from what OpenRouter reported on each call, never from a price list, because a
model can be served by several providers at different rates and because a model reached through
a linked upstream key (BYOK) is billed by that vendor rather than out of the OpenRouter balance.
Both are reported separately. Projection scales each model's spend by the traces it still owes.
Exit status 2 when the projection exceeds --budget, so a watcher can act on it.
"""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INC = REPO / "data" / "hover" / "traces" / "_incoming"
PORTIONS = ("taxonomy", "judging", "generalization")


def scan(run: Path):
    """-> {model: {'traces','calls','or_cost','upstream','byok','errors'}} for one portion."""
    cm = json.loads((run / "candidate_map.json").read_text())
    per = {}
    for c in cm["candidates"]:
        d = run / "raw" / "evaluation" / "traces" / f"candidate_{c['candidate_index']:03d}"
        s = {"model": c["solver_model"], "reasoning": c.get("reasoning"), "traces": 0, "calls": 0,
             "or_cost": 0.0, "upstream": 0.0, "byok": False, "errors": 0, "in": 0, "out": 0}
        for f in sorted(d.glob("*.json")) if d.exists() else []:
            t = json.loads(f.read_text()); s["traces"] += 1; s["errors"] += t.get("status") != "ok"
            for call in t.get("lm_calls") or []:
                u = (call.get("response") or {}).get("usage") or call.get("usage") or {}
                s["calls"] += 1; s["or_cost"] += float(u.get("cost") or 0)
                s["upstream"] += float((u.get("cost_details") or {}).get("upstream_inference_cost") or 0)
                s["byok"] = s["byok"] or bool(u.get("is_byok"))
                s["in"] += int(u.get("prompt_tokens") or 0); s["out"] += int(u.get("completion_tokens") or 0)
        per[c["pool_candidate_id"]] = s
    return per, len(json.loads((REPO / "data" / "hover" / "splits" / cm["candidate_set"] / "split.json").read_text())["portions"][run.name.split("-", 2)[-1]])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--budget", type=float, default=None, help="exit 2 if the projected total exceeds this")
    ap.add_argument("--quiet", action="store_true"); a = ap.parse_args()
    # Per-model cost per trace, from anywhere it has been measured, so that a (model, portion)
    # pair that has not started yet still contributes to the projection. Without this the
    # headline creeps up from near zero as models begin, which is useless as an early warning.
    # Only directories captured under the run's own settings count. The first smoke ran with each
    # model's default reasoning, which cost deepseek and qwen three to four times what they cost
    # with it off, so averaging it in overstated the projection by a third. Real run first, the
    # reasoning-off check as the fallback for models it has not reached yet.
    rate = {}
    for d in sorted(INC.glob("models-1-*"), key=lambda x: "check" in x.name):
        if "smoke" in d.name: continue
        if not (d / "candidate_map.json").exists(): continue
        for c in json.loads((d / "candidate_map.json").read_text())["candidates"]:
            td = d / "raw" / "evaluation" / "traces" / f"candidate_{c['candidate_index']:03d}"
            n = up = 0.0
            for f in sorted(td.glob("*.json")) if td.exists() else []:
                t = json.loads(f.read_text())
                if t.get("status") != "ok": continue
                n += 1
                for call in t.get("lm_calls") or []:
                    u = (call.get("response") or {}).get("usage") or {}
                    up += float((u.get("cost_details") or {}).get("upstream_inference_cost") or 0)
            if n: rate.setdefault(c["solver_model"], []).append((n, up, "check" not in d.name))
    # a model measured on the real run uses that; the check is used only until then
    rate = {m: (lambda real: sum(u for _, u, _ in real) / sum(n for n, _, _ in real))([x for x in v if x[2]] or v)
            for m, v in rate.items()}
    tot = defaultdict(float); done = expect = 0; rows = []
    for p in PORTIONS:
        run = INC / f"models-1-{p}"
        if not (run / "candidate_map.json").exists(): continue
        per, n_tasks = scan(run)
        for alias, s in sorted(per.items()):
            done += s["traces"]; expect += n_tasks
            proj_or = s["or_cost"] / s["traces"] * n_tasks if s["traces"] else 0
            proj_up = s["upstream"] / s["traces"] * n_tasks if s["traces"] else 0
            tot["or"] += s["or_cost"]; tot["up"] += s["upstream"]; tot["proj_or"] += proj_or; tot["proj_up"] += proj_up
            rows.append((p, alias, s, n_tasks, proj_or, proj_up))
    if not rows: print("no models-1 capture directories yet"); return 0
    if not a.quiet:
        print(f"{'portion':15s} {'model':30s} {'reas':>7s} {'traces':>11s} {'err':>4s} {'OR $':>8s} {'upstream $':>10s} {'proj OR':>8s} {'proj up':>8s}")
        for p, alias, s, n, po, pu in rows:
            flag = " BYOK" if s["byok"] else ""
            print(f"{p:15s} {s['model'][:30]:30s} {str(s['reasoning'])[:7]:>7s} {s['traces']:5d}/{n:<5d} {s['errors']:4d} {s['or_cost']:8.4f} {s['upstream']:10.4f} {po:8.2f} {pu:8.2f}{flag}")
    # the whole run, including (model, portion) pairs not yet begun
    split = json.loads((REPO / "data" / "hover" / "splits" / "models-1" / "split.json").read_text())["portions"]
    setj = json.loads((REPO / "data" / "hover" / "candidates" / "sets" / "models-1.json").read_text())
    models = list(setj["solver_models"].values()); n_all = sum(len(v) for v in split.values())
    unmeasured = [m for m in models if m not in rate]
    full = sum(rate.get(m, 0.0) * n_all for m in models)
    proj_total = max(full, tot["proj_up"])
    print(f"\ntraces {done:,}/{expect:,} ({done / expect:.0%} of the run)" if expect else "")
    print(f"spent so far: OpenRouter balance ${tot['or']:.2f}; total real cost ${tot['up']:.2f} (the difference is billed by the upstream vendor via a linked key)")
    print(f"projected for the whole run (10 models x {n_all:,} tasks): ${proj_total:.2f} real cost"
          + (f"; {len(unmeasured)} model(s) not yet measured, excluded" if unmeasured else "")
          + f"; of which OpenRouter balance ${sum(0 if 'claude' in m else rate.get(m, 0.0) * n_all for m in models):.2f}")
    if a.budget is not None and proj_total > a.budget:
        print(f"OVER BUDGET: projected ${proj_total:.2f} exceeds ${a.budget:.2f}"); return 2
    if a.budget is not None: print(f"within budget (${a.budget:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
