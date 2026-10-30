# AI-assisted (Claude), exploration code for CS581 project
"""Hook a strategy into MAGUS: replace the graph-building step, leave everything else (MCL, trace) as MAGUS has it.

Targets the MAGUS package layout of commit 39041fc (magus.align.merge.graph_build.graph_builder), the commit
MAGUS_COMMIT pins. install() monkey-patches graph_builder.buildMatrix; MAGUS's source is not edited.

The replacement builds MAGUS's graph exactly (sum over backbones of A_b^T A_b, integer weights, self loops and
same-subset entries included), applies the strategy to the cross-subset edges, and stores the result behind a
read-only dict-like CSR view that MAGUS's clustering and trace code accept.
With strategy "magus" the graph is MAGUS's own, so MAGUS's alignment is reproduced.
"""
import json
import os
import time

import numpy as np
import scipy.sparse as sp

from . import registry
from .graph import EdgeGraph, fingerprint


class _Row:
    __slots__ = ("idx", "val")

    def __init__(self, idx, val):
        self.idx, self.val = idx, val

    def get(self, key, default=None):
        i = np.searchsorted(self.idx, key)
        if i < len(self.idx) and self.idx[i] == key:
            return int(self.val[i])
        return default

    def __getitem__(self, key):
        v = self.get(key)
        if v is None:
            raise KeyError(key)
        return v

    def __contains__(self, key):
        return self.get(key) is not None

    def items(self):
        return list(zip(self.idx.tolist(), self.val.tolist()))  # a list: MAGUS's mlr_mcl takes len() of it

    def keys(self):
        return self.idx.tolist()

    def values(self):
        return self.val.tolist()

    def __iter__(self):
        return iter(self.idx.tolist())

    def __len__(self):
        return len(self.idx)


class CSRGraph:
    def __init__(self, csr):
        csr.sort_indices()
        self.csr = csr

    def __len__(self):
        return self.csr.shape[0]

    def __getitem__(self, a):
        s, e = self.csr.indptr[a], self.csr.indptr[a + 1]
        return _Row(self.csr.indices[s:e], self.csr.data[s:e])

    def __iter__(self):
        return (self[a] for a in range(len(self)))


def _column_matrix(alignmap, n):
    rows, cols, vals = [], [], []
    for l, column in enumerate(alignmap):
        for node, count in column.items():
            rows.append(l)
            cols.append(node)
            vals.append(count)
    return sp.csr_matrix((np.array(vals, dtype=np.int64), (rows, cols)), shape=(len(alignmap), n))


def build_edge_graph(context, cache_dir=None):
    """MAGUS's graph from the context's backbones, as an EdgeGraph (loaded from cache_dir when inputs match)."""
    from magus.align.merge.graph_build import graph_builder as gb
    from magus.configuration import Configs
    from magus.helpers import sequenceutils
    from magus.tasks import task

    files = [t.outputFile for t in task.asCompleted(context.backboneTasks)]
    for path in context.backbonePaths:
        if path not in files:
            files.append(path)
    files = sorted(files)
    sub = np.array([s for s, _ in context.graph.matSubPosMap], dtype=np.int64)
    key = fingerprint(list(context.subalignmentPaths) + files)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        meta = os.path.join(cache_dir, "graph.json")
        if os.path.exists(meta) and json.load(open(meta)).get("key") == key:
            Configs.log("[graphmods] graph loaded from cache " + cache_dir)
            return EdgeGraph.load(os.path.join(cache_dir, "graph.npz"), cache_dir), files
        for f in os.listdir(cache_dir):  # stale cache for other inputs
            if f.startswith(("feat_", "graph.")):
                os.remove(os.path.join(cache_dir, f))
    n = context.graph.matrixSize
    total = sp.csr_matrix((n, n), dtype=np.int64)
    support = sp.csr_matrix((n, n), dtype=np.int64)
    cover = np.zeros(n, dtype=np.int64)
    R = np.zeros((n, len(files)), dtype=np.int32)
    for bi, f in enumerate(files):
        aln = sequenceutils.readFromFasta(f)
        length = len(next(iter(aln.values())).seq)
        if f in context.backboneExtend:
            ext = gb.requestHmmExtensionTasks(context, aln, f)
            task.submitTasks(ext)
            for t in task.asCompleted(ext):
                aln.update(sequenceutils.readFromStockholm(t.outputFile, includeInsertions=True))
        A = _column_matrix(gb.backboneToAlignMap(context, aln, length), n)
        prod = (A.T @ A).tocsr()
        total = total + prod
        support = support + (prod > 0).astype(np.int64)
        col = np.asarray(A.sum(axis=0)).ravel()
        R[:, bi] = col
        cover |= (col > 0).astype(np.int64) << bi
    g = EdgeGraph.from_matrices(total.tocsr(), support.tocsr(), cover, R, sub, len(files), cache_dir)
    if cache_dir:
        g.save(os.path.join(cache_dir, "graph.npz"))
        json.dump({"key": key, "subsets": list(context.subalignmentPaths), "backbones": files},
                  open(os.path.join(cache_dir, "graph.json"), "w"), indent=1)
    Configs.log("[graphmods] built graph: {} nodes, {} cross edges, {} backbones".format(g.N, len(g.w), len(files)))
    return g, files


