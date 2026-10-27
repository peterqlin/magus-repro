#!/usr/bin/env python3
# AI-assisted (Claude), exploration code for CS581 project
"""Write the reps.tsv that `python3 -m graphmods.sweep` reads: one row per finished MAGUS run.

Usage: graphmods_reps.py [--out runs/graphmods_reps.tsv] [--all]

For each data/manifest.tsv row whose run has runs/<name>/DONE (with --all: any run whose work dir holds subset
alignments and backbones), the row is: name, condition, subsets = runs/<name>/work/subalignments,
backbones = runs/<name>/work/graph, reference = the dataset's reference.fasta. Paths are relative to the
project root, as the container sees them at /work.
"""

import argparse
import csv
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("runs", "graphmods_reps.tsv"))
    ap.add_argument("--all", action="store_true", help="include runs without DONE whose work dir is complete")
    a = ap.parse_args()

    rows, skipped = [], []
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "manifest.tsv")), delimiter="\t"):
        run = os.path.join("runs", r["name"])
        subsets = os.path.join(run, "work", "subalignments")
        backbones = os.path.join(run, "work", "graph")
        complete = (glob.glob(os.path.join(ROOT, subsets, "*")) and
                    glob.glob(os.path.join(ROOT, backbones, "backbone_*_mafft.txt")))
        if (os.path.exists(os.path.join(ROOT, run, "DONE")) or a.all) and complete:
            rows.append([r["name"], r["condition"], subsets, backbones, r["reference"]])
        else:
            skipped.append(r["name"])

    out = os.path.join(ROOT, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write("name\tcondition\tsubsets\tbackbones\treference\n")
        f.writelines("\t".join(row) + "\n" for row in rows)
    print("{} rows -> {} ({} without a finished run)".format(len(rows), os.path.relpath(out, ROOT), len(skipped)))


if __name__ == "__main__":
    main()
