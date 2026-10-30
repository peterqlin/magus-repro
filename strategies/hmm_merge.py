# AI-assisted (Claude), exploration code for CS581 project
"""Whole merge, HMM (UPP-like): an HMM built from one MAGUS backbone (hmmbuild, every column a match state) and all
sequences aligned to it with hmmalign; insertions get their own columns. Ignores the subset alignments' columns."""
from graphmods import merge as M

FAMILY = "whole"
GRID = [{}]


def merge(job):
    seqs = {}
    for p in job.subsets:
        seqs.update({k: v.replace("-", "").replace(".", "") for k, v in M.read_fasta(p).items()})
    unaligned, hmm, out = job.path("unaligned.fasta"), job.path("backbone.hmm"), job.path("hmmalign.afa")
    M.write_fasta(seqs, unaligned)
    log = job.path("tool.log")
    M.run([M.tool("hmmbuild"), "--cpu", job.threads, "--symfrac", "0.0", "--informat", "afa", hmm, job.backbones[0]],
          log=log)
    M.run([M.tool("hmmalign"), "--outformat", "afa", "-o", out, hmm, unaligned], log=log)
    M.finish(job, out)
