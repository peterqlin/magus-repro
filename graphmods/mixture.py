# AI-assisted (Claude), exploration code for CS581 project
"""Two-component zero-truncated mixture on the per-edge (k, n) table, fitted by EM per dataset (no reference).

true edges k | n ~ Bin(n, p1), false edges k | n ~ Bin(n, p0) ("binom"), or the same with beta-binomial components ("bb").
Same code as the project's earlier vote-model study (cs581/gcmvote in evanlin23/scratch), so posteriors match its results.
"""
import math

import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import betaln, gammaln


def _lchoose(n, k):
    return gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)


def _binom_logpmf_trunc(k, n, p):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return _lchoose(n, k) + k * np.log(p) + (n - k) * np.log1p(-p) - np.log1p(-(1 - p) ** n)


def _bb_logpmf_trunc(k, n, a, b):
    lp = _lchoose(n, k) + betaln(k + a, n - k + b) - betaln(a, b)
    p0 = np.exp(betaln(a, n + b) - betaln(a, b))  # P(k = 0)
    return lp - np.log1p(-np.minimum(p0, 1 - 1e-12))


def fit_mixture(K, N, C, kind="binom", iters=500, tol=1e-9):
    """EM on the aggregated table: cells (K[i], N[i]) observed C[i] times (K >= 1).
    Returns dict(pi, params of both components, loglik, bic) and the per-cell posterior P(true)."""
    K, N, C = (np.asarray(x, dtype=float) for x in (K, N, C))
    tot = C.sum()
    if kind == "binom":
        th1, th0 = [0.8], [0.15]
        logpmf = lambda th: _binom_logpmf_trunc(K, N, th[0])
    else:  # beta-binomial: (mean, log concentration)
        th1, th0 = [0.8, math.log(5.0)], [0.15, math.log(5.0)]

        def logpmf(th):
            m, s = th[0], math.exp(th[1])
            return _bb_logpmf_trunc(K, N, m * s, (1 - m) * s)
    pi, ll_old = 0.5, -np.inf
    for it in range(iters):
        l1 = np.log(pi) + logpmf(th1)
        l0 = np.log(1 - pi) + logpmf(th0)
        mx = np.maximum(l1, l0)
        lse = mx + np.log(np.exp(l1 - mx) + np.exp(l0 - mx))
        r = np.exp(l1 - lse)
        ll = float((C * lse).sum())
        pi = float(np.clip((C * r).sum() / tot, 1e-6, 1 - 1e-6))
        th1 = _mstep(K, N, C * r, th1, kind)
        th0 = _mstep(K, N, C * (1 - r), th0, kind)
        if abs(ll - ll_old) < tol * abs(ll):
            break
        ll_old = ll
    if th1[0] < th0[0]:  # label switching: component 1 = the high-vote (true) component
        th1, th0, pi, r = th0, th1, 1 - pi, 1 - r
    npar = 3 if kind == "binom" else 5
    res = {"kind": kind, "pi": pi, "p1": th1[0], "p0": th0[0], "loglik": ll, "iters": it + 1,
           "bic": -2 * ll + npar * math.log(tot), "n_edges": int(tot)}
    if kind == "bb":
        res.update(conc1=math.exp(th1[1]), conc0=math.exp(th0[1]))
    return res, r


def _mstep(K, N, Wt, th, kind):
    if Wt.sum() <= 0:
        return th
    if kind == "binom":
        f = lambda p: -(Wt * _binom_logpmf_trunc(K, N, p)).sum()
        return [minimize_scalar(f, bounds=(1e-6, 1 - 1e-6), method="bounded").x]

    def f(x):
        m, s = 1 / (1 + math.exp(-x[0])), math.exp(x[1])
        return -(Wt * _bb_logpmf_trunc(K, N, m * s, (1 - m) * s)).sum()
    x0 = [math.log(th[0] / (1 - th[0])), th[1]]
    x = minimize(f, x0, method="L-BFGS-B", bounds=[(-12, 12), (-5, 8)]).x
    return [1 / (1 + math.exp(-x[0])), x[1]]


def table(k, n):
    """Aggregate edges into (k, n) cells. Returns K, N, C and the cell index of every edge."""
    key = n.astype(np.int64) * 1000 + k
    uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    return uk % 1000, uk // 1000, cnt, inv
