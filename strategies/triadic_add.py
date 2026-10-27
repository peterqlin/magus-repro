# AI-assisted (Claude), exploration code for CS581 project
"""Triadic closure, adding edges: a missing cross-subset pair (a, b) that many pairs of edges a-c, c-b point to is added.
Closure score t_ab = sum_c s_ac s_cb / sigma_c (resource allocation on normalised strengths s = w / possible pairs;
t ~ 1 for a clean clique). Added: pairs that are each other's best missing partner in the other's subset (at most one
added edge per node and subset) with t >= tau, weight lam * t * possible pairs.
On a 1000M3 replicate the mutual-best candidates number 168k; t >= 0.02 / 0.05 / 0.1 / 0.25 keeps 25.9k / 7.7k / 2.3k / 186.
Existing edges are unchanged."""
FAMILY = "network"
GRID = [{"tau": tau, "lam": lam} for tau in (0.02, 0.05, 0.1, 0.25) for lam in (0.5, 1, 2)]


def apply(g, tau, lam):
    a, b, t, poss = g.missing_tc()
    sel = t >= tau
    return g.w, (a[sel], b[sel], lam * t[sel] * poss[sel])
