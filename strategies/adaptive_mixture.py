# AI-assisted (Claude), exploration code for CS581 project
"""Adaptive cutoff: fit a two-component mixture to this dataset's (k, n) values (true edges vs false edges, binomial or
beta-binomial components, EM, no reference) and keep an edge iff its posterior P(true | k, n) > t. The fitted model
implies a k cutoff for every n, so the cutoff adapts to each dataset."""
import numpy as np

FAMILY = "adaptive"
GRID = [{"kind": kind, "t": t} for kind in ("binom", "bb") for t in (0.5, 0.9)]


def apply(g, kind, t):
    return np.where(g.posterior(kind) > t, g.w, 0)
