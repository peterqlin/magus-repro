# AI-assisted (Claude), exploration code for CS581 project
"""Second opinion from OPAL: every pair of subset alignments is aligned with OPAL (profile-profile, PASTA's DNA
merger), and each edge gets the letter pairs OPAL puts in one column (g.opal_pairs, graphmods/evidence.py).
mode=add: w + lam * opal (opal scaled to MAGUS's total weight); mode=filter: edges OPAL does not support get weight
times factor; mode=only: the OPAL weight alone, on MAGUS's edges."""
import numpy as np

FAMILY = "evidence"
GRID = [{"mode": "add", "lam": x} for x in (0.5, 1, 2)] + [{"mode": "filter", "factor": f} for f in (0, 0.25)] + \
       [{"mode": "only"}]
NEEDS_INPUTS = True  # runs OPAL on the subset alignments


def apply(g, mode, lam=1, factor=0):
    o = g.opal_pairs
    if mode == "add":
        return g.w + lam * o * g.w.sum() / max(o.sum(), 1)
    if mode == "filter":
        return np.where(o > 0, g.w, g.w * factor)
    return o
