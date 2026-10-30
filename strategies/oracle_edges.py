# AI-assisted (Claude), exploration code for CS581 project
"""Ceiling, graph filter: MAGUS's graph with every false edge deleted, using the reference alignment (an edge is
false when no residue pair of its two columns shares a reference column). The best any edge filter could do on
this graph; MCL and the trace run as in MAGUS. Not a method: it reads the reference."""
import numpy as np

FAMILY = "ceiling"
GRID = [{}]


def apply(g):
    return np.where(g.true_pairs > 0, g.w, 0)
