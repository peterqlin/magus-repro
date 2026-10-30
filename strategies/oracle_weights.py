# AI-assisted (Claude), exploration code for CS581 project
"""Ceiling, decomposition: MAGUS's edges only (no edges added), reweighted to the residue pairs the reference
aligns (false edges get 0), scaled to MAGUS's total edge weight. Against oracle_edges it measures what correct
weights add over deleting false edges; against oracle_graph, what the missing true edges add. Reads the reference."""
FAMILY = "ceiling"
GRID = [{}]


def apply(g):
    t = g.true_pairs.astype(float)
    return t * (g.w.sum() / max(t.sum(), 1))
