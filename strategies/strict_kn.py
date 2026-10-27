# AI-assisted (Claude), exploration code for CS581 project
"""Strict cutoff on the fraction of backbones that could have supported the edge: keep iff k >= F * n
(n = backbones holding a letter in both columns)."""
import numpy as np

FAMILY = "strict"
GRID = [{"F": round(F / 10, 1)} for F in range(2, 11)]


def apply(g, F):
    return np.where(g.k >= F * g.n - 1e-9, g.w, 0)
