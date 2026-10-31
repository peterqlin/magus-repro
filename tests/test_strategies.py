# AI-assisted (Claude), exploration code for CS581 project
"""Smoke test without MAGUS: every strategy in the folder, at every grid point, on a small random graph built the way
MAGUS builds it (sum over backbones of A_b^T A_b). Checks shapes, that "magus" leaves the graph unchanged, that the
feature cache round-trips, that the cold-cost accounting charges features loaded from the cache, and the structure
features, subset repair and edge model on toy inputs. Strategies with NEEDS_INPUTS (they read the subset alignments)
are left to a replay on real inputs.

    python -m pytest tests        or        python tests/test_strategies.py
"""
import os
import sys
import tempfile

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from graphmods import registry  # noqa: E402
from graphmods.graph import EdgeGraph  # noqa: E402
from graphmods.hook import run_strategy  # noqa: E402


def random_graph(seed=0, n_sub=4, cols=30, seqs=40, B=6, cache_dir=None):
    rng = np.random.default_rng(seed)
    N = n_sub * cols
    sub = np.repeat(np.arange(n_sub), cols)
    total = sp.csr_matrix((N, N), dtype=np.int64)
    support = sp.csr_matrix((N, N), dtype=np.int64)
    bits = sp.csr_matrix((N, N), dtype=np.int64)
    cover = np.zeros(N, dtype=np.int64)
    R = np.zeros((N, B), dtype=np.int32)
    for b in range(B):
        # each backbone letter lands in one column per subset, near its true column
        rows, colidx = [], []
        for s in range(seqs):
            base = rng.integers(0, cols - 2)
            for t in range(n_sub):
                if rng.random() < 0.8:
                    rows.append(s)
                    colidx.append(t * cols + min(cols - 1, base + rng.integers(0, 2)))
        A = sp.csr_matrix((np.ones(len(rows), dtype=np.int64), (rows, colidx)), shape=(seqs, N))
        P = (A.T @ A).tocsr()
        total = total + P
        support = support + (P > 0).astype(np.int64)
        bits = bits + (P > 0).astype(np.int64) * (1 << b)
        c = np.asarray(A.sum(axis=0)).ravel()
        R[:, b] = c
        cover |= (c > 0).astype(np.int64) << b
    return EdgeGraph.from_matrices(total.tocsr(), support.tocsr(), cover, R, sub, B, cache_dir,
                                   support_bits=bits.tocsr()), total.tocsr()


def test_every_strategy_runs():
    g, total = random_graph()
    assert len(g.w) > 0
    for m in registry.all_strategies():
        if not hasattr(m, "apply") or m.FAMILY == "ceiling" or getattr(m, "NEEDS_INPUTS", False):
            continue  # whole merges, ceilings and strategies that read the subset alignments need real inputs
        for params in m.GRID:
            w, added = run_strategy(g, m, dict(params))
            assert w.shape == g.w.shape, (m.NAME, params)
            assert np.all(np.isfinite(w)) and np.all(w >= 0), (m.NAME, params)
            M, info = g.to_csr(w, added)
            assert M.shape == total.shape
            assert (M != M.T).nnz == 0, "graph must stay symmetric"


def test_magus_is_identity():
    g, total = random_graph()
    w, added = run_strategy(g, registry.load("magus"), {})
    M, info = g.to_csr(w, added)
    assert info["weight_scale"] == 1
    assert (M - total).nnz == 0


def test_feature_cache_and_cold_cost():
    with tempfile.TemporaryDirectory() as d:
        g, _ = random_graph(cache_dir=d)
        first = (g.ovl.copy(), g.tc.copy(), g.missing_tc())
        assert {"emb", "ovl", "poss", "tc"} <= set(g.cold)
        g2, _ = random_graph(cache_dir=d)
        assert np.array_equal(g2.ovl, first[0]) and np.array_equal(g2.tc, first[1])
        assert all(np.array_equal(x, y) for x, y in zip(g2.missing_tc(), first[2]))
        assert g2.timings == {}, "everything was loaded from the cache"
        assert {"ovl", "emb", "tc", "poss", "missing_tc"} <= g2.used, "dependencies are charged too"
        assert all(g2.cold[f] is not None for f in g2.used)


def test_structure_features():
    from graphmods.graph import heaviest_chain
    pa, pb = heaviest_chain(np.array([0, 1, 1, 2]), np.array([0, 2, 1, 3]), np.array([1.0, 1, 5, 1]))
    assert pa.tolist() == [0, 1, 2] and pb.tolist() == [0, 1, 3]
    g, _ = random_graph()
    assert np.all(g.chain_offset >= 0) and np.all((g.diag_support >= 0) & (g.diag_support <= 2))
    p = g.backbone_em
    assert np.all((p >= 0) & (p <= 1))
    ra, rb = g.best_ratio
    assert np.all((ra > 0) & (ra <= 1)) and np.all((rb > 0) & (rb <= 1))


def test_kb_matches_k():
    g, _ = random_graph()
    from graphmods.graph import popcount
    assert np.array_equal(popcount(g.kb), g.k)


def test_repair_splits_mixed_column():
    from graphmods.repair import repair
    sub = {"a": "ACG", "b": "ACG", "c": "ACG", "d": "ACG"}
    # two backbones put c's C apart from the others' C, none puts it with them
    backbones = [{"a": "AC-G", "b": "AC-G", "c": "A-CG"}, {"a": "AC-G", "c": "A-CG", "d": "AC-G"}, {"b": "ACG", "d": "ACG"}]
    fixed, n = repair(sub, backbones, 2)
    assert n == 1 and fixed == {"a": "AC-G", "b": "AC-G", "c": "A-CG", "d": "AC-G"}
    assert repair(sub, backbones, 3) == (sub, 0)


def test_learned_fit():
    from graphmods import learned
    rng = np.random.default_rng(1)
    X = rng.normal(size=(5000, len(learned.FEATURES)))
    p = 1 / (1 + np.exp(-(2 * X[:, 0] - X[:, 3] - 1)))
    model = learned.fit(X, rng.binomial(10, p) / 10, rng.integers(1, 50, len(p)).astype(float))
    assert len(model["coef"]) == 1 + 2 * len(learned.FEATURES)
    assert np.abs(learned.predict(model, X) - p).mean() < 0.03


if __name__ == "__main__":
    test_every_strategy_runs()
    test_structure_features()
    test_kb_matches_k()
    test_repair_splits_mixed_column()
    test_learned_fit()
    test_magus_is_identity()
    test_feature_cache_and_cold_cost()
    print("ok")
