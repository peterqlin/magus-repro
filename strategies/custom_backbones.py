# AI-assisted (Claude), exploration code for CS581 project
"""Different backbones: r backbones of `per` sequences per subset, aligned with MAFFT `method` (linsi = MAGUS's
L-INS-i, ginsi = G-INS-i, fftns2 = FFT-NS-2), either added to the run's own backbones (mode=add) or used instead of
them (mode=replace); then MAGUS's merge. pick=random samples the sequences as MAGUS does; pick=spread picks, per
subset, sequences that fill columns few others fill (greedy cover weighted by 1 / occupancy), so gappy columns get
backbone letters. Each backbone set is built once per dataset and shared by its settings; its build time is
reported as backbone_s and is not part of merge_s, as in more_backbones."""
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
        {"method": "fftns2", "pick": "random", "mode": "add", "r": 40}]
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
    shared = M.shared_dir(job, "_custom_{}_{}_r{}_p{}".format(method, pick, r, per))
    done = os.path.join(shared, "build.json")
    built_now = not os.path.exists(done)
    if built_now:
        os.makedirs(shared, exist_ok=True)
        t0 = time.time()
        subs = [{k: v.upper() for k, v in read_fasta(p).items()} for p in job.subsets]
        mats = [(list(sub), residue_matrix(sub)) for sub in subs]
        mafft = M.tool("mafft")

        def one(i):
            out = os.path.join(shared, "backbone_{}_mafft.txt".format(i + 1))
            if os.path.exists(out):  # resumes after a time limit
                return
            rng = np.random.default_rng(i)
            seqs = {}
            for sub, (names, H) in zip(subs, mats):
                for t in pick_taxa(names, H, per, pick, rng):
                    seqs[t] = sub[t].replace("-", "").replace(".", "")
            unaligned = os.path.join(shared, "backbone_{}_unalign.txt".format(i + 1))
            write_fasta(seqs, unaligned)
            with open(out + ".tmp", "w") as f, open(os.path.join(shared, "mafft.log"), "a") as log:
                subprocess.run([mafft] + METHODS[method] + ["--quiet", "--thread", "1", "--anysymbol", unaligned],
                               stdout=f, stderr=log, check=True)
            write_fasta({k: v.upper() for k, v in read_fasta(out + ".tmp").items()}, out)
            os.remove(out + ".tmp")
            os.remove(unaligned)
        with concurrent.futures.ThreadPoolExecutor(job.threads) as ex:
            list(ex.map(one, range(r)))
        json.dump({"backbone_s": round(time.time() - t0, 1)}, open(done, "w"))
    paths = sorted(glob.glob(os.path.join(shared, "backbone_*_mafft.txt")))
    assert len(paths) == r, "expected {} backbones in {}, found {}".format(r, shared, len(paths))
    return paths, json.load(open(done))["backbone_s"], built_now


def merge(job, method, pick, mode, r, per=8):
    paths, secs, built_now = build(job, method, pick, r, per)
    M.magus_merge(job, job.out, backbones=(job.backbones + paths) if mode == "add" else paths)
    return {"backbone_s": secs, "backbones": len(paths) + (len(job.backbones) if mode == "add" else 0),
            "feature_s": {"backbones": secs} if built_now else {}, "feature_cold_s": {}}
