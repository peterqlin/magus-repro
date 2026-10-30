# AI-assisted (Claude), exploration code for CS581 project
"""Ceiling, merge: the alignment graph built from the reference instead of backbones. Every cross-subset column pair
gets weight = residue pairs the reference aligns (missing pairs are added), scaled to MAGUS's total edge weight so
the self-loop and same-subset entries keep their relative size; MCL and the trace run as in MAGUS. What a merge of
these 25 fixed subset alignments can reach with perfect evidence. Not a method: it reads the reference."""
FAMILY = "ceiling"
GRID = [{}]


def apply(g):
    t = g.true_pairs.astype(float)
    a, b, tm = g.true_missing()
    scale = g.w.sum() / max(t.sum() + tm.sum(), 1)
    return t * scale, (a, b, tm * scale)
