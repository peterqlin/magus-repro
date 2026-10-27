# AI-assisted (Claude), exploration code for CS581 project
"""Neighbourhood overlap = embeddedness / |N(a) | N(b) minus {a, b}| (embeddedness corrected for nodes that have many
neighbours anyway; 0 to 1). Edges with overlap below tau get weight w * factor (0 drops, 0.5 / 0.25 downweight).
tau values: quantiles 0.10-0.70 of all edges' overlap on the project's training replicates."""
import numpy as np

FAMILY = "network"
GRID = [{"tau": tau, "factor": f} for tau in (0.14, 0.205, 0.261, 0.325, 0.423) for f in (0, 0.5, 0.25)]


def apply(g, tau, factor):
    return np.where(g.ovl < tau, g.w * factor, g.w)
