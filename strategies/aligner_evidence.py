# AI-assisted (Claude), exploration code for CS581 project
"""Evidence from several independent aligners: every pair of subset alignments is aligned (columns fixed) by each of
`tools` (opal, mafft = MAFFT --merge, clustal = Clustal Omega profile-profile; graphmods/evidence.py), and each edge
gets w + lam * (mean over the tools of the letter pairs the tool puts in one column, each tool scaled to MAGUS's total
weight). mode=vote instead multiplies w by 1 + lam * (number of tools that put the two columns together). optimize=1
also runs MAGUS's trace optimizer (--graphtraceoptimize true)."""
import numpy as np

FAMILY = "evidence"
GRID = [{"tools": t, "lam": 0.25} for t in ("mafft", "clustal", "opal+mafft", "opal+clustal", "opal+mafft+clustal")] + \
       [{"tools": "opal+mafft+clustal", "lam": 0.5}, {"tools": "opal+mafft+clustal", "mode": "vote", "lam": 0.5}] + \
       [{"tools": t, "lam": 0.25, "optimize": 1} for t in ("mafft", "opal+mafft")]
NEEDS_INPUTS = True  # runs the aligners on the subset alignments


def magus_args(optimize=0, **_):
    return ["--graphtraceoptimize", "true"] if optimize else []


def apply(g, tools, lam, mode="add", optimize=0):
    names = tools.split("+")
    ev = [g.pair_evidence(t)[0] for t in names]
    if mode == "vote":
        return g.w * (1 + lam * sum((e > 0).astype(float) for e in ev))
    scaled = sum(e * g.w.sum() / max(e.sum(), 1) for e in ev) / len(ev)
    return g.w + lam * scaled
