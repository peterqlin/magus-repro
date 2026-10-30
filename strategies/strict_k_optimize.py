# AI-assisted (Claude), exploration code for CS581 project
"""Strict support cutoff (k >= K, as strict_k) followed by MAGUS's trace optimizer (--graphtraceoptimize true)."""
import numpy as np

FAMILY = "merge"
GRID = [{"K": K} for K in (3, 4, 5)]


def apply(g, K):
    return np.where(g.k >= K, g.w, 0)


def magus_args(K):
    return ["--graphtraceoptimize", "true"]
