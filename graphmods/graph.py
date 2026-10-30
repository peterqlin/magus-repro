# AI-assisted (Claude), exploration code for CS581 project
"""The alignment graph a strategy sees: MAGUS's cross-subset edges plus per-edge evidence.

MAGUS's graph is sum over backbones b of A_b^T A_b, where A_b is the (backbone column x graph node) count matrix of
backbone b (the same graph MAGUS's own buildMatrix produces, built here with sparse matrix products). Nodes are
the columns of the subset alignments. From the same pass we keep, per cross-subset edge (a, b), a < b:

    w   MAGUS's edge weight (letter pairs summed over backbones)
    k   support: number of backbones that align at least one letter pair of a and b
    n   exposure: number of backbones holding a letter in both a and b (the backbones that COULD support the edge)

and per node and backbone R[node, j] = letters of that node present in backbone j (for poss below).

Derived features (computed on first use, then cached on the object and in the optional cache directory):
    emb   embeddedness |N(a) & N(b)| on the cross-subset graph (all edges)
    ovl   neighbourhood overlap emb / |N(a) | N(b) minus {a, b}|, 0 if that is 0
    poss  sum_j R[a, j] R[b, j]: letter pairs the backbones could have aligned
    s     normalised strength clip(w / max(poss, 1), 0, 1)
    tc    triadic closure, resource allocation: t_ab = sum_c s_ac s_cb / sigma_c, sigma_c = sum_x s_cx
    missing_tc()  missing pairs that are each other's best missing partner in the other's subset, with their t and poss

A strategy returns new weights for the existing cross edges (0 deletes an edge) and optionally added edges.
Self loops and same-subset entries of MAGUS's matrix are always kept as MAGUS built them.
"""
import hashlib
import json
import os
import time

import numpy as np
import scipy.sparse as sp

BLOCK = 512  # rows per block in the 2-hop products (memory ~ BLOCK x nodes)


def popcount(x):
    x = x.astype(np.uint64)
    c = np.zeros(len(x), dtype=np.int64)
    while x.any():
        c += (x & np.uint64(1)).astype(np.int64)
        x >>= np.uint64(1)
    return c


def heaviest_chain(pa, pb, w):
    """Heaviest set of points strictly increasing in both pa and pb (weighted LIS with a Fenwick tree of maxima).
    Returns the chain's pa and pb, increasing."""
    order = np.lexsort((-pb, pa))  # equal pa: larger pb first, so two points with one pa never chain
    pa, pb, w = pa[order], pb[order], w[order].astype(float)
    size = int(pb.max()) + 2
    tree_v, tree_i = [0.0] * (size + 1), [-1] * (size + 1)
    best, parent = [0.0] * len(pa), [-1] * len(pa)
    for i in range(len(pa)):
        j, v, arg = int(pb[i]), 0.0, -1  # max over pb' < pb[i]: prefix [0, pb[i]) = Fenwick indices 1..pb[i]
        while j > 0:
            if tree_v[j] > v:
                v, arg = tree_v[j], tree_i[j]
            j -= j & -j
        best[i], parent[i] = v + w[i], arg
        j = int(pb[i]) + 1
        while j <= size:
            if best[i] > tree_v[j]:
                tree_v[j], tree_i[j] = best[i], i
            j += j & -j
    i = int(np.argmax(best))
    chain = []
    while i >= 0:
        chain.append(i)
        i = parent[i]
    chain = chain[::-1]
    return pa[chain], pb[chain]


def pair_lookup(M, r, c):
    """M[r[i], c[i]] for CSR M (0 where absent), vectorized."""
    M = M.tocsr()
    M.sort_indices()
    out = np.zeros(len(r))
    if M.nnz == 0 or len(r) == 0:
        return out
    rowid = np.repeat(np.arange(M.shape[0], dtype=np.int64), np.diff(M.indptr))
    keys = rowid * M.shape[1] + M.indices
    q = r.astype(np.int64) * M.shape[1] + c
    pos = np.clip(np.searchsorted(keys, q), 0, len(keys) - 1)
    ok = keys[pos] == q
    out[ok] = M.data[pos[ok]]
    return out


