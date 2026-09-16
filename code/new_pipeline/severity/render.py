"""Condensed trace rendering for the severity rater.

The judge's rendering repeats, in every turn, the instructions (identical for a
given agent across all traces) and the input passages (identical to the retrieval
event immediately above). Neither carries information the rater lacks, so:

  - agent OUTPUTS are kept verbatim -- that is where every finding lives;
  - each agent's instructions are shown once, at the top of the corpus;
  - a turn's input passages are replaced by a pointer to the retrieval event;
  - each retrieved document is cut to title + a snippet;
  - the FINAL OUTPUT (a harness concatenation of every retrieved document) is
    reduced to the list of titles it contains.

Gold never enters: traces are stripped by goldfree before rendering.
"""
import re

SNIP = 120

def _docs(body, snip=None):
    snip = SNIP if snip is None else snip
    out = []
    for ln in body.split("\n"):
        if " | " in ln:
            t, _, s = ln.partition(" | ")
            s = s.strip()
            out.append(f"  {t} | {s[:snip].rstrip()}{'…' if len(s) > snip else ''}")
        elif ln.strip():
            out.append("  " + ln)
    return "\n".join(out)

def condense(txt: str, instructions_seen: dict) -> str:
    """`instructions_seen` accumulates {agent: instruction text} across traces so
    each agent's spec is emitted once by the caller."""
    blocks = re.split(r"(?=\n===== )", "\n" + txt)
    out = []
    hop = 0
    for b in blocks:
        if "RETRIEVAL EVENT" in b:
            hop += 1
            head, _, body = b.partition("documents returned:\n")
            out.append(head + "documents returned:\n" + _docs(body))
        elif "FINAL OUTPUT" in b:
            titles = [ln.split(" | ")[0].strip() for ln in b.split("\n") if " | " in ln]
            out.append(f"\n===== FINAL OUTPUT · harness =====\n[concatenation of every retrieved "
                       f"document; {len(titles)} titles: " + "; ".join(titles) + "]")
        elif re.search(r"===== TURN \d+", b):
            m = re.search(r"===== TURN (\d+) · agent: (\S+)", b)
            agent = m.group(2) if m else "?"
            # instructions: capture once, replace with pointer
            ins = re.search(r"--- instructions given to this agent ---\n(.*?)\n--- input", b, re.S)
            if ins and agent not in instructions_seen:
                instructions_seen[agent] = ins.group(1).strip()
            b = re.sub(r"--- instructions given to this agent ---\n.*?\n(?=--- input)",
                       f"--- instructions: see the {agent} specification at the top ---\n", b, flags=re.S)
            # input: keep claim/context/summaries (short), replace passages with a pointer
            b = re.sub(r"(\[\[ ## passages ## \]\]\n).*?(?=\n\[\[ ## |\n--- output)",
                       lambda mm: mm.group(1) + f"[the documents from the hop-{hop} retrieval event above]",
                       b, flags=re.S)
            out.append(b)
        else:
            out.append(b)
    return "".join(out)
