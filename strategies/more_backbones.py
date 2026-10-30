# AI-assisted (Claude), exploration code for CS581 project
"""More evidence: MAGUS's merge on the same subset alignments with a fresh set of r backbones of m sequences each
(MAGUS builds them: m / 25 random sequences per subset, MAFFT L-INS-i), instead of the run's own 10 x 200; then the
graph is optionally cut at k >= cutoff * r (as strict_k) before MAGUS's MCL and trace. r=10, m=200, cutoff=0 is a
fresh draw of MAGUS's own design, the control for the others. The backbones of one (r, m) are built once per dataset
and shared by its settings; their build time is reported as backbone_s and is not part of merge_s."""
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time

from graphmods import merge as M
from graphmods.replay import MERGE_FLAGS

FAMILY = "evidence"
GRID = [{"r": r, "m": m, "cutoff": c} for r, m, c in
        [(10, 200, 0), (20, 200, 0), (40, 200, 0), (40, 100, 0), (20, 200, 0.4), (40, 200, 0.4), (40, 100, 0.4)]]


def backbones(job, r, m):
    """Build (or reuse) r backbones of m sequences for this dataset; returns (paths, seconds to build, built now)."""
    shared = os.path.join(os.path.dirname(os.path.dirname(job.out)), "_backbones_r{}_m{}".format(r, m))
    done = os.path.join(shared, "build.json")
    built_now = not os.path.exists(done)
    if built_now:
        shutil.rmtree(shared, ignore_errors=True)
        os.makedirs(shared)
        t0 = time.time()
        M.run([sys.executable, "-m", "magus.main", "-s"] + job.subsets +
              ["-d", os.path.join(shared, "work"), "-o", os.path.join(shared, "unused.fasta"), "-np", job.threads,
               "-r", r, "-m", m, "--graphclustermethod", "none", "--graphtracemethod", "naive"],
              log=os.path.join(shared, "build.log"))
        for f in glob.glob(os.path.join(shared, "work", "graph", "backbone_*_mafft.txt")):
            shutil.copy(f, shared)
        shutil.rmtree(os.path.join(shared, "work"), ignore_errors=True)
        json.dump({"backbone_s": round(time.time() - t0, 1)}, open(done, "w"))
    paths = sorted(glob.glob(os.path.join(shared, "backbone_*_mafft.txt")))
    assert len(paths) == r, "expected {} backbones in {}, found {}".format(r, shared, len(paths))
    return paths, json.load(open(done))["backbone_s"], built_now


def merge(job, r, m, cutoff):
    paths, secs, built_now = backbones(job, r, m)
    strategy = ["--strategy", "strict_k", "--param", "K={}".format(max(2, round(cutoff * r)))] if cutoff else \
        ["--strategy", "magus"]
    root = os.path.dirname(os.path.dirname(os.path.abspath(M.__file__)))
    subprocess.run([sys.executable, "-m", "graphmods.run"] + strategy +
                   ["--", "-s"] + job.subsets + ["-b"] + paths +
                   ["-d", job.path("magus"), "-o", job.out, "-np", str(job.threads)] + MERGE_FLAGS,
                   cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=open(job.path("magus.log"), "w"))
    # the build is charged like a cached feature, then left out: merge_s minus feature_s is the merge alone
    return {"backbone_s": secs, "backbones": r, "backbone_size": m,
            "feature_s": {"backbones": secs} if built_now else {}, "feature_cold_s": {}}
