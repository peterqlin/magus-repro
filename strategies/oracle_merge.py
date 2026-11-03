# AI-assisted (Claude), exploration code for CS581 project
"""Ceiling, whole merge: the subset alignments merged by the reference itself. Per subset, an order-preserving
assignment of its columns to reference columns (each used at most once) that puts the most residues in their own
reference column (dynamic programming, as aligning the subset's columns to the reference's); unassigned columns get
columns of their own. Columns of different subsets assigned to the same reference column are merged. What merging
these fixed subset alignments can reach, without MAGUS's graph, MCL or trace. Not a method: it reads the reference
($GRAPHMODS_REFERENCE)."""
import collections
import os

import numpy as np

from graphmods import merge as M

FAMILY = "ceiling"
GRID = [{}]


def ref_width(ref):
    return 1 + max(int(c[-1]) for c in ref.values() if len(c))


def assign(votes, width, sid):
    """Order-preserving column -> reference column assignment maximising residues placed in their own column."""
    n = len(votes)
    dp = np.zeros((n + 1, width + 1), dtype=np.int32)
    for c in range(1, n + 1):
        v = np.zeros(width + 1, dtype=np.int32)
        for t, k in votes[c - 1].items():
            v[t + 1] = k
        take = np.empty(width + 1, dtype=np.int32)
        take[0] = 0
        take[1:] = dp[c - 1, :-1] + v[1:]
        dp[c] = np.maximum.accumulate(np.maximum(dp[c - 1], take))
    keys, j = [None] * n, width
    for c in range(n, 0, -1):  # trace back
        while j > 0 and dp[c, j] == dp[c, j - 1]:
            j -= 1
        if j > 0 and votes[c - 1].get(j - 1, 0) > 0 and dp[c, j] == dp[c - 1, j - 1] + votes[c - 1][j - 1]:
            keys[c - 1] = (j - 1, 0)
            j -= 1
    last = -1
    for c in range(n):  # unassigned columns: own column right after the previous assigned one
        if keys[c] is None:
            keys[c] = (last, 1, sid, c)
        else:
            last = keys[c][0]
    return keys


def merge(job):
    ref = {}
    for name, row in M.read_fasta(os.environ["GRAPHMODS_REFERENCE"]).items():
        r = np.frombuffer(row.upper().encode(), dtype=np.uint8)
        ref[name] = np.flatnonzero((r != ord("-")) & (r != ord(".")))
    width_ref = ref_width(ref)
    placed = []  # per subset: (alignment, [key per column])
    for path in job.subsets:
        aln = M.read_fasta(path)
        width = len(next(iter(aln.values())))
        votes = [collections.Counter() for _ in range(width)]
        for name, row in aln.items():
            r = np.frombuffer(row.upper().encode(), dtype=np.uint8)
            cols = np.flatnonzero((r != ord("-")) & (r != ord(".")))
            for c, t in zip(cols.tolist(), ref[name].tolist()):
                votes[c][t] += 1
        keys = assign(votes, width_ref, len(placed))
        placed.append((aln, keys))
    order = sorted({k for _, keys in placed for k in keys})
    index = {k: i for i, k in enumerate(order)}
    out = {}
    for aln, keys in placed:
        pos = np.array([index[k] for k in keys])
        for name, row in aln.items():
            line = np.full(len(order), ord("-"), dtype=np.uint8)
            line[pos] = np.frombuffer(row.encode(), dtype=np.uint8)
            out[name] = line.tobytes().decode()
    M.write_fasta(out, job.path("oracle.fasta"))
    M.finish(job, job.path("oracle.fasta"))
