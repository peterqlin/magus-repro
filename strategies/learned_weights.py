# AI-assisted (Claude), exploration code for CS581 project
"""Learned edge weights: p = the fitted probability that an edge's letter pairs are true (graphmods/learned.py,
fractional logistic regression on the edge's features, trained by scripts/graphmods_train.py on the replicates of
the other parity, so the model never saw this dataset). mode=weight: w * p; weight2: w * p^2; cut: w where p >= t."""
import os

import numpy as np

from graphmods import learned

FAMILY = "learned"
GRID = [{"mode": "weight"}, {"mode": "weight2"}, {"mode": "cut", "t": 0.5}, {"mode": "cut", "t": 0.3}]
NEEDS_INPUTS = True


def apply(g, mode, t=0.5):
    model = learned.load_model(os.environ.get("GRAPHMODS_NAME"))
    p = learned.predict(model, learned.features(g))
    g.notes["mean_p"] = float(np.average(p, weights=g.w))
    if mode == "weight":
        return g.w * p
    if mode == "weight2":
        return g.w * p ** 2
    return np.where(p >= t, g.w, 0)
