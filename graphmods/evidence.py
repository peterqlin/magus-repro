# AI-assisted (Claude), exploration code for CS581 project
"""Extra evidence for the graph from an independent aligner: OPAL profile-profile alignments of every pair of subset
alignments (PASTA's merger for DNA/RNA).

OPAL keeps each input alignment's columns, so every output column holds at most one column of each subset; a column
holding column x of subset s and column y of subset t aligns count_s[x] * count_t[y] letter pairs (count = residues
in the column), the same unit as MAGUS's backbone weight. opal_pair_weights returns that count for every existing
cross-subset edge (0 if OPAL does not put the two columns together). Runs ceil(S * (S - 1) / 2) OPAL jobs, in
parallel threads (MAGUS's -np). OPAL jar: $OPAL_JAR (the image sets it); heap per job: $OPAL_XMX (default 2g).
"""
import concurrent.futures
import os
import subprocess
import tempfile

import numpy as np
import scipy.sparse as sp

from .graph import pair_lookup
from .score import read_fasta

GAPS = (ord("-"), ord("."))


def _residue_cols(row):
    r = np.frombuffer(row.encode(), dtype=np.uint8)
    return np.flatnonzero((r != GAPS[0]) & (r != GAPS[1]))


def column_map(sub_aln, out_aln, width_out):
    """out column -> column of the subset alignment it holds (-1: none), from the residues of the subset's rows."""
    m = np.full(width_out, -1, dtype=np.int64)
    for name, row in sub_aln.items():
        cs, co = _residue_cols(row), _residue_cols(out_aln[name])
        assert len(cs) == len(co), "OPAL changed sequence " + name
        m[co] = cs
    return m


def node_columns(subset_paths, alignment):
    """Graph node -> the column of `alignment` (a merge of these subset alignments, a path or a dict) that holds it;
    -1 for a subset column with no residue."""
    aln = read_fasta(alignment) if isinstance(alignment, str) else alignment
    aln = {k: v.upper() for k, v in aln.items()}
    out = []
    for path in subset_paths:
        sub = {k: v.upper() for k, v in read_fasta(path).items()}
        m = np.full(len(next(iter(sub.values()))), -1, dtype=np.int64)
        for name, row in sub.items():
            cs, co = _residue_cols(row), _residue_cols(aln[name])
            assert len(cs) == len(co), "sequence {} differs between subset and alignment".format(name)
            m[cs] = co
        out.append(m)
    return np.concatenate(out)


def _threads():
    try:
        from magus.configuration import Configs
        return max(1, int(Configs.numCores))
    except Exception:
        return os.cpu_count() or 1


def opal_pair_weights(g):
    if not getattr(g, "subset_paths", None):
        raise SystemExit("opal_pairs needs the subset alignments (the hook sets them)")
    jar = os.environ.get("OPAL_JAR", "/opt/opal/opal.jar")
    xmx = os.environ.get("OPAL_XMX", "2g")
    subs = [{k: v.upper() for k, v in read_fasta(p).items()} for p in g.subset_paths]
    width = [len(next(iter(s.values()))) for s in subs]
    base = np.r_[0, np.cumsum(width)[:-1]]
    assert sum(width) == g.N, "subset alignments do not match the graph"
    counts = []
    for s in subs:
        M = np.frombuffer("".join(s.values()).encode(), dtype=np.uint8).reshape(len(s), -1)
        counts.append(((M != GAPS[0]) & (M != GAPS[1])).sum(axis=0).astype(np.float64))
    pairs = [(s, t) for s in range(len(subs)) for t in range(s + 1, len(subs))]
    tmp = tempfile.mkdtemp(prefix="opal_", dir=g.cache_dir or None)

    def one(st):
        s, t = st
        out = os.path.join(tmp, "{}_{}.fasta".format(s, t))
        with open(os.devnull, "w") as dn:
            subprocess.run(["java", "-Xmx" + xmx, "-jar", jar, "--in", g.subset_paths[s], "--in2", g.subset_paths[t],
                            "--out", out, "--align_method", "profile", "--quiet"], stdout=dn, stderr=dn, check=True)
        aln = {k: v.upper() for k, v in read_fasta(out).items()}
        os.remove(out)
        w_out = len(next(iter(aln.values())))
        ms, mt = column_map(subs[s], aln, w_out), column_map(subs[t], aln, w_out)
        both = (ms >= 0) & (mt >= 0)
        x, y = ms[both], mt[both]
        return base[s] + x, base[t] + y, counts[s][x] * counts[t][y]

    rows, cols, vals = [], [], []
    with concurrent.futures.ThreadPoolExecutor(_threads()) as ex:
        for r, c, v in ex.map(one, pairs):
            rows.append(r); cols.append(c); vals.append(v)
    os.rmdir(tmp)
    rows, cols, vals = np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)
    W = sp.csr_matrix((np.r_[vals, vals], (np.r_[rows, cols], np.r_[cols, rows])), shape=(g.N, g.N))
    g.notes["opal_pairs"] = {"jobs": len(pairs), "opal_edges": int(len(vals)),
                             "opal_edges_in_graph": int((pair_lookup(W, g.a, g.b) > 0).sum())}
    return pair_lookup(W, g.a, g.b)
