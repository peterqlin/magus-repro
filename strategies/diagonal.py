# AI-assisted (Claude), exploration code for CS581 project
"""Diagonal support: a true edge (a, b) between two subsets usually comes with its neighbours (a-1, b-1) and
(a+1, b+1), since aligned stretches run along diagonals. An edge with fewer than m of those two neighbours in the
graph (g.diag_support) gets its weight times factor (0 deletes it)."""
import numpy as np

FAMILY = "structure"
GRID = [{"m": 1, "factor": 0}, {"m": 1, "factor": 0.25}, {"m": 2, "factor": 0.25}, {"m": 2, "factor": 0.5}]


def apply(g, m, factor):
    return np.where(g.diag_support < m, g.w * factor, g.w)
