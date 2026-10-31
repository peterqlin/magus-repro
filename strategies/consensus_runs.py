# AI-assisted (Claude), exploration code for CS581 project
"""Consensus of independent merges: the 40 backbones of more_backbones (r=40, m=200; shared with it) are split into
4 groups of 10 and each group is merged with MAGUS on its own. The final merge uses all 40 backbones, with each
edge weighted by the fraction f of the 4 group merges that align its two columns (mode=weight: w * f) or kept only
when f >= t (mode=filter). The group merges are shared by the settings and charged to each (feature group_merges);
the backbone build is left out of merge_s, as in more_backbones."""
import json
import os
import time

from graphmods import merge as M

FAMILY = "iterate"
GRID = [{"mode": "weight"}, {"mode": "filter", "t": 0.5}, {"mode": "filter", "t": 0.75}]


def group_merges(job, paths, r, m, groups):
    shared = M.shared_dir(job, "_consensus_r{}_m{}_g{}".format(r, m, groups))
    done = os.path.join(shared, "build.json")
    outs = [os.path.join(shared, "group_{}.fasta".format(i)) for i in range(groups)]
    built_now = not os.path.exists(done)
    if built_now:
        os.makedirs(shared, exist_ok=True)
        t0 = time.time()
        for i, out in enumerate(outs):
            if not os.path.exists(out):  # resumes after a time limit
                M.magus_merge(job, out + ".tmp", backbones=paths[i::groups], name="group_{}".format(i))
                os.replace(out + ".tmp", out)
        json.dump({"group_s": round(time.time() - t0, 1)}, open(done, "w"))
    return outs, json.load(open(done))["group_s"], built_now


def merge(job, mode, t=0.5, r=40, m=200, groups=4):
    paths, backbone_s, backbones_now = M.magus_backbones(job, r, m)
    outs, group_s, built_now = group_merges(job, paths, r, m, groups)
    params = {"mode": "weight"} if mode == "weight" else {"mode": "filter", "t": t, "factor": 0}
    M.magus_merge(job, job.out, backbones=paths, strategy="_from_alignment", params=params, name="final",
                  env={"GRAPHMODS_ALIGNMENTS": os.pathsep.join(outs)})
    here = {}  # computed in this run: subtracted from merge_s; feature_cold_s is what is charged back
    if backbones_now:
        here["backbones"] = backbone_s
    if built_now:
        here["group_merges"] = group_s
    return {"backbone_s": backbone_s, "group_s": group_s, "feature_s": here, "feature_cold_s": {"group_merges": group_s}}