def run_strategy(g, strategy, params):
    out = strategy.apply(g, **params)
    added = None
    if isinstance(out, tuple):
        out, added = out
    return np.asarray(out, dtype=float), added


def install(name, params=None, strategies=None, cache_dir=None, info_path=None):
    """Patch MAGUS so that its graph step runs strategy `name` with `params`."""
    from magus.align.merge import alignment_graph
    from magus.align.merge.graph_build import graph_builder as gb
    from magus.configuration import Configs

    params = params or {}
    strategy = registry.load(name, strategies)

    def buildMatrix(context):
        if Configs.graphBuildRestrict:
            raise SystemExit("graphmods: --graphbuildrestrict is not supported")
        t0 = time.time()
        g, files = build_edge_graph(context, cache_dir)
        t1 = time.time()
        new_w, added = run_strategy(g, strategy, params)
        M, info = g.to_csr(new_w, added)
        t2 = time.time()
        context.graph.matrix = CSRGraph(M)
        info.update(strategy=name, params=params, family=strategy.FAMILY,
                    variant=registry.variant_name(name, params), backbones=len(files),
                    graph_s=round(t1 - t0, 2), strategy_s=round(t2 - t1, 2), feature_s=g.timings,
                    features_used=sorted(g.used), feature_cold_s={f: g.cold.get(f) for f in sorted(g.used)},
                    notes=g.notes)
        Configs.log("[graphmods] {}: kept {} of {} cross edges, added {}".format(
            info["variant"], info["kept_edges"], info["edges"], info["added_edges"]))
        if info_path:
            json.dump(info, open(info_path, "w"), indent=1, default=str)

    original_write = alignment_graph.AlignmentGraph.writeGraphToFile
    original_cost = alignment_graph.AlignmentGraph.computeClusteringCost

    def writeGraphToFile(self, filePath):
        if not isinstance(self.matrix, CSRGraph):
            return original_write(self, filePath)
        coo = self.matrix.csr.tocoo()
        np.savetxt(filePath, np.column_stack([coo.row, coo.col, coo.data]), fmt="%d")
        Configs.log("Wrote matrix to {}".format(filePath))

    def computeClusteringCost(self, clusters):
        if not isinstance(self.matrix, CSRGraph):
            return original_cost(self, clusters)
        label = np.arange(self.matrixSize) + len(clusters)
        for c, cluster in enumerate(clusters):
            label[np.asarray(cluster, dtype=np.int64)] = c
        sub = np.array([s for s, _ in self.matSubPosMap])
        coo = self.matrix.csr.tocoo()
        cut = (sub[coo.row] != sub[coo.col]) & (label[coo.row] != label[coo.col])
        return int(coo.data[cut].sum() / 2)

    gb.buildMatrix = buildMatrix
    alignment_graph.AlignmentGraph.writeGraphToFile = writeGraphToFile
    alignment_graph.AlignmentGraph.computeClusteringCost = computeClusteringCost
    return strategy
