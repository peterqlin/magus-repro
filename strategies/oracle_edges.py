# AI-assisted (Claude), exploration code for CS581 project
"""Ceiling, graph filter: MAGUS's graph with every false edge deleted, using the reference alignment; true edges keep
MAGUS's weight, and MCL and the trace run as in MAGUS. Not a method: it reads the reference.
Two rules for a false edge:
  no f (default)  no residue pair of its two columns shares a reference column (over all sequences)
  f               at most a fraction f of the residue pairs the backbones aligned across it (the pairs MAGUS's weight
                  counts) are aligned in the reference; f = 0.5 is the majority rule. This is the best a filter of the
                  backbone evidence could do."""
import numpy as np

FAMILY = "ceiling"
GRID = [{}] + [{"f": f} for f in (0.25, 0.5, 0.75)]


def apply(g, f=None):
    if f is None:
        return np.where(g.true_pairs > 0, g.w, 0)
    return np.where(g.true_w > f * g.w, g.w, 0)
