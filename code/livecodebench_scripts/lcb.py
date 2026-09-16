"""LiveCodeBench: load problems, build the prompt, score a generation.

    python3 lcb.py stats                       # count problems per release / difficulty
    python3 lcb.py show <question_id>          # print one problem's prompt
    python3 lcb.py score <question_id> <file>  # run one generation against the tests

Uses the upstream runner (evaluator/upstream, MIT) for execution; must run under
evaluator/.venv/bin/python, which has its dependencies.
"""
import base64, json, pickle, sys, zlib, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "tasks" / "raw"
UP = ROOT / "evaluator" / "upstream"
sys.path.insert(0, str(UP))

RELEASES = {"v1": ["test.jsonl"], "v2": ["test2.jsonl"], "v3": ["test3.jsonl"],
            "v4": ["test4.jsonl"], "v5": ["test5.jsonl"], "v6": ["test6.jsonl"]}

SYSTEM = ("You are an expert Python programmer. You will be given a question (problem "
          "specification) and will generate a correct Python program that matches the "
          "specification and passes all tests.")
FMT_STARTER = ("You will use the following starter code to write the solution to the "
               "problem and enclose your code within delimiters.")
FMT_STDIN = ("Read the inputs from stdin solve the problem and write the answer to stdout "
             "(do not directly test on the sample inputs). Enclose your code within delimiters "
             "as follows. Ensure that when the python program runs, it reads the inputs, runs "
             "the algorithm and writes output to STDOUT.")


def iter_problems(files=None):
    for f in files or [x for v in RELEASES.values() for x in v]:
        p = RAW / f
        if not p.exists():
            continue
        with open(p) as fh:
            for line in fh:
                if line.strip():
                    d = json.loads(line); d["_file"] = f; yield d


def load_problem(qid):
    for d in iter_problems():
        if d["question_id"] == qid:
            return d
    raise KeyError(qid)


def tests_of(d):
    pub = json.loads(d["public_test_cases"])
    try:
        priv = json.loads(d["private_test_cases"])
    except Exception:
        priv = json.loads(pickle.loads(zlib.decompress(base64.b64decode(d["private_test_cases"].encode()))))
    return pub, priv


def user_prompt(d):
    s = f"### Question:\n{d['question_content']}\n\n"
    if d.get("starter_code"):
        s += f"### Format: {FMT_STARTER}\n```python\n{d['starter_code']}\n```\n\n"
    else:
        s += f"### Format: {FMT_STDIN}\n```python\n# YOUR CODE HERE\n```\n\n"
    return s + "### Answer: (use the provided format with backticks)\n\n"


def extract_code(text):
    m = re.search(r"```python\n(.*?)```", text, re.S) or re.search(r"```\n(.*?)```", text, re.S)
    return m.group(1) if m else text


def sample_for_runner(d):
    """The dict shape upstream's run_test expects."""
    pub, priv = tests_of(d)
    tests = pub + priv
    meta = json.loads(d.get("metadata") or "{}")
    io = {"inputs": [t["input"] for t in tests], "outputs": [t["output"] for t in tests]}
    if meta.get("func_name"):
        io["fn_name"] = meta["func_name"]
    return {"input_output": json.dumps(io)}, len(pub), len(priv)


def score(d, code, timeout=6):
    """Gold is `all_pass`. The upstream runner stops at the FIRST failing test, so on a
    failure `total` and `per_test` cover only the tests that ran, not every test the
    problem has -- `passed / total` is NOT a graded pass fraction."""
    from lcb_runner.evaluation.compute_code_generation_metrics import check_correctness
    sample, npub, npriv = sample_for_runner(d)
    try:
        res, meta = check_correctness(sample, code, timeout, debug=False)
    except IndexError:
        # upstream: when the child is killed (global timeout, or the OS kills it for
        # memory -- e.g. set(permutations(S)) at N=13) `result` gets a fallback but
        # `metadata_list` stays empty and `metadata_list[0]` raises. Every test failed.
        res = [-1] * (npub + npriv); meta = {"error": "child killed: global timeout or out of memory"}
    passed = sum(1 for r in res if r is True or r == 1)
    return {"passed": passed, "total": len(res), "all_pass": passed == len(res),
            "public": npub, "private": npriv, "per_test": [bool(r is True or r == 1) for r in res],
            "error": (meta or {}).get("error_message") or (meta or {}).get("error")}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        from collections import Counter
        c = Counter(); ids = set()
        for d in iter_problems():
            if d["question_id"] in ids: continue
            ids.add(d["question_id"]); c[(d["_file"], d["difficulty"], d["platform"])] += 1
        byf = Counter(); byd = Counter(); byp = Counter()
        for (f, dif, plat), n in c.items(): byf[f] += n; byd[dif] += n; byp[plat] += n
        print("unique problems:", len(ids))
        print("by file      :", dict(sorted(byf.items())))
        print("by difficulty:", dict(byd))
        print("by platform  :", dict(byp))
    elif cmd == "show":
        d = load_problem(sys.argv[2]); print("SYSTEM:", SYSTEM, "\n"); print(user_prompt(d))
    elif cmd == "score":
        d = load_problem(sys.argv[2]); code = extract_code(open(sys.argv[3]).read())
        print(json.dumps(score(d, code), indent=2))
