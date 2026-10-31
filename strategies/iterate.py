# AI-assisted (Claude), exploration code for CS581 project
"""Iterated merge: MAGUS's merge, then again on the same graph with the edges the previous alignment did not use
(its two columns in different output columns) down-weighted (mode=filter: times factor) or the ones it used
boosted (mode=boost: times 1 + lam), for `rounds` merges in all. The graph sees its own clustering's verdict, so
MCL can settle clusters the first pass split or joined on weak edges."""
import os

from graphmods import merge as M

FAMILY = "iterate"
GRID = [{"mode": "filter", "factor": 0}, {"mode": "filter", "factor": 0.25}, {"mode": "boost", "lam": 1},
        {"mode": "filter", "factor": 0.25, "rounds": 3}]


def merge(job, mode, factor=0, lam=1, rounds=2):
    prev = M.magus_merge(job, job.path("pass1.fasta"), name="pass1")
    params = {"mode": "filter", "t": 1, "factor": factor} if mode == "filter" else {"mode": "boost", "lam": lam}
    for r in range(2, rounds + 1):
        out = job.out if r == rounds else job.path("pass{}.fasta".format(r))
        M.magus_merge(job, out, strategy="_from_alignment", params=params, name="pass{}".format(r),
                      env={"GRAPHMODS_ALIGNMENTS": os.path.abspath(prev)})
        prev = out
    return {"rounds": rounds}
