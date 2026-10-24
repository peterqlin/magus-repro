#!/usr/bin/env python3
"""Score the Step 8 pilot runs and write results/pilot_scores.csv.

Usage: pilot_scores.py [name ...]   (default: the four pilots)
"""

import csv
import os
import re
import sys

from score import ROOT, score

PILOTS = ["1000M1_R01", "1000L1_R01", "1000S1_R01", "RNASim_R01"]
COLUMNS = ["name", "SPFN", "SPFP", "SPFN_SPFP_mean", "SP_score", "TC", "wall_s", "max_rss_mb"]


def parse_time(path):
    """Return (wall seconds, max RSS in MiB) from GNU time -v output."""
    text = open(path).read()
    wall = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)", text).group(1)
    seconds = 0.0
    for part in wall.split(":"):
        seconds = seconds * 60 + float(part)
    rss_kb = int(re.search(r"Maximum resident set size \(kbytes\): (\d+)", text).group(1))
    return seconds, rss_kb / 1024


def main():
    names = sys.argv[1:] or PILOTS
    manifest = {r["name"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data", "manifest.tsv")), delimiter="\t")}
    out = os.path.join(ROOT, "results", "pilot_scores.csv")
    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for name in names:
            run = os.path.join(ROOT, "runs", name)
            s = score(os.path.join(ROOT, manifest[name]["reference"]), os.path.join(run, "magus.aln"))
            wall, rss = parse_time(os.path.join(run, "time.txt"))
            row = [name, s["SPFN"], s["SPFP"], s["SPFN_SPFP_mean"], s["SP-Score"], s["TC"], round(wall, 2), round(rss, 1)]
            writer.writerow(row)
            print(",".join(str(v) for v in row))
    print("wrote " + os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
