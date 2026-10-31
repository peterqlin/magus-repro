# AI-assisted (Claude), exploration code for CS581 project
"""Second opinion from OPAL: every pair of subset alignments is aligned with OPAL (profile-profile, PASTA's DNA
merger), and each edge gets the letter pairs OPAL puts in one column (g.opal_pairs, graphmods/evidence.py).
mode=add: w + lam * opal (opal scaled to MAGUS's total weight), with the edges OPAL does not support times drop;
mode=filter: edges OPAL does not support get weight times factor; mode=only: the OPAL weight alone; mode=boost:
w * (1 + lam) on the edges OPAL supports (MAGUS's weight scale kept); mode=pairadd: as add, but OPAL is scaled per
pair of subsets to that pair's backbone weight, not globally. K > 0 first cuts MAGUS's edges at k >= K, and chain > 0
first drops edges more than chain columns off their subset pair's chain (as chain_filter); optimize=1 also runs MAGUS's
trace optimizer (--graphtraceoptimize true, as strict_k_optimize). With missing=1,
the column pairs OPAL aligns that MAGUS has no edge for are added too (mode=only, missing=1 is a graph from OPAL
alone, backbones unused)."""
import numpy as np

FAMILY = "evidence"
GRID = [{"mode": "add", "lam": x} for x in (0.25, 0.5, 1, 2, 4)] + [{"mode": "add", "lam": 1, "missing": 1}] + \
       [{"mode": "add", "lam": 1, "drop": 0.25}, {"mode": "add", "lam": 0.5, "drop": 0}] + \
       [{"mode": "filter", "factor": f} for f in (0, 0.25)] + [{"mode": "only"}, {"mode": "only", "missing": 1}] + \
       [{"mode": "boost", "lam": x} for x in (0.5, 1, 3)] + [{"mode": "pairadd", "lam": x} for x in (0.5, 1)] + \
       [{"mode": "add", "lam": 1, "K": 3}, {"mode": "boost", "lam": 1, "K": 3}] + \
       [{"mode": "add", "lam": 0.1}, {"mode": "add", "lam": 0.25, "chain": 2}, {"mode": "add", "lam": 0.25, "optimize": 1},
        {"mode": "add", "lam": 0.25, "K": 5, "optimize": 1}]
NEEDS_INPUTS = True  # runs OPAL on the subset alignments


def magus_args(optimize=0, **_):
    return ["--graphtraceoptimize", "true"] if optimize else []


def apply(g, mode, lam=1, factor=0, missing=0, drop=1, K=0, chain=0, optimize=0):
    o = g.opal_pairs
    base = np.where(g.k >= K, g.w, 0) if K else g.w
    if chain:
        base = np.where(g.chain_offset > chain, 0, base)
    ma, mb, mw = g.opal_missing() if missing else (None, None, None)
    scale = lam * g.w.sum() / max(o.sum(), 1)
    if mode == "add":
        w = np.where(o > 0, base, base * drop) + scale * o
    elif mode == "pairadd":
        nsub = int(g.sub.max()) + 1
        key = g.sub[g.a] * nsub + g.sub[g.b]
        bw, ow = np.bincount(key, base, nsub * nsub), np.bincount(key, o, nsub * nsub)
        w = base + lam * o * (bw / np.maximum(ow, 1))[key]
    elif mode == "boost":
        return base * np.where(o > 0, 1 + lam, 1)
    elif mode == "filter":
        return np.where(o > 0, base, base * factor)
    else:
        scale = g.w.sum() / max(o.sum(), 1)  # keeps MAGUS's total weight, so the self loops keep their share
        w = o * scale
    return (w, (ma, mb, mw * scale)) if missing else w
