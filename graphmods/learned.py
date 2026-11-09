# AI-assisted (Claude), exploration code for CS581 project
"""Learned edge weights: per-edge features, and a fractional logistic regression from them to the fraction of an
edge's weight that is true (true_w / w, from the reference; graphmods/oracle.py).

    strategies/dump_edge_features.py   writes features and labels per dataset (a ceiling: it reads the reference)
    scripts/graphmods_train.py         fits the model, two folds by replicate parity
    strategies/learned_weights.py      applies the model trained on the other parity, so no dataset is scored by a
                                       model that saw it

Features are symmetric in the edge's two columns (min / max of per-column values). Two feature sets: "base" (the
backbones and the graph) and "opal" (base plus OPAL's verdict on the edge, graphmods/evidence.py).
"""
import json
import os
import re

import numpy as np

PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP_DIR = os.environ.get("GRAPHMODS_DUMP_DIR") or os.path.join(PKG_ROOT, "runs", "_graphmods", "edge_features")
MODEL = os.environ.get("GRAPHMODS_MODEL") or os.path.join(PKG_ROOT, "results", "graphmods_edge_model.json")
FEATURES = ["log_w", "k_frac", "n_frac", "k_over_n", "s", "ovl", "log_emb", "log_chain_offset", "diag_support",
            "occ_min", "occ_max", "backbone_em", "best_min", "best_max", "log_deg_min", "log_deg_max"]
OPAL_FEATURES = ["opal_on", "log_opal"]
SETS = {"base": FEATURES, "opal": FEATURES + OPAL_FEATURES}


def features(g, opal=False):
    occ, (ra, rb), deg = g.occupancy, g.best_ratio, g.deg
    oa, ob, da, db = occ[g.a], occ[g.b], deg[g.a], deg[g.b]
    cols = {
        "log_w": np.log1p(g.w), "k_frac": g.k / g.B, "n_frac": g.n / g.B, "k_over_n": g.k / np.maximum(g.n, 1),
        "s": g.s, "ovl": g.ovl, "log_emb": np.log1p(g.emb), "log_chain_offset": np.log1p(g.chain_offset),
        "diag_support": g.diag_support, "occ_min": np.minimum(oa, ob), "occ_max": np.maximum(oa, ob),
        "backbone_em": g.backbone_em, "best_min": np.minimum(ra, rb), "best_max": np.maximum(ra, rb),
        "log_deg_min": np.log1p(np.minimum(da, db)), "log_deg_max": np.log1p(np.maximum(da, db)),
    }
    if opal:
        cols.update(opal_on=(g.opal_pairs > 0).astype(float), log_opal=np.log1p(g.opal_pairs))
    return np.column_stack([cols[f] for f in SETS["opal" if opal else "base"]]).astype(np.float64)


def replicate(name):
    m = re.search(r"_R(\d+)$", name or "")
    return int(m.group(1)) if m else None


def design(X, mean, std):
    Z = (X - mean) / std
    return np.column_stack([np.ones(len(Z)), Z, Z ** 2])


def predict(model, X):
    z = design(X, np.array(model["mean"]), np.array(model["std"])) @ np.array(model["coef"])
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))


def fit(X, y, wt, l2=1e-3):
    """Fractional logistic regression (labels in [0, 1], sample weights wt), L2 on everything but the intercept."""
    from scipy.optimize import minimize
    mean, std = X.mean(axis=0), X.std(axis=0)
    std[std == 0] = 1
    D = design(X, mean, std)
    wt = wt / wt.sum()

    def loss(c):
        z = D @ c
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))
        ll = -(wt * (y * np.log(np.maximum(p, 1e-12)) + (1 - y) * np.log(np.maximum(1 - p, 1e-12)))).sum()
        grad = D.T @ (wt * (p - y))
        reg = l2 * (c[1:] ** 2).sum()
        grad[1:] += 2 * l2 * c[1:]
        return ll + reg, grad
    c = minimize(loss, np.zeros(D.shape[1]), jac=True, method="L-BFGS-B", options={"maxiter": 2000}).x
    return {"mean": mean.tolist(), "std": std.tolist(), "coef": c.tolist(), "l2": l2}


def load_model(name, features="base"):
    """The model for feature set `features` trained on the replicates of the other parity than dataset `name`."""
    if not os.path.exists(MODEL):
        raise SystemExit("no edge model at {} (scripts/graphmods_train.py writes it)".format(MODEL))
    models = json.load(open(MODEL))[features]
    r = replicate(name)
    if r is None:
        raise SystemExit("learned weights need the dataset name ($GRAPHMODS_NAME, <condition>_R<replicate>)")
    return models["odd" if r % 2 == 0 else "even"]