class EdgeGraph:
    def __init__(self, other, a, b, w, k, n, sub, R, B, cache_dir=None, kb=None):
        self.other = other          # (rows, cols, vals): self loops and same-subset entries, kept as MAGUS built them
        self.a, self.b, self.w, self.k, self.n = a, b, w, k, n
        self.kb = kb                # per edge: bit j set if backbone j aligns a letter pair of it (None: older cache)
        self.sub = sub              # node -> subset index
        self.R = R                  # (nodes x backbones) letters per node per backbone
        self.B = B                  # number of backbones
        self.N = len(sub)
        self.cache_dir = cache_dir
        self._f = {}
        self.timings = {}           # feature -> seconds to compute it in this process (exclusive of nested features)
        self.cold = {}              # feature -> seconds it took when first computed (this process or the cache)
        self.used = set()           # features the strategy touched, directly or through another feature
        self.notes = {}             # e.g. mixture fits
        self._stack = []            # nested compute times, for exclusive timings
        self._deps = []             # features touched while computing the one on top
        self._depmap = {}           # feature -> every feature it was built from

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_matrices(cls, total, support, cover, R, sub, B, cache_dir=None, support_bits=None):
        coo = sp.triu(total, k=1).tocoo()
        keep = sub[coo.row] != sub[coo.col]
        a, b, w = coo.row[keep].astype(np.int64), coo.col[keep].astype(np.int64), coo.data[keep].astype(np.int64)
        o = np.lexsort((b, a))
        a, b, w = a[o], b[o], w[o]
        k = pair_lookup(support, a, b).astype(np.int64)
        n = popcount(cover[a] & cover[b])
        kb = pair_lookup(support_bits, a, b).astype(np.int64) if support_bits is not None else None
        full = total.tocoo()
        cross = sub[full.row] != sub[full.col]
        other = (full.row[~cross].astype(np.int64), full.col[~cross].astype(np.int64), full.data[~cross].astype(np.int64))
        g = cls(other, a, b, w, k, n, sub, R, B, cache_dir, kb)
        g.cover = cover
        return g

    def save(self, path):
        np.savez_compressed(path, a=self.a, b=self.b, w=self.w, k=self.k, n=self.n, sub=self.sub, R=self.R,
                            B=np.array([self.B]), o_r=self.other[0], o_c=self.other[1], o_v=self.other[2],
                            **({"kb": self.kb} if self.kb is not None else {}),
                            **({"cover": self.cover} if getattr(self, "cover", None) is not None else {}))

    @classmethod
    def load(cls, path, cache_dir=None):
        z = np.load(path)
        g = cls((z["o_r"], z["o_c"], z["o_v"]), z["a"], z["b"], z["w"], z["k"], z["n"], z["sub"], z["R"],
                int(z["B"][0]), cache_dir, z["kb"] if "kb" in z.files else None)
        g.cover = z["cover"] if "cover" in z.files else None
        return g

    # ------------------------------------------------------------------ features (lazy, cached)
    def _cached(self, name, fn):
        """Compute a feature once. The cache file keeps its compute time and the features it was built from, so a run
        that loads it still reports what it would cost cold, which is what a single MAGUS run pays."""
        if name not in self._f:
            path = os.path.join(self.cache_dir, "feat_" + name + ".npz") if self.cache_dir else None
            if path and os.path.exists(path):
                z = np.load(path)
                xs = sorted((f for f in z.files if f.startswith("x")), key=lambda f: int(f[1:]))
                val = tuple(z[f] for f in xs) if len(xs) > 1 else z["x0"]
                self.cold[name] = float(z["time"]) if "time" in z.files else None
                self._depmap[name] = {str(d) for d in z["deps"]} if "deps" in z.files else set()
                for d in self._depmap[name]:
                    self._cold_from_cache(d)
            else:
                t0 = time.time()
                self._stack.append(0.0)
                self._deps.append(set())
                val = fn()
                nested = self._stack.pop()
                self._depmap[name] = self._deps.pop()
                dt = time.time() - t0
                if self._stack:
                    self._stack[-1] += dt
                self.timings[name] = self.cold[name] = round(dt - nested, 2)  # exclusive of nested features
                if path:
                    arrs = val if isinstance(val, tuple) else (val,)
                    np.savez_compressed(path, time=np.array(self.cold[name]),
                                        deps=np.array(sorted(self._depmap[name]), dtype=str),
                                        **{f"x{i}": v for i, v in enumerate(arrs)})
            self._f[name] = val
        names = {name} | self._depmap[name]
        self.used |= names
        if self._deps:
            self._deps[-1] |= names
        return self._f[name]

    def _cold_from_cache(self, name):
        path = os.path.join(self.cache_dir, "feat_" + name + ".npz") if self.cache_dir else None
        if name not in self.cold and path and os.path.exists(path):
            z = np.load(path)
            self.cold[name] = float(z["time"]) if "time" in z.files else None

    def adjacency(self):
        ones = np.ones(len(self.a))
        A = sp.csr_matrix((np.r_[ones, ones], (np.r_[self.a, self.b], np.r_[self.b, self.a])), shape=(self.N, self.N))
        A.sort_indices()
        return A

    def _block_products(self, L, Rm, want_missing=False, S_exist=None):
        """Values of (L @ Rm) at the existing edges; optionally each row's best missing partner per subset."""
        out = np.zeros(len(self.a))
        rows, cols = self.a, self.b  # sorted by a (from_matrices); the products are symmetric, one orientation suffices
        idx = np.arange(len(self.a))
        rptr = np.searchsorted(rows, np.arange(self.N + 1))
        ma, mb, mt = [], [], []
        L = L.tocsr()
        for lo in range(0, self.N, BLOCK):
            hi = min(self.N, lo + BLOCK)
            P = (L[lo:hi] @ Rm).tocsr()
            e0, e1 = rptr[lo], rptr[hi]
            if e1 > e0:
                v = pair_lookup(P, rows[e0:e1] - lo, cols[e0:e1])
                out[idx[e0:e1]] = v  # symmetric: both orientations give the same value
            if want_missing:
                Pc = P.tocoo()
                rr, cc, vv = Pc.row.astype(np.int64) + lo, Pc.col.astype(np.int64), Pc.data
                ok = (self.sub[rr] != self.sub[cc]) & (vv > 0)
                rr, cc, vv = rr[ok], cc[ok], vv[ok]
                ex = pair_lookup(S_exist, rr, cc) > 0
                rr, cc, vv = rr[~ex], cc[~ex], vv[~ex]
                if len(rr):
                    key = rr * (int(self.sub.max()) + 1) + self.sub[cc]
                    o = np.lexsort((-vv, key))
                    key, rr, cc, vv = key[o], rr[o], cc[o], vv[o]
                    first = np.r_[True, key[1:] != key[:-1]]
                    ma.append(rr[first]); mb.append(cc[first]); mt.append(vv[first])
        if want_missing:
            cat = (lambda x: np.concatenate(x) if x else np.zeros(0))
            return out, cat(ma).astype(np.int64), cat(mb).astype(np.int64), cat(mt)
        return out

    @property
    def emb(self):
        def f():
            A = self.adjacency()
            return self._block_products(A, A)
        return self._cached("emb", f)

    @property
    def deg(self):
        return np.bincount(np.r_[self.a, self.b], minlength=self.N)

    @property
    def ovl(self):
        def f():
            emb, deg = self.emb, self.deg
            den = (deg[self.a] - 1) + (deg[self.b] - 1) - emb
            return np.where(den > 0, emb / np.maximum(den, 1), 0.0)
        return self._cached("ovl", f)

    def poss_of(self, a, b):
        out = np.empty(len(a))
        for lo in range(0, len(a), 2_000_000):
            hi = min(len(a), lo + 2_000_000)
            out[lo:hi] = (self.R[a[lo:hi]].astype(np.float64) * self.R[b[lo:hi]]).sum(axis=1)
        return out

    @property
    def poss(self):
        return self._cached("poss", lambda: self.poss_of(self.a, self.b))

    @property
    def s(self):
        return np.clip(self.w / np.maximum(self.poss, 1), 0, 1)

    def _S(self):
        s = self.s
        S = sp.csr_matrix((np.r_[s, s], (np.r_[self.a, self.b], np.r_[self.b, self.a])), shape=(self.N, self.N))
        S.sort_indices()
        return S

    def _tc_all(self):
        S = self._S()
        sig = np.asarray(S.sum(axis=1)).ravel()
        Rm = (sp.diags(1.0 / np.maximum(sig, 1e-12)) @ S).tocsr()
        t_e, ma, mb, mt = self._block_products(S, Rm, want_missing=True, S_exist=S)
        return t_e, ma, mb, mt

    @property
    def tc(self):
        return self._cached("tc", lambda: self._tc_all())[0]

    def missing_tc(self):
        """Missing cross-subset pairs (a < b) that are each other's best missing partner in the other's subset:
        returns a, b, t, poss."""
        def f():
            _, ma, mb, mt = self._cached("tc", lambda: self._tc_all())
            if len(ma) == 0:
                z = np.zeros(0)
                return z.astype(np.int64), z.astype(np.int64), z, z
            M = self.N
            k1 = ma * M + mb
            k2 = mb * M + ma
            s1 = np.sort(k1)
            p = np.clip(np.searchsorted(s1, k2), 0, len(s1) - 1)
            sel = (s1[p] == k2) & (ma < mb)
            a, b, t = ma[sel], mb[sel], mt[sel]
            return a, b, t, self.poss_of(a, b)
        return self._cached("missing_tc", f)

    # ------------------------------------------------------------------ structure (merge-step ideas)
    def subset_pos(self):
        """node -> its column index within its own subset alignment (nodes are contiguous per subset)."""
        first = np.r_[0, np.flatnonzero(np.diff(self.sub)) + 1]
        start = np.zeros(int(self.sub.max()) + 1, dtype=np.int64)
        start[self.sub[first]] = first
        return np.arange(self.N) - start[self.sub]

    @property
    def chain_offset(self):
        """Per edge (a, b): how far b's column is from where the heaviest order-preserving chain of edges between
        the two subsets puts a's partner (columns; interpolated between chain points). Two subsets' columns can only
        align in increasing order, so edges far off the chain cannot all be right. Chain: heaviest strictly
        increasing set of edges with k >= 2 (weighted longest increasing subsequence)."""
        def f():
            pos = self.subset_pos()
            nsub = int(self.sub.max()) + 1
            key = self.sub[self.a] * nsub + self.sub[self.b]
            order = np.argsort(key, kind="stable")
            out = np.zeros(len(self.a))
            for idx in np.split(order, np.flatnonzero(np.diff(key[order])) + 1):
                pa, pb = pos[self.a[idx]], pos[self.b[idx]]
                strong = self.k[idx] >= 2
                if strong.sum() < 2:
                    continue
                ca, cb = heaviest_chain(pa[strong], pb[strong], self.w[idx][strong])
                out[idx] = np.abs(pb - np.interp(pa, ca, cb))
            return out
        return self._cached("chain_offset", f)

    @property
    def best_ratio(self):
        """Per edge (a, b): w over the heaviest edge from a into b's subset, and over the heaviest edge from b into
        a's subset (1, 1: each is the other's best partner there, as in a reciprocal best hit)."""
        def f():
            out = []
            for x, y in ((self.a, self.b), (self.b, self.a)):
                key = x * (int(self.sub.max()) + 1) + self.sub[y]
                _, inv = np.unique(key, return_inverse=True)
                top = np.zeros(inv.max() + 1)
                np.maximum.at(top, inv, self.w)
                out.append(self.w / top[inv])
            return out[0], out[1]
        return self._cached("best_ratio", f)

    @property
    def diag_support(self):
        """Per edge (a, b): how many of (a-1, b-1) and (a+1, b+1) are edges too, within the same two subsets."""
        def f():
            A = self.adjacency()
            out = np.zeros(len(self.a))
            for d in (-1, 1):
                a2, b2 = self.a + d, self.b + d
                ok = (a2 >= 0) & (a2 < self.N) & (b2 >= 0) & (b2 < self.N)
                ok[ok] &= (self.sub[a2[ok]] == self.sub[self.a[ok]]) & (self.sub[b2[ok]] == self.sub[self.b[ok]])
                hit = np.zeros(len(self.a))
                hit[ok] = pair_lookup(A, a2[ok], b2[ok]) > 0
                out += hit
            return out
        return self._cached("diag_support", f)

    @property
    def occupancy(self):
        """node -> fraction of its subset's sequences with a residue in that column (needs self.subset_paths)."""
        def f():
            from .score import read_fasta
            if not getattr(self, "subset_paths", None):
                raise SystemExit("occupancy needs the subset alignments (the hook sets them)")
            occ, base = np.zeros(self.N), 0
            for path in self.subset_paths:
                rows = list(read_fasta(path).values())
                M = np.frombuffer("".join(rows).encode(), dtype=np.uint8).reshape(len(rows), -1)
                occ[base:base + M.shape[1]] = ((M != ord("-")) & (M != ord("."))).mean(axis=0)
                base += M.shape[1]
            assert base == self.N, "subset alignments do not match the graph"
            return occ
        return self._cached("occupancy", f)

    @property
    def backbone_em(self):
        """Per edge: posterior that it is true, with each backbone treated as a noisy annotator (one-coin
        Dawid-Skene, EM): backbone j votes for an edge it holds both columns of with probability p_j if the edge
        is true and q_j if not. Backbones that agree with the consensus get more say than k's equal votes."""
        def f():
            if self.kb is None or getattr(self, "cover", None) is None:
                raise SystemExit("backbone_em needs per-backbone votes: rebuild the graph cache")
            # edges with the same votes and the same exposed backbones share a posterior: fit on the distinct patterns
            pat, inv, cnt = np.unique(np.column_stack([self.cover[self.a] & self.cover[self.b], self.kb]), axis=0,
                                      return_inverse=True, return_counts=True)
            bits = np.arange(self.B, dtype=np.int64)
            X = ((pat[:, :1] >> bits) & 1).astype(bool)
            V = ((pat[:, 1:] >> bits) & 1).astype(bool)
            XV, XN, cnt = (X & V).astype(float), (X & ~V).astype(float), cnt.astype(float)
            pi, p, q = 0.5, np.full(self.B, 0.8), np.full(self.B, 0.3)
            for _ in range(200):
                lt = np.log(pi) + XV @ np.log(p) + XN @ np.log(1 - p)
                lf = np.log(1 - pi) + XV @ np.log(q) + XN @ np.log(1 - q)
                post = 1.0 / (1.0 + np.exp(np.clip(lf - lt, -50, 50)))
                wt, wf = cnt * post, cnt * (1 - post)
                pi = float(np.clip(wt.sum() / cnt.sum(), 1e-3, 1 - 1e-3))
                p = np.clip((XV.T @ wt) / np.maximum(X.T @ wt, 1e-9), 1e-3, 1 - 1e-3)
                q = np.clip((XV.T @ wf) / np.maximum(X.T @ wf, 1e-9), 1e-3, 1 - 1e-3)
            self.notes["backbone_em"] = {"pi": round(pi, 4), "p": np.round(p, 3).tolist(), "q": np.round(q, 3).tolist(),
                                         "patterns": int(len(pat))}
            return post[inv.ravel()]
        return self._cached("backbone_em", f)

    def _opal(self):
        from .evidence import opal_pair_weights
        return self._cached("opal", lambda: opal_pair_weights(self))

    @property
    def opal_pairs(self):
        """Per edge: letter pairs that an OPAL alignment of the edge's two subset alignments puts in one column
        (graphmods/evidence.py; needs self.subset_paths and $OPAL_JAR)."""
        return self._opal()[0]

    def opal_missing(self):
        """Column pairs OPAL aligns that have no edge: a, b, letter pairs."""
        return self._opal()[1:]

    # ------------------------------------------------------------------ truth (ceilings only)
    def _truth(self):
        """T[a, b] = number of residue pairs of columns a and b that the reference alignment puts in one column.
        Needs self.subset_paths (MAGUS's subset alignments, in its node order) and self.reference, which the hook
        sets from $GRAPHMODS_REFERENCE; only the ceiling strategies use it."""
        from .score import read_fasta
        if not getattr(self, "reference", None) or not getattr(self, "subset_paths", None):
            raise SystemExit("ceiling strategies need the reference alignment ($GRAPHMODS_REFERENCE; replay sets it)")
        refcol = {}
        width = 0
        for name, row in read_fasta(self.reference).items():
            r = np.frombuffer(row.encode(), dtype=np.uint8)
            refcol[name] = np.flatnonzero((r != ord("-")) & (r != ord(".")))
            width = len(r)
        rows, cols, base = [], [], 0
        for path in self.subset_paths:
            aln = read_fasta(path)
            w = 0
            for name, row in aln.items():
                r = np.frombuffer(row.encode(), dtype=np.uint8)
                pos = np.flatnonzero((r != ord("-")) & (r != ord(".")))
                ref = refcol[name]
                assert len(pos) == len(ref), "sequence {} differs between subset and reference".format(name)
                rows.append(base + pos)
                cols.append(ref)
                w = len(r)
            base += w
        assert base == self.N, "subset alignments ({} columns) do not match the graph ({} nodes)".format(base, self.N)
        rows, cols = np.concatenate(rows), np.concatenate(cols)
        X = sp.csr_matrix((np.ones(len(rows), dtype=np.int64), (rows, cols)), shape=(self.N, width))
        return (X @ X.T).tocsr()

    @property
    def true_pairs(self):
        """Per existing cross-subset edge: residue pairs the reference aligns (0 = a false edge)."""
        return self._cached("true_pairs", lambda: pair_lookup(self._truth(), self.a, self.b))

    @property
    def true_w(self):
        """Per existing cross-subset edge: of the residue pairs the backbones aligned across it (the pairs w counts),
        those the reference also aligns. Needs self.context and self.backbone_files, which the hook sets."""
        from .oracle import backbone_true_pairs
        if not getattr(self, "reference", None) or getattr(self, "context", None) is None:
            raise SystemExit("ceiling strategies need the reference alignment ($GRAPHMODS_REFERENCE; replay sets it)")
        return self._cached("true_w", lambda: backbone_true_pairs(self.context, self.backbone_files,
                                                                  self.reference, self))

    def true_missing(self):
        """Cross-subset column pairs with true residue pairs but no MAGUS edge: a, b, true pair count."""
        def f():
            T = sp.triu(self._truth(), k=1).tocoo()
            cross = self.sub[T.row] != self.sub[T.col]
            a, b, t = T.row[cross].astype(np.int64), T.col[cross].astype(np.int64), T.data[cross].astype(np.float64)
            have = pair_lookup(self.adjacency(), a, b) > 0
            return a[~have], b[~have], t[~have]
        return self._cached("true_missing", f)

    def posterior(self, kind):
        """P(true | k, n) under a two-component zero-truncated mixture fitted to this dataset's (k, n) table."""
        from . import mixture

        def f():
            K, Nn, C, inv = mixture.table(self.k, self.n)
            fit, r = mixture.fit_mixture(K, Nn, C, kind)
            self.notes["fit_" + kind] = fit
            return r[inv]
        return self._cached("post_" + kind, f)

    # ------------------------------------------------------------------ output
    def to_csr(self, new_w, added=None):
        """MAGUS matrix with the cross edges replaced by new_w (0 = deleted) plus optional added edges (a, b, w)."""
        new_w = np.asarray(new_w, dtype=float)
        assert new_w.shape == self.w.shape, "a strategy must return one weight per existing cross edge"
        integer = added is None and np.all((new_w == 0) | (new_w == self.w))
        scale = 1 if integer else 1000
        nw = np.rint(new_w * scale).astype(np.int64)
        keep = nw > 0
        ra, rb, rv = self.a[keep], self.b[keep], nw[keep]
        n_add = 0
        if added is not None and len(added[0]):
            aa, ab, aw = (np.asarray(x) for x in added)
            av = np.rint(aw * scale).astype(np.int64)
            ok = av > 0
            ra, rb, rv = np.r_[ra, aa[ok]], np.r_[rb, ab[ok]], np.r_[rv, av[ok]]
            n_add = int(ok.sum())
        o_r, o_c, o_v = self.other
        rows = np.r_[o_r, ra, rb]
        cols = np.r_[o_c, rb, ra]
        vals = np.r_[o_v * scale, rv, rv]
        M = sp.csr_matrix((vals, (rows, cols)), shape=(self.N, self.N))
        M.sort_indices()
        M.indices = M.indices.astype(np.int32)
        info = {"edges": int(len(self.w)), "kept_edges": int(keep.sum()), "added_edges": n_add, "weight_scale": scale}
        return M, info


def fingerprint(paths):
    h = hashlib.sha256()
    for p in paths:
        st = os.stat(p)
        h.update(f"{os.path.basename(p)}:{st.st_size}\n".encode())
    return h.hexdigest()[:16]
