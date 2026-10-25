# AI-assisted (Claude), exploration code for CS581 project
"""Strict cutoff on support: keep an edge only if at least K backbones align a letter pair of its two columns (k >= K)."""
import numpy as np

FAMILY = "strict"
GRID = [{"K": K} for K in range(2, 11)]


def apply(g, K):
    return np.where(g.k >= K, g.w, 0)
