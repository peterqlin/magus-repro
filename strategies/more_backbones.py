# AI-assisted (Claude), exploration code for CS581 project
"""More evidence: MAGUS's merge on the same subset alignments with a fresh set of r backbones of m sequences each
(MAGUS builds them: m / 25 random sequences per subset, MAFFT L-INS-i), instead of the run's own 10 x 200; then the
graph is optionally cut at k >= cutoff * r (as strict_k) before MAGUS's MCL and trace. r=10, m=200, cutoff=0 is a
fresh draw of MAGUS's own design, the control for the others. The backbones of one (r, m) are built once per dataset
and shared by its settings; their build time is reported as backbone_s and is not part of merge_s."""
from graphmods import merge as M

FAMILY = "evidence"
GRID = [{"r": r, "m": m, "cutoff": c} for r, m, c in
        [(10, 200, 0), (20, 200, 0), (40, 200, 0), (40, 100, 0), (20, 200, 0.4), (40, 200, 0.4), (40, 100, 0.4)]]


def merge(job, r, m, cutoff):
    paths, secs, built_now = M.magus_backbones(job, r, m)
    if cutoff:
        M.magus_merge(job, job.out, backbones=paths, strategy="strict_k", params={"K": max(2, round(cutoff * r))})
    else:
        M.magus_merge(job, job.out, backbones=paths)
    # the build is charged like a cached feature, then left out: merge_s minus feature_s is the merge alone
    return {"backbone_s": secs, "backbones": r, "backbone_size": m,
            "feature_s": {"backbones": secs} if built_now else {}, "feature_cold_s": {}}
