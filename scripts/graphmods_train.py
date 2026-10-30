#!/usr/bin/env python3
# AI-assisted (Claude), exploration code for CS581 project
"""Fit the edge model that strategies/learned_weights.py applies, from the dumps of strategies/dump_edge_features.py.

Usage: graphmods_train.py [--dumps runs/_graphmods/edge_features] [--out results/graphmods_edge_model.json]

Per feature set (graphmods/learned.py SETS: base, opal), two models: "even" fitted on the even replicates, "odd" on the
odd ones; learned_weights uses the one fitted on the other parity. Each edge counts with weight w (the loss is over letter pairs, as MAGUS's weights are). Prints, per
model, the held-out weighted log loss against a constant model and the share of false and of true weight a cut at
p >= 0.5 keeps.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from graphmods import learned  # noqa: E402


def load(paths, features):
    X, y, w = [], [], []
    for p in paths:
        z = np.load(p)
        names = list(z["features"])
        missing = [f for f in features if f not in names]
        assert not missing, "{}: dumped without {}".format(p, missing)
        X.append(z["X"][:, [names.index(f) for f in features]]); y.append(z["y"]); w.append(z["w"])
    return np.concatenate(X), np.concatenate(y), np.concatenate(w)


def logloss(p, y, w):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return float(-(w * (y * np.log(p) + (1 - y) * np.log(1 - p))).sum() / w.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dumps", default=learned.DUMP_DIR)
    ap.add_argument("--out", default=learned.MODEL)
    ap.add_argument("--l2", type=float, default=1e-3)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.dumps, "*.npz")))
    files = [f for f in files if not f.endswith(".tmp.npz")]
    by = {0: [], 1: []}
    for f in files:
        r = learned.replicate(os.path.basename(f)[:-4])
        if r is not None:
            by[r % 2].append(f)
    if not by[0] or not by[1]:
        sys.exit("need dumps of even and odd replicates in {} (found {} and {})".format(a.dumps, len(by[0]), len(by[1])))
    models = {}
    for fset, features in learned.SETS.items():
        models[fset] = {}
        for parity, label in ((0, "even"), (1, "odd")):
            X, y, w = load(by[parity], features)
            m = models[fset][label] = learned.fit(X, y, w, a.l2)
            m.update(features=features, datasets=len(by[parity]))
            Xt, yt, wt = load(by[1 - parity], features)
            p = learned.predict(m, Xt)
            const = np.full(len(yt), np.average(y, weights=w))
            keep = p >= 0.5
            true_w, false_w = wt * yt, wt * (1 - yt)
            print("{} model {} ({} datasets, {} edges) on the {} other-parity datasets: log loss {:.4f} (constant "
                  "{:.4f}); cut p >= 0.5 keeps {:.1%} of true and {:.1%} of false weight".format(
                      fset, label, len(by[parity]), len(y), len(by[1 - parity]), logloss(p, yt, wt),
                      logloss(const, yt, wt), true_w[keep].sum() / true_w.sum(),
                      false_w[keep].sum() / max(false_w.sum(), 1e-12)))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(models, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
