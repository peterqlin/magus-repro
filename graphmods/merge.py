# AI-assisted (Claude), exploration code for CS581 project
"""Whole-merge strategies: replace MAGUS's entire merge (graph, MCL, trace) with another way of merging the same
fixed subset alignments.

A strategy file that defines

    def merge(job, **params): ...      # write the merged alignment to job.out

is run by `python3 -m graphmods.run --strategy NAME -- <MAGUS arguments>` instead of MAGUS, with the inputs taken
from MAGUS's own flags (-s subset alignments, -b backbones, -o output, -d work dir, -np threads), so graphmods.replay
and graphmods.sweep run it like any other strategy. The helpers below cover what the bundled strategies share: the
subset alignments, MAGUS's bundled tools, a guide tree over the subsets and a progressive pairwise merge along it.
"""
import argparse
import collections
import glob
import json
import math
import os
import subprocess
import time

from .score import read_fasta, write_fasta


class Job:
    def __init__(self, subsets, backbones, out, work, threads):
        self.subsets, self.backbones, self.out, self.work, self.threads = subsets, backbones, out, work, threads
        os.makedirs(work, exist_ok=True)

    def path(self, name):
        return os.path.join(self.work, name)


def parse_magus_args(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("-s", "--subalignments", nargs="+", default=[])
    ap.add_argument("-b", "--backbones", nargs="+", default=[])
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("-d", "--directory", default="graphmods_merge_work")
    ap.add_argument("-np", "--numprocs", type=int, default=os.cpu_count())
    a, _ = ap.parse_known_args(argv)

    def files(paths):
        out = []
        for p in paths:
            out += sorted(glob.glob(os.path.join(p, "*"))) if os.path.isdir(p) else [p]
        return [os.path.abspath(p) for p in out]
    backbones = [p for p in files(a.backbones) if p.endswith("_mafft.txt")] or files(a.backbones)
    return Job(files(a.subalignments), backbones, os.path.abspath(a.output), os.path.abspath(a.directory),
               max(1, a.numprocs))


def tool(name):
    """A tool bundled with MAGUS: clustal, mafft, hmmbuild, hmmalign, ..."""
    from magus.configuration import Configs
    return getattr(Configs, name + "Path")


def run(cmd, stdout=None, log=None):
    with open(log or os.devnull, "a") as err:
        subprocess.run([str(c) for c in cmd], stdout=stdout, stderr=err, check=True)


def finish(job, path):
    """Write `path` to job.out as plain upper-case FASTA with '-' gaps."""
    aln = read_fasta(path)
    write_fasta({k: v.replace(".", "-").upper() for k, v in aln.items()}, job.out)


# ------------------------------------------------------------------ guide tree over subsets
def _kmers(seqs, k=6):
    c = collections.Counter()
    for s in seqs:
        s = s.replace("-", "").replace(".", "").upper().replace("U", "T")
        for i in range(len(s) - k + 1):
            c[s[i:i + k]] += 1
    return c


def _cosine_distance(x, y):
    dot = sum(v * y.get(key, 0) for key, v in x.items())
    nx = math.sqrt(sum(v * v for v in x.values()))
    ny = math.sqrt(sum(v * v for v in y.values()))
    return 1.0 - dot / (nx * ny) if nx and ny else 1.0


def guide_tree(subsets):
    """UPGMA over the subsets on 6-mer cosine distance: a list of merges (i, j) of cluster ids, where clusters
    0..n-1 are the subsets and merge t creates cluster n + t."""
    prof = [_kmers(read_fasta(p).values()) for p in subsets]
    n = len(prof)
    size = {i: 1 for i in range(n)}
    dist = {(i, j): _cosine_distance(prof[i], prof[j]) for i in range(n) for j in range(i + 1, n)}
    merges, nxt = [], n
    while len(size) > 1:
        (i, j), _ = min(dist.items(), key=lambda kv: kv[1])
        merges.append((i, j))
        for k in list(size):
            if k in (i, j):
                continue
            dik = dist.pop((min(i, k), max(i, k)))
            djk = dist.pop((min(j, k), max(j, k)))
            dist[(k, nxt)] = (size[i] * dik + size[j] * djk) / (size[i] + size[j])
        del dist[(i, j)]
        size[nxt] = size.pop(i) + size.pop(j)
        nxt += 1
    return merges


def progressive(job, merge_two):
    """Merge the subset alignments pairwise along guide_tree; merge_two(a, b, out) aligns two alignments, keeping
    each one's columns. Returns the path of the final alignment."""
    paths = dict(enumerate(job.subsets))
    for t, (i, j) in enumerate(guide_tree(job.subsets)):
        out = job.path("merge_{}.fasta".format(t))
        merge_two(paths.pop(i), paths.pop(j), out)
        paths[len(job.subsets) + t] = out
    return next(iter(paths.values()))


# ------------------------------------------------------------------ driver
def run_strategy(strategy, params, magus_argv, info_path=None):
    job = parse_magus_args(magus_argv)
    t0 = time.time()
    extra = strategy.merge(job, **params) or {}  # a strategy may return extra info fields
    info = {"strategy": strategy.NAME, "params": params, "family": strategy.FAMILY, "subsets": len(job.subsets),
            "merge_tool_s": round(time.time() - t0, 2)}
    info.update(extra)
    if info_path:
        json.dump(info, open(info_path, "w"), indent=1)
