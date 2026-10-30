# AI-assisted (Claude), exploration code for CS581 project
"""Repair the subset alignments before the merge: a subset column whose residues the backbones put in different
columns is split, when at least min_apart more backbones say apart than together (graphmods/repair.py); then
MAGUS's merge of the repaired subsets with the same backbones (with K: cut at k >= K, as strict_k). The only
strategy here that can change the subset alignments' own residue pairs, i.e. lower the floor of graphmods.spsplit."""
from graphmods import merge as M
from graphmods.repair import repair_files

FAMILY = "repair"
GRID = [{"min_apart": 2}, {"min_apart": 3}, {"min_apart": 2, "K": 4}]


def merge(job, min_apart, K=0):
    subsets, split = repair_files(job.subsets, job.backbones, job.path("repaired"), min_apart)
    if K:
        M.magus_merge(job, job.out, subsets=subsets, strategy="strict_k", params={"K": K})
    else:
        M.magus_merge(job, job.out, subsets=subsets)
    return {"columns_split": split}
