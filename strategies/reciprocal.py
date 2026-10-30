# AI-assisted (Claude), exploration code for CS581 project
"""Reciprocal best partners: a column aligns with at most one column of any other subset, so an edge that is much
lighter than its endpoint's heaviest edge into the same subset is suspect. With ra, rb = w over the heaviest edge
from a into b's subset and from b into a's subset (g.best_ratio), an edge is kept when both ratios are >= t
(side=both) or either is (side=either); others get weight times factor."""
import numpy as np

FAMILY = "network"
GRID = [{"t": t, "side": "both", "factor": 0} for t in (1, 0.75, 0.5, 0.25, 0.1)] + \
       [{"t": t, "side": "either", "factor": 0} for t in (0.5, 0.25)] + [{"t": 0.5, "side": "both", "factor": 0.25}]


def apply(g, t, side, factor):
    ra, rb = g.best_ratio
    ok = (ra >= t) & (rb >= t) if side == "both" else (ra >= t) | (rb >= t)
    return np.where(ok, g.w, g.w * factor)
