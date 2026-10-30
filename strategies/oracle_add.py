# AI-assisted (Claude), exploration code for CS581 project
"""Ceiling, decomposition: MAGUS's graph unchanged (false edges kept) plus every true column pair it has no edge
for, weighted like MAGUS's true edges (backbone weight per true residue pair). Measures what MAGUS's missing
evidence costs on its own. Reads the reference."""
FAMILY = "ceiling"
GRID = [{}]


def apply(g):
    t = g.true_pairs
    true = t > 0
    per_pair = g.w[true].sum() / max(t[true].sum(), 1)
    a, b, tm = g.true_missing()
    return g.w, (a, b, tm * per_pair)
