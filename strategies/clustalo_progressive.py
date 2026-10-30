# AI-assisted (Claude), exploration code for CS581 project
"""Whole merge, Clustal Omega: profile-profile merges of the subset alignments (each one's columns kept fixed) along
a UPGMA guide tree over the subsets (6-mer distance; graphmods.merge.guide_tree). Backbones unused."""
from graphmods import merge as M

FAMILY = "whole"
GRID = [{}]


def merge(job):
    first = "".join(M.read_fasta(job.subsets[0]).values()).upper()
    seqtype = "RNA" if "U" in first else "DNA"  # Clustal Omega otherwise may guess protein

    def merge_two(a, b, out):
        M.run([M.tool("clustal"), "--p1", a, "--p2", b, "--is-profile", "--seqtype", seqtype, "-o", out, "--outfmt=fa",
               "--force", "--threads", job.threads], log=job.path("tool.log"))
    M.finish(job, M.progressive(job, merge_two))
