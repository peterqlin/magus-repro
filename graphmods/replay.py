# AI-assisted (Claude), exploration code for CS581 project
"""Merge-only run of one strategy on a MAGUS run's own subsets and backbones, scored against the reference.

    python -m graphmods.replay --subsets DIR --backbones DIR_OR_FILES... --reference REF.fasta --out DIR \
        --strategy strict_k --param K=5 [--cache DIR] [--threads 4]

Decomposition and subset / backbone alignment are not redone: the strategy sees exactly the inputs the MAGUS run used,
so methods are compared on identical inputs (paired). For a full MAGUS work dir: subsets are work/subalignments and
backbones are work/graph/backbone_*_mafft.txt. Prints one JSON row: SPFN, SPFP, err (percent), TC, merge_s, edges.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

from . import registry, score

MERGE_FLAGS = ["--graphclustermethod", "mcl", "--graphtracemethod", "minclusters", "--graphtraceoptimize", "false",
               "-f", "4"]
PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def backbone_files(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            m = sorted(glob.glob(os.path.join(p, "*_mafft.txt")))
            out.extend(m if m else sorted(os.path.join(p, f) for f in os.listdir(p)))
        else:
            out.append(p)
    return [os.path.abspath(p) for p in out]


def replay(subsets, backbones, reference, out_dir, strategy="magus", params=None, cache=None, threads=4,
           strategies=None, keep_work=False):
    params = params or {}
    out_dir = os.path.abspath(out_dir)
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir)
    out = os.path.join(out_dir, "out.fasta")
    info = os.path.join(out_dir, "info.json")
    cmd = [sys.executable, "-m", "graphmods.run", "--strategy", strategy, "--info", info]
    for k, v in params.items():
        cmd += ["--param", f"{k}={v}"]
    if strategies:
        cmd += ["--strategies", os.path.abspath(strategies)]
    if cache:
        cmd += ["--cache", os.path.abspath(cache)]
    cmd += ["--", "-np", str(threads), "-d", os.path.join(out_dir, "work"), "-s", os.path.abspath(subsets),
            "-b"] + backbone_files(backbones) + ["-o", out] + MERGE_FLAGS
    t0 = time.time()
    with open(os.path.join(out_dir, "magus.log"), "w") as log:
        subprocess.run(cmd, cwd=PKG_ROOT, stdout=log, stderr=subprocess.STDOUT, check=True,
                       env=dict(os.environ, PYTHONPATH=PKG_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")))
    wall = round(time.time() - t0, 1)
    if not keep_work:
        shutil.rmtree(os.path.join(out_dir, "work"), ignore_errors=True)
    s = score.fastsp(reference, out)
    row = {"variant": registry.variant_name(strategy, params), "strategy": strategy, "params": params,
           "SPFN": 100 * s["SPFN"], "SPFP": 100 * s["SPFP"], "err": 50 * (s["SPFN"] + s["SPFP"]),
           "TC": 100 * s["TC"] if s.get("TC") is not None else None, "merge_s": wall}
    if os.path.exists(info):
        row.update({k: v for k, v in json.load(open(info)).items() if k not in ("strategy", "params", "variant")})
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subsets", required=True)
    ap.add_argument("--backbones", required=True, nargs="+")
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strategy", default="magus")
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--strategies")
    ap.add_argument("--cache")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--keep-work", action="store_true")
    a = ap.parse_args()
    row = replay(a.subsets, a.backbones, a.reference, a.out, a.strategy, registry.parse_params(a.param), a.cache,
                 a.threads, a.strategies, a.keep_work)
    print(json.dumps(row))


if __name__ == "__main__":
    main()
