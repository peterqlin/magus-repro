# AI-assisted (Claude), exploration code for CS581 project
"""Trace step: MAGUS's own graph, traced with MAGUS's mwtgreedy trace and/or followed by its trace optimizer
(--graphtraceoptimize true: residue-level repair of the trace). minclusters without the optimizer is MAGUS's default.
Left out after a timing run on the smoke dataset (Δerr vs MAGUS): fm +0.85, rgfast +1.73, rg +0.54, mwtsearch (same
as mwtgreedy), clustering with mlrmcl +0.25 or rg +3.47."""
FAMILY = "merge"
GRID = [{"trace": "minclusters", "optimize": "true"}, {"trace": "mwtgreedy", "optimize": "false"},
        {"trace": "mwtgreedy", "optimize": "true"}]


def apply(g, trace, optimize):
    return g.w


def magus_args(trace, optimize):
    return ["--graphtracemethod", trace, "--graphtraceoptimize", optimize]
