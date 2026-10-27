# AI-assisted (Claude), exploration code for CS581 project
"""Triadic closure, reweighting: strengthen every existing edge by how strongly it is closed through third columns,
w' = w + L * t_ab * possible pairs (nothing deleted, nothing added)."""
FAMILY = "network"
GRID = [{"L": L} for L in (0.25, 0.5, 1, 2, 4)]


def apply(g, L):
    return g.w + L * g.tc * g.poss
