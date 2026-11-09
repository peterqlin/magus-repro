# AI-assisted (Claude), exploration code for CS581 project
"""Helper for iterate and consensus_runs, not swept (the name starts with "_"): MAGUS's graph reweighted by the
fraction f of the alignments in $GRAPHMODS_ALIGNMENTS (os.pathsep-separated merges of these subset alignments) that
put each edge's two columns in one column. mode=filter: edges with f < t get weight times factor; mode=weight:
w * f; mode=boost: w * (1 + lam * f)."""
import os

import numpy as np

from graphmods.evidence import node_columns

FAMILY = "iterate"
GRID = [{}]
NEEDS_INPUTS = True


def agreement(g):
    paths = [p for p in os.environ.get("GRAPHMODS_ALIGNMENTS", "").split(os.pathsep) if p]
    if not paths:
        raise SystemExit("_from_alignment needs $GRAPHMODS_ALIGNMENTS")
    votes = np.zeros(len(g.a))
    for p in paths:
        col = node_columns(g.subset_paths, p)
        votes += (col[g.a] == col[g.b]) & (col[g.a] >= 0)
    g.notes["alignments"] = len(paths)
    return votes / len(paths)


def apply(g, mode="filter", t=0.5, factor=0, lam=1):
    f = agreement(g)
    if mode == "filter":
        return np.where(f >= t, g.w, g.w * factor)
    if mode == "weight":
        return g.w * f
    return g.w * (1 + lam * f)
