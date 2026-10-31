# AI-assisted (Claude), exploration code for CS581 project
"""Extra evidence for the graph from independent aligners: alignments of every pair of subset alignments with their
columns kept fixed, by OPAL (profile-profile, PASTA's merger for DNA/RNA), MAFFT (--merge with the two as sub-MSAs) or
Clustal Omega (profile-profile).

The aligner keeps each input alignment's columns, so every output column holds at most one column of each subset; a column
holding column x of subset s and column y of subset t aligns count_s[x] * count_t[y] letter pairs (count = residues
in the column): letter pairs, as MAGUS's weight counts them, but over every sequence rather than a backbone's.
pair_weights returns that count for every existing cross-subset edge (0 if the aligner does not put the two columns
together), and the column pairs it aligns that MAGUS has no edge for (a, b, count). Runs S * (S - 1) / 2 jobs for S
subsets, in parallel threads (MAGUS's -np). OPAL jar: $OPAL_JAR (the image sets it); heap per job: $OPAL_XMX (default
4g; a job that fails is retried once with twice the heap). MAFFT and Clustal Omega are MAGUS's bundled binaries.
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


def _run_opal(a, b, out, tmp):
    xmx = os.environ.get("OPAL_XMX", "4g")
    jar = os.environ.get("OPAL_JAR", "/opt/opal/opal.jar")
    for heap in (xmx, str(2 * int(xmx[:-1])) + xmx[-1]):
        with open(os.devnull, "w") as dn:
            r = subprocess.run(["java", "-Xmx" + heap, "-jar", jar, "--in", a, "--in2", b, "--out", out,
                                "--align_method", "profile", "--quiet"], stdout=dn, stderr=dn)
        if r.returncode == 0:
            return
    r.check_returncode()


def _run_mafft(a, b, out, tmp):
    from .merge import tool
    sa, sb = read_fasta(a), read_fasta(b)
    inp, tab = out + ".in", out + ".table"
    with open(inp, "w") as f:
        for k, v in list(sa.items()) + list(sb.items()):
            f.write(">{}\n{}\n".format(k, v))
    with open(tab, "w") as f:
        f.write(" ".join(str(i + 1) for i in range(len(sa))) + "\n")
        f.write(" ".join(str(len(sa) + i + 1) for i in range(len(sb))) + "\n")
    with open(out, "w") as f, open(os.devnull, "w") as dn:
        subprocess.run([tool("mafft"), "--merge", tab, "--thread", "1", "--anysymbol", "--quiet", inp], stdout=f,
                       stderr=dn, check=True)
    os.remove(inp)
    os.remove(tab)


def _run_clustal(a, b, out, tmp):
    from .merge import tool
    seqtype = "RNA" if "U" in "".join(read_fasta(a).values()).upper() else "DNA"
    with open(os.devnull, "w") as dn:
        subprocess.run([tool("clustal"), "--p1", a, "--p2", b, "--is-profile", "--seqtype", seqtype, "-o", out,
                        "--outfmt=fa", "--force", "--threads", "1"], stdout=dn, stderr=dn, check=True)


TOOLS = {"opal": _run_opal, "mafft": _run_mafft, "clustal": _run_clustal}


def opal_pair_weights(g):
    return pair_weights(g, "opal")


def pair_weights(g, aligner="opal"):
    if not getattr(g, "subset_paths", None):
        raise SystemExit("pairwise evidence needs the subset alignments (the hook sets them)")
    run_one = TOOLS[aligner]
    subs = [{k: v.upper() for k, v in read_fasta(p).items()} for p in g.subset_paths]
    width = [len(next(iter(s.values()))) for s in subs]
    base = np.r_[0, np.cumsum(width)[:-1]]
    assert sum(width) == g.N, "subset alignments do not match the graph"
    counts = []
    for s in subs:
        M = np.frombuffer("".join(s.values()).encode(), dtype=np.uint8).reshape(len(s), -1)
        counts.append(((M != GAPS[0]) & (M != GAPS[1])).sum(axis=0).astype(np.float64))
    pairs = [(s, t) for s in range(len(subs)) for t in range(s + 1, len(subs))]
    tmp = tempfile.mkdtemp(prefix=aligner + "_", dir=g.cache_dir or None)

    def one(st):
        s, t = st
        out = os.path.join(tmp, "{}_{}.fasta".format(s, t))
        run_one(g.subset_paths[s], g.subset_paths[t], out, tmp)
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
    on_edges = pair_lookup(W, g.a, g.b)
    lo, hi = np.minimum(rows, cols), np.maximum(rows, cols)
    missing = pair_lookup(g.adjacency(), lo, hi) == 0
    g.notes[aligner + "_pairs"] = {"jobs": len(pairs), "edges": int(len(vals)), "edges_in_graph": int((on_edges > 0).sum())}
    return on_edges, lo[missing], hi[missing], vals[missing]
