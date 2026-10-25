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
    def __init__(self, other, a, b, w, k, n, sub, R, B, cache_dir=None):
        self.other = other          # (rows, cols, vals): self loops and same-subset entries, kept as MAGUS built them
        self.a, self.b, self.w, self.k, self.n = a, b, w, k, n
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
    def from_matrices(cls, total, support, cover, R, sub, B, cache_dir=None):
        coo = sp.triu(total, k=1).tocoo()
        keep = sub[coo.row] != sub[coo.col]
        a, b, w = coo.row[keep].astype(np.int64), coo.col[keep].astype(np.int64), coo.data[keep].astype(np.int64)
        o = np.lexsort((b, a))
        a, b, w = a[o], b[o], w[o]
        k = pair_lookup(support, a, b).astype(np.int64)
        n = popcount(cover[a] & cover[b])
        full = total.tocoo()
        cross = sub[full.row] != sub[full.col]
        other = (full.row[~cross].astype(np.int64), full.col[~cross].astype(np.int64), full.data[~cross].astype(np.int64))
        return cls(other, a, b, w, k, n, sub, R, B, cache_dir)

    def save(self, path):
        np.savez_compressed(path, a=self.a, b=self.b, w=self.w, k=self.k, n=self.n, sub=self.sub, R=self.R,
                            B=np.array([self.B]), o_r=self.other[0], o_c=self.other[1], o_v=self.other[2])

    @classmethod
    def load(cls, path, cache_dir=None):
        z = np.load(path)
        return cls((z["o_r"], z["o_c"], z["o_v"]), z["a"], z["b"], z["w"], z["k"], z["n"], z["sub"], z["R"],
                   int(z["B"][0]), cache_dir)

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
