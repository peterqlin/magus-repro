# AI-assisted (Claude), exploration code for CS581 project
"""Ground truth from the backbones, for the ceiling strategies (no real run has a reference).

EdgeGraph.true_pairs counts, per edge, the residue pairs of its two columns that the reference aligns over all
sequences. backbone_true_pairs instead counts, per edge, the residue pairs the backbones aligned across it (the pairs
MAGUS's weight w counts) that the reference also aligns, so true_w <= w. Backbone letters are mapped to graph nodes
exactly as MAGUS's graph_builder.backboneToAlignMap does, and the mapping is checked against MAGUS's weights.
"""
import numpy as np
import scipy.sparse as sp

from .graph import pair_lookup
from .score import read_fasta

GAPS = (ord("-"), ord("."))


def residues(seq):
    """Positions of the residues (not gaps) of an aligned row."""
    arr = np.frombuffer(seq.encode(), dtype=np.uint8)
    return np.flatnonzero((arr != GAPS[0]) & (arr != GAPS[1]))


def reference_columns(reference):
    """taxon -> the reference column of each residue, and the reference width."""
    ref = read_fasta(reference)
    return {t: residues(s) for t, s in ref.items()}, len(next(iter(ref.values())))


def backbone_letters(context, backbone, refcol):
    """(backbone column, node, reference column) of every backbone letter that MAGUS puts in the graph."""
    out_n, out_node, out_ref = [], [], []
    for taxon, rec in backbone.items():
        subset = context.taxonSubalignmentMap[taxon]
        subsetseq = context.backboneSubalignment[taxon].seq
        unaligned = context.unalignedSequences[taxon].seq
        posarray = [0] * len(unaligned)
        i = 0
        for n in range(len(subsetseq)):
            if subsetseq[n] == unaligned[i]:
                posarray[i] = n
                i += 1
                if i == len(unaligned):
                    break
        base = int(context.graph.subsetMatrixIdx[subset])
        rc = refcol[taxon]
        i = n = 0
        for c in rec.seq:
            if i == len(unaligned):
                break
            if c == unaligned[i]:
                out_n.append(n)
                out_node.append(base + posarray[i])
                out_ref.append(rc[i])
            if c.upper() == unaligned[i]:
                i += 1
            if c == c.upper() and c != ".":
                n += 1
    return np.array(out_n, dtype=np.int64), np.array(out_node, dtype=np.int64), np.array(out_ref, dtype=np.int64)


def backbone_true_pairs(context, files, reference, g):
    """Per cross edge of g: backbone-aligned residue pairs that the reference also aligns."""
    from magus.helpers import sequenceutils

    if context.backboneExtend:
        raise SystemExit("graphmods.oracle: HMM-extended backbones are not supported")
    refcol, width = reference_columns(reference)
    N = g.N
    true_total = sp.csr_matrix((N, N), dtype=np.int64)
    all_total = sp.csr_matrix((N, N), dtype=np.int64)
    for f in files:
        n, node, rc = backbone_letters(context, sequenceutils.readFromFasta(f), refcol)
        ones = np.ones(len(n), dtype=np.int64)
        At = sp.csr_matrix((ones, (n * width + rc, node)), shape=((int(n.max()) + 1) * width, N))
        A = sp.csr_matrix((ones, (n, node)), shape=(int(n.max()) + 1, N))
        true_total = true_total + (At.T @ At).tocsr()
        all_total = all_total + (A.T @ A).tocsr()
    if not np.array_equal(pair_lookup(all_total, g.a, g.b).astype(np.int64), g.w):
        raise SystemExit("graphmods.oracle: backbone letters don't reproduce MAGUS's edge weights")
    return pair_lookup(true_total, g.a, g.b)
