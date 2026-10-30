# AI-assisted (Claude), exploration code for CS581 project
"""Repair subset alignments with the backbones before merging: split a subset column whose residues the backbones
put in different columns.

For every subset column and every backbone, the column's residues from the backbone's sequences either share one
backbone column or not. Per column, sequences are joined when more backbones put them together than apart; each
group but the largest (which also keeps the sequences no backbone holds) becomes a column of its own, right after
the original, when at least min_apart more backbones put it apart from the largest group than together. A merge
can not change a subset alignment's own residue pairs (graphmods/spsplit.py: the floor), so this is the one step
here that can lower the floor.
"""
import collections
import os

import numpy as np

from .score import read_fasta, write_fasta

GAPS = (ord("-"), ord("."))


def _residues(row):
    r = np.frombuffer(row.encode(), dtype=np.uint8)
    return np.flatnonzero((r != GAPS[0]) & (r != GAPS[1]))


class _Union:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def join(self, x, y):
        self.p[self.find(x)] = self.find(y)


def votes(sub, backbones):
    """{column: {(u, v): (set of backbones with u, v together, set with them apart)}} for the subset alignment `sub`
    (name -> row): every pair of its sequences with a residue in the column that a backbone holds both of."""
    scol = {n: _residues(r) for n, r in sub.items()}
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: (set(), set())))
    for j, bb in enumerate(backbones):
        held = sorted(n for n in bb if n in sub)
        bcol = {n: _residues(bb[n]) for n in held}
        for i, u in enumerate(held):
            for v in held[i + 1:]:
                cols, iu, iv = np.intersect1d(scol[u], scol[v], assume_unique=True, return_indices=True)
                same = bcol[u][iu] == bcol[v][iv]
                for c, s in zip(cols.tolist(), same.tolist()):
                    out[c][(u, v)][0 if s else 1].add(j)
    return out


def repair(sub, backbones, min_apart):
    """The repaired subset alignment (name -> row) and the number of columns split off."""
    names = list(sub)
    rows = {n: np.frombuffer(sub[n].encode(), dtype="S1").copy() for n in names}
    width = len(rows[names[0]])
    new_cols = {}  # column -> [list of names moved to each new column after it]
    for c, pairs in votes(sub, backbones).items():
        if not any(a for _, a in pairs.values()):
            continue
        uf = _Union()
        for (u, v), (t, a) in pairs.items():
            uf.find(u), uf.find(v)
            if len(t) > len(a):
                uf.join(u, v)
        groups = collections.defaultdict(list)
        for x in list(uf.p):
            groups[uf.find(x)].append(x)
        if len(groups) < 2:
            continue
        main = max(groups.values(), key=len)
        mainset = set(main)
        moved = []
        for g in groups.values():
            if g is main:
                continue
            gs = set(g)
            t, a = set(), set()
            for (u, v), (tt, aa) in pairs.items():
                if (u in gs and v in mainset) or (v in gs and u in mainset):
                    t |= tt
                    a |= aa
            if len(a) - len(t) >= min_apart:
                moved.append(g)
        if moved:
            new_cols[c] = moved
    out_rows = {n: [] for n in names}
    for c in range(width):
        moved = new_cols.get(c, [])
        movedset = set(x for g in moved for x in g)
        for n in names:
            out_rows[n].append(b"-" if n in movedset else rows[n][c])
        for g in moved:
            gs = set(g)
            for n in names:
                out_rows[n].append(rows[n][c] if n in gs else b"-")
    return {n: b"".join(out_rows[n]).decode() for n in names}, sum(len(m) for m in new_cols.values())


def repair_files(subset_paths, backbone_paths, out_dir, min_apart):
    """Write repaired copies of the subset alignments to out_dir (same file names); returns (paths, columns split)."""
    backbones = [{k: v.upper() for k, v in read_fasta(p).items()} for p in backbone_paths]
    paths, split = [], 0
    os.makedirs(out_dir, exist_ok=True)
    for p in subset_paths:
        sub = {k: v.upper() for k, v in read_fasta(p).items()}
        fixed, n = repair(sub, backbones, min_apart)
        out = os.path.join(out_dir, os.path.basename(p))
        write_fasta(fixed, out)
        paths.append(out)
        split += n
    return paths, split
