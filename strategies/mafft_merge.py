# AI-assisted (Claude), exploration code for CS581 project
"""Whole merge, MAFFT: `mafft --merge` on the subset alignments as fixed sub-MSAs (MAFFT's default progressive
strategy; MAFFT builds its own guide tree). Replaces MAGUS's graph, MCL and trace; backbones unused."""
from graphmods import merge as M

FAMILY = "whole"
GRID = [{}]


def merge(job):
    seqs, table = {}, []
    for p in job.subsets:
        aln = M.read_fasta(p)
        table.append(" ".join(str(len(seqs) + i + 1) for i in range(len(aln))))
        seqs.update(aln)
    inp, tab, out = job.path("input.fasta"), job.path("subMSAtable"), job.path("mafft.fasta")
    M.write_fasta(seqs, inp)
    open(tab, "w").write("\n".join(table) + "\n")
    with open(out, "w") as f:
        M.run([M.tool("mafft"), "--merge", tab, "--thread", job.threads, "--anysymbol", "--quiet", inp], stdout=f,
              log=job.path("tool.log"))
    M.finish(job, out)
