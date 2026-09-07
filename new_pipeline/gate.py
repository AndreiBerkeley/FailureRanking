#!/usr/bin/env python3
"""Interannotation gate: can independent readers apply the taxonomy alike?

    python -m new_pipeline.gate --taxonomy <tax.json> --corpus <dir> --structure <f> --out <dir> [--readers 4]

Runs the measurement judge over the gate corpus with N independent readers
(resumable; the judge does the calling), then measures agreement from what the
readers wrote down, with no deliberation anywhere:

  kappa      Fleiss' kappa over subjects = (trace, code) pairs, each rated
             present/absent by every reader. Reported per code (subjects =
             traces) and pooled over every pair.
  coverage   the share of the open reader's problems that a code fits well
             (the judge's own "covered" verdict), i.e. 1 - unmapped/problems.

A taxonomy passes when pooled kappa >= --kappa-target and coverage >=
--coverage-floor. The gate corpus is never shown to the refiner; that is what
makes the measurement a certification rather than a fit.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from new_pipeline.llm import log  # noqa: E402


def fleiss_kappa(ratings):
    """ratings: list of (n_yes, n_no) per subject, every subject rated by the same
    number of readers. Two categories: present / absent."""
    ratings = [(a, b) for a, b in ratings if a + b > 0]
    if not ratings: return None
    n = ratings[0][0] + ratings[0][1]
    if any(a + b != n for a, b in ratings) or n < 2: return None
    N = len(ratings)
    p_yes = sum(a for a, _ in ratings) / (N * n); p_no = 1 - p_yes
    P_e = p_yes ** 2 + p_no ** 2
    P_bar = sum((a * (a - 1) + b * (b - 1)) / (n * (n - 1)) for a, b in ratings) / N
    return 1.0 if P_e == 1.0 else (P_bar - P_e) / (1 - P_e)


def measure(judge_out: Path, code_ids: list[str]) -> dict:
    """Agreement and coverage from a finished judge run's per-trace records."""
    per_code = defaultdict(list); pooled = []; problems = covered = 0; readers = None; traces = 0; exercised = set(); silent = 0
    for f in sorted((judge_out / "traces").glob("*.json")):
        t = json.loads(f.read_text())
        if t.get("status") != "judged": continue
        ann = (t.get("panel") or {}).get("annotators") or []
        if readers is None: readers = len(ann)
        if len(ann) != readers or readers < 2: continue
        traces += 1
        if not t.get("codes"): silent += 1
        for c in code_ids:
            yes = sum(1 for a in ann if (a or {}).get(c, 0) > 0)
            if yes: exercised.add(c)
            per_code[c].append((yes, readers - yes)); pooled.append((yes, readers - yes))
        o = t.get("open") or {}
        problems += len(o.get("problems") or [])
        covered += sum(1 for d in (o.get("details") or []) if d.get("verdict") == "covered")
    k_pooled = fleiss_kappa(pooled)
    k_codes = {c: fleiss_kappa(v) for c, v in per_code.items() if c in exercised}
    # pooled over exercised codes only: a code nobody ever assigned reads as perfect agreement on absence and inflates the number
    k_exercised = fleiss_kappa([r for c in exercised for r in per_code[c]])
    return {"traces": traces, "readers": readers, "silent_traces": silent,
            "kappa_pooled_all_codes": k_pooled, "kappa_pooled_exercised_codes": k_exercised,
            "kappa_per_code": k_codes, "codes_exercised": sorted(exercised), "codes_never_assigned": sorted(set(code_ids) - exercised),
            "open_reader_problems": problems, "open_reader_covered": covered,
            "coverage": (covered / problems) if problems else None}


def run(taxonomy: Path, corpus: Path, structure: Path, out: Path, model: str, readers: int, kappa_target: float, coverage_floor: float,
        open_model: str | None = None, traces_per_call: int = 5, thinking: str | None = "HIGH", dry_run: bool = False, extra: list | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    tax = json.loads(taxonomy.read_text()); ids = [c["id"] for c in tax["codes"]]
    cmd = [sys.executable, "-m", "new_pipeline.judge.run", "--taxonomy", str(taxonomy), "--traces", str(corpus), "--out", str(out / "judge"),
           "--structure", str(structure), "--model", model, "--annotators", str(readers), "--threshold", str(max(2, readers // 2)),
           "--traces-per-call", str(traces_per_call)] + (["--open-model", open_model] if open_model else []) + (["--thinking", thinking] if thinking else []) + (extra or [])
    (out / "judge_command.txt").write_text(" ".join(cmd) + "\n")
    if dry_run:
        log(f"gate: dry run; would judge {len(list(corpus.glob('*.json')))} traces with {readers} readers"); return {"dry_run": True, "command": cmd}
    if not (out / "judge" / "summary.json").exists() or json.loads((out / "judge" / "summary.json").read_text())["counts"].get("failed"):
        log(f"gate: judging {corpus.name} with {readers} readers"); subprocess.run(cmd, check=True, cwd=str(REPO))
    m = measure(out / "judge", ids)
    k = m["kappa_pooled_exercised_codes"]; cov = m["coverage"]
    m.update({"kappa_target": kappa_target, "coverage_floor": coverage_floor,
              "passed": bool(k is not None and cov is not None and k >= kappa_target and cov >= coverage_floor),
              "taxonomy": str(taxonomy), "codes": len(ids), "measured_at": time.strftime("%Y-%m-%d %H:%M:%S")})
    (out / "gate.json").write_text(json.dumps(m, indent=2))
    log(f"gate: kappa {k if k is None else round(k, 3)} (target {kappa_target}), coverage {cov if cov is None else round(cov, 3)} (floor {coverage_floor}) -> {'PASS' if m['passed'] else 'FAIL'}")
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taxonomy", type=Path, required=True); ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--structure", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="gemini-3.6-flash"); ap.add_argument("--open-model", default=None)
    ap.add_argument("--readers", type=int, default=4); ap.add_argument("--kappa-target", type=float, default=0.75)
    ap.add_argument("--coverage-floor", type=float, default=0.70); ap.add_argument("--traces-per-call", type=int, default=5)
    ap.add_argument("--thinking", default="HIGH"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--measure-only", type=Path, default=None, help="skip judging; measure an existing judge output directory")
    a = ap.parse_args()
    if a.measure_only:
        tax = json.loads(a.taxonomy.read_text()); m = measure(a.measure_only, [c["id"] for c in tax["codes"]]); print(json.dumps(m, indent=2)); return
    run(a.taxonomy, a.corpus, a.structure, a.out, a.model, a.readers, a.kappa_target, a.coverage_floor, a.open_model, a.traces_per_call, a.thinking, a.dry_run)


if __name__ == "__main__":
    main()
