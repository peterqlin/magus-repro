# AI-assisted (Claude), exploration code for CS581 project
"""Stacked: the three separate gains of the 70-dataset sweep in one merge. Optionally repair the subset alignments
first (as subset_repair, min_apart = repair, votes from the run's own backbones), add `ginsi` G-INS-i backbones of 8
random sequences per subset to the run's own (as custom_backbones), then MAGUS's merge with pairwise aligner evidence
(as aligner_evidence: `tools` at lam) and MAGUS's trace optimizer. tools=none keeps MAGUS's own graph. The settings
switch one part off at a time, so the grid also shows what each adds to the others. The G-INS-i build is shared by
the settings and left out of merge_s, as in custom_backbones."""
from graphmods import merge as M
from graphmods import registry
from graphmods.repair import repair_files

FAMILY = "stacked"
GRID = [{"repair": 7, "ginsi": 10, "tools": "opal+mafft"},
        {"repair": 0, "ginsi": 10, "tools": "opal+mafft"},
        {"repair": 7, "ginsi": 0, "tools": "opal+mafft"},
        {"repair": 7, "ginsi": 10, "tools": "none"},
        {"repair": 0, "ginsi": 10, "tools": "none"},
        {"repair": 0, "ginsi": 10, "tools": "opal"}]


def merge(job, repair, ginsi, tools, lam=0.25):
    info = {"feature_s": {}, "feature_cold_s": {}}
    backbones = list(job.backbones)
    if ginsi:
        paths, secs, secs_now = registry.load("custom_backbones").build(job, "ginsi", "random", ginsi, 8)
        backbones += paths
        info["backbone_s"] = secs
        if secs_now:  # charged like a cached feature, then left out: merge_s minus feature_s is the merge alone
            info["feature_s"]["backbones"] = secs_now
    subsets = job.subsets
    if repair:
        subsets, info["columns_split"] = repair_files(job.subsets, job.backbones, job.path("repaired"), repair)
    if tools == "none":
        M.magus_merge(job, job.out, subsets=subsets, backbones=backbones, strategy="trace",
                      params={"trace": "minclusters", "optimize": "true"})
    else:
        M.magus_merge(job, job.out, subsets=subsets, backbones=backbones, strategy="aligner_evidence",
                      params={"tools": tools, "lam": lam, "optimize": 1})
    return info
