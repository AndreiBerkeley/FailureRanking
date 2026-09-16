"""judging-100-1: the pools-1/judging tasks not in judging-50-1 (set difference, no draw).
Built 2026-09-16 by the inline script recorded in the session; this file reproduces it."""
import json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
m = json.load(open(ROOT / "splits/pools-1/split.json"))["portions"]["judging"]
s50 = set(json.load(open(ROOT / "splits/judging-50-1/split.json"))["portions"]["judging"])
rest = sorted(t for t in m if t not in s50)
assert len(rest) == 100 and not (set(rest) & s50)
have = json.load(open(ROOT / "splits/judging-100-1/split.json"))["portions"]["judging"]
assert have == rest, "judging-100-1 on disk is not the set difference"
print("judging-100-1 reproduces:", len(rest))
