# AI-assisted (Claude), exploration code for CS581 project
"""Order consistency: a merge keeps each subset's column order, so the true edges between two subsets never cross.
Per pair of subsets, the heaviest non-crossing chain of edges with k >= 2 is found (weighted longest increasing
subsequence); an edge more than d columns from that chain (g.chain_offset, interpolated between chain points) gets
its weight times factor (0 deletes it)."""
import numpy as np

FAMILY = "structure"
GRID = [{"d": d, "factor": f} for d in (1, 2, 4, 8) for f in (0, 0.25)]


def apply(g, d, factor):
    return np.where(g.chain_offset > d, g.w * factor, g.w)
