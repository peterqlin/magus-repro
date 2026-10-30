# AI-assisted (Claude), exploration code for CS581 project
"""Training data for learned_weights (not a method: it reads the reference): writes, for up to max_edges random
edges of the dataset, the features of graphmods/learned.py (both sets, so OPAL runs) and the label true_w / w to
runs/_graphmods/edge_features/<dataset>.npz ($GRAPHMODS_DUMP_DIR), and leaves MAGUS's graph unchanged."""
import os

import numpy as np

from graphmods import learned

FAMILY = "ceiling"
GRID = [{}]
NEEDS_INPUTS = True


def apply(g, max_edges=300000):
    name = os.environ.get("GRAPHMODS_NAME") or "unnamed"
    X = learned.features(g, opal=True)
    y = np.clip(g.true_w / np.maximum(g.w, 1), 0, 1)
    idx = np.arange(len(g.w))
    if len(idx) > max_edges:
        idx = np.sort(np.random.default_rng(0).choice(idx, max_edges, replace=False))
    os.makedirs(learned.DUMP_DIR, exist_ok=True)
    tmp = os.path.join(learned.DUMP_DIR, name + ".tmp.npz")
    np.savez_compressed(tmp, X=X[idx], y=y[idx], w=g.w[idx].astype(np.float64), features=np.array(learned.SETS["opal"]),
                        edges=np.array([len(g.w)]), true_frac=np.array([g.true_w.sum() / max(g.w.sum(), 1)]))
    os.replace(tmp, os.path.join(learned.DUMP_DIR, name + ".npz"))
    g.notes["dumped_edges"] = int(len(idx))
    return g.w
