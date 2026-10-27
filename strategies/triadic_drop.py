# AI-assisted (Claude), exploration code for CS581 project
"""Triadic closure, removing edges: drop an edge whose closure score t_ab is below tau (weakly closed edges).
tau values: quantiles 0.10-0.70 of all edges' t on the project's training replicates."""
import numpy as np

FAMILY = "network"
GRID = [{"tau": tau} for tau in (0.0081, 0.0136, 0.023, 0.0422, 0.18)]


def apply(g, tau):
    return np.where(g.tc < tau, 0, g.w)
