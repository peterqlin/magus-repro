# AI-assisted (Claude), exploration code for CS581 project
"""Gappy columns: columns that few of their subset's sequences fill are where subset alignments are least reliable.
Each edge's weight is multiplied by o ** gamma, o = the smaller occupancy (fraction of the subset's sequences with a
residue there, g.occupancy) of its two columns; with theta, edges with o < theta are deleted instead."""
import numpy as np

FAMILY = "structure"
GRID = [{"gamma": x} for x in (0.5, 1, 2)] + [{"theta": t} for t in (0.1, 0.25)]
NEEDS_INPUTS = True  # reads the subset alignments


def apply(g, gamma=0, theta=0):
    occ = g.occupancy
    o = np.minimum(occ[g.a], occ[g.b])
    w = g.w * o ** gamma if gamma else g.w.astype(float)
    return np.where(o < theta, 0, w)
