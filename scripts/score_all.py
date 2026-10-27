#!/usr/bin/env python3
"""Score every finished run (runs/<name>/DONE) and write results/scores.csv.

Usage: score_all.py

One row per manifest dataset with a finished run, in manifest order: FastSP scores against the reference,
plus wall time and max RSS from time.txt. Datasets without a finished run are listed on stderr and make
the exit status 1; the CSV still holds every finished run.
"""

import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from pilot_scores import parse_time
from score import ROOT, score

COLUMNS = ["name", "condition", "replicate", "SPFN", "SPFP", "SPFN_SPFP_mean", "SP_score", "TC",
           "wall_s", "max_rss_mb"]


def score_row(row):
    run = os.path.join(ROOT, "runs", row["name"])
    s = score(os.path.join(ROOT, row["reference"]), os.path.join(run, "magus.aln"))
    wall, rss = parse_time(os.path.join(run, "time.txt"))
    return [row["name"], row["condition"], row["replicate"], s["SPFN"], s["SPFP"], s["SPFN_SPFP_mean"],
            s["SP-Score"], s["TC"], round(wall, 2), round(rss, 1)]


def main():
    manifest = list(csv.DictReader(open(os.path.join(ROOT, "data", "manifest.tsv")), delimiter="\t"))
    done = [r for r in manifest if os.path.exists(os.path.join(ROOT, "runs", r["name"], "DONE"))]
    missing = [r["name"] for r in manifest if r not in done]

    workers = int(os.environ.get("SLURM_CPUS_PER_TASK", "2"))
    with ThreadPoolExecutor(workers) as pool:
        rows = list(pool.map(score_row, done))

    out = os.path.join(ROOT, "results", "scores.csv")
    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    print("wrote {} ({} of {} datasets)".format(os.path.relpath(out, ROOT), len(rows), len(manifest)))

    if missing:
        sys.exit("no finished run for {}: {}".format(len(missing), " ".join(missing)))


if __name__ == "__main__":
    main()
