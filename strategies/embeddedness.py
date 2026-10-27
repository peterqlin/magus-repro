# AI-assisted (Claude), exploration code for CS581 project
"""Embeddedness = number of nodes adjacent to both endpoints (= triangles the edge sits in). Edges with embeddedness
below tau get weight w * factor: factor 0 drops them, 0.5 / 0.25 downweights them. tau values: quantiles 0.10-0.70 of
all edges' embeddedness on the project's training replicates, fixed before any accuracy was seen."""
import numpy as np

FAMILY = "network"
GRID = [{"tau": tau, "factor": f} for tau in (25, 34, 50, 74, 111) for f in (0, 0.5, 0.25)]


def apply(g, tau, factor):
    return np.where(g.emb < tau, g.w * factor, g.w)
