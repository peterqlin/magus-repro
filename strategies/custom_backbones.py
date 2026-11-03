# AI-assisted (Claude), exploration code for CS581 project
"""Different backbones: r backbones of `per` sequences per subset, aligned with MAFFT `method` (linsi = MAGUS's
L-INS-i, ginsi = G-INS-i, fftns2 = FFT-NS-2), either added to the run's own backbones (mode=add) or used instead of
them (mode=replace); then MAGUS's merge. pick=random samples the sequences as MAGUS does; pick=spread picks, per
subset, sequences that fill columns few others fill (greedy cover weighted by 1 / occupancy), so gappy columns get
backbone letters. Each backbone set is built once per dataset and shared by its settings (r=20 reuses r=10's ten);
its build time is reported as backbone_s and is not part of merge_s, as in more_backbones. ginsi random add r=10, 20,
30 is a dose test, and linsi random add r=10 its control (more of MAGUS's own kind of backbone)."""
import concurrent.futures
import glob
import json
import os
import subprocess
import time

import numpy as np

from graphmods import merge as M
from graphmods.score import read_fasta, write_fasta

FAMILY = "evidence"
GRID = [{"method": "ginsi", "pick": "random", "mode": "add", "r": 10},
        {"method": "linsi", "pick": "spread", "mode": "add", "r": 10},
        {"method": "linsi", "pick": "spread", "mode": "replace", "r": 10},
        {"method": "ginsi", "pick": "spread", "mode": "add", "r": 10},
        {"method": "fftns2", "pick": "random", "mode": "add", "r": 40},
        {"method": "ginsi", "pick": "random", "mode": "add", "r": 20},
        {"method": "ginsi", "pick": "random", "mode": "add", "r": 30},
        {"method": "ginsi", "pick": "random", "mode": "replace", "r": 10},
        {"method": "linsi", "pick": "random", "mode": "add", "r": 10}]
METHODS = {"linsi": ["--localpair", "--maxiterate", "1000", "--ep", "0.123"],
           "ginsi": ["--globalpair", "--maxiterate", "1000", "--ep", "0.123"],
           "fftns2": ["--retree", "2"]}


def residue_matrix(sub):
    rows = np.frombuffer("".join(sub.values()).encode(), dtype=np.uint8).reshape(len(sub), -1)
    return (rows != ord("-")) & (rows != ord("."))


def pick_taxa(names, H, per, pick, rng):
    if pick == "random" or len(names) <= per:
        return [names[i] for i in rng.permutation(len(names))[:per]]
    gain = 1.0 / np.maximum(H.mean(axis=0), 1e-9)
    left = np.ones(H.shape[1], dtype=bool)
    chosen = [int(rng.integers(len(names)))]
    left &= ~H[chosen[0]]
    while len(chosen) < per:
        score = (H & left) @ gain + rng.random(len(names)) * 1e-6  # random tie-breaks: backbones differ
        score[chosen] = -1
        i = int(np.argmax(score))
        chosen.append(i)
        left &= ~H[i]
        if not left.any():
            left[:] = True  # every column covered: start a new cover
    return [names[i] for i in chosen]


def build(job, method, pick, r, per):
    """Backbones 1..r of (method, pick, per) for this dataset. Backbone i depends only on i, so they are built once
    in a directory shared by every r (r=20 reuses r=10's ten) and a build stopped by a time limit resumes. Returns
    (paths, build seconds of these r on job.threads threads, seconds spent building in this call)."""
    shared = M.shared_dir(job, "_custom_{}_{}_p{}".format(method, pick, per))
    out = lambda i: os.path.join(shared, "backbone_{}_mafft.txt".format(i + 1))
    todo = [i for i in range(r) if not os.path.exists(out(i))]
    t_call = time.time()
    if todo:
        os.makedirs(shared, exist_ok=True)
        subs = [{k: v.upper() for k, v in read_fasta(p).items()} for p in job.subsets]
        mats = [(list(sub), residue_matrix(sub)) for sub in subs]
        mafft = M.tool("mafft")

        def one(i):
            t0 = time.time()
            rng = np.random.default_rng(i)
            seqs = {}
            for sub, (names, H) in zip(subs, mats):
                for t in pick_taxa(names, H, per, pick, rng):
                    seqs[t] = sub[t].replace("-", "").replace(".", "")
            unaligned = os.path.join(shared, "backbone_{}_unalign.txt".format(i + 1))
            write_fasta(seqs, unaligned)
            with open(out(i) + ".tmp", "w") as f, open(os.path.join(shared, "mafft.log"), "a") as log:
                subprocess.run([mafft] + METHODS[method] + ["--quiet", "--thread", "1", "--anysymbol", unaligned],
                               stdout=f, stderr=log, check=True)
            json.dump({"s": round(time.time() - t0, 1)}, open(out(i) + ".json", "w"))
            write_fasta({k: v.upper() for k, v in read_fasta(out(i) + ".tmp").items()}, out(i))
            os.remove(out(i) + ".tmp")
            os.remove(unaligned)
        with concurrent.futures.ThreadPoolExecutor(job.threads) as ex:
            list(ex.map(one, todo))
    paths = [out(i) for i in range(r)]
    single = sum(json.load(open(p + ".json"))["s"] for p in paths if os.path.exists(p + ".json"))
    return paths, round(single / max(1, job.threads), 1), round(time.time() - t_call, 1) if todo else 0


def merge(job, method, pick, mode, r, per=8):
    paths, secs, secs_now = build(job, method, pick, r, per)
    M.magus_merge(job, job.out, backbones=(job.backbones + paths) if mode == "add" else paths)
    return {"backbone_s": secs, "backbones": len(paths) + (len(job.backbones) if mode == "add" else 0),
            "feature_s": {"backbones": secs_now} if secs_now else {}, "feature_cold_s": {}}
