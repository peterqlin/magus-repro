# AI-assisted (Claude), exploration code for CS581 project
"""Second opinion from OPAL: every pair of subset alignments is aligned with OPAL (profile-profile, PASTA's DNA
merger), and each edge gets the letter pairs OPAL puts in one column (g.opal_pairs, graphmods/evidence.py).
mode=add: w + lam * opal (opal scaled to MAGUS's total weight); mode=filter: edges OPAL does not support get weight
times factor; mode=only: the OPAL weight alone. With missing=1, the column pairs OPAL aligns that MAGUS has no edge
for are added too (mode=only, missing=1 is a graph from OPAL alone, backbones unused)."""
import numpy as np

FAMILY = "evidence"
GRID = [{"mode": "add", "lam": x} for x in (0.25, 0.5, 1, 2, 4)] + [{"mode": "add", "lam": 1, "missing": 1}] + \
       [{"mode": "filter", "factor": f} for f in (0, 0.25)] + [{"mode": "only"}, {"mode": "only", "missing": 1}]
NEEDS_INPUTS = True  # runs OPAL on the subset alignments


def apply(g, mode, lam=1, factor=0, missing=0):
    o = g.opal_pairs
    ma, mb, mw = g.opal_missing() if missing else (None, None, None)
    if mode == "add":
        scale = lam * g.w.sum() / max(o.sum(), 1)
        w = g.w + scale * o
    elif mode == "filter":
        return np.where(o > 0, g.w, g.w * factor)
    else:
        scale = g.w.sum() / max(o.sum(), 1)  # keeps MAGUS's total weight, so the self loops keep their share
        w = o * scale
    return (w, (ma, mb, mw * scale)) if missing else w
