# AI-assisted (Claude), exploration code for CS581 project
"""Backbones as noisy annotators: instead of counting votes (k), fit each backbone's own hit rate on true and on
false edges (one-coin Dawid-Skene, EM over the backbones that hold both columns of an edge) and take the posterior
that the edge is true (g.backbone_em). mode=weight multiplies the weight by it; mode=cut deletes edges below t."""
import numpy as np

FAMILY = "adaptive"
GRID = [{"mode": "weight"}, {"mode": "cut", "t": 0.5}, {"mode": "cut", "t": 0.9}]


def apply(g, mode, t=0.5):
    p = g.backbone_em
    return g.w * p if mode == "weight" else np.where(p >= t, g.w, 0)
