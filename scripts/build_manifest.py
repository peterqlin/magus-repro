#!/usr/bin/env python3
"""Write data/manifest.tsv from the staged datasets in data/datasets/.

Usage: build_manifest.py

Columns: name, condition, replicate, unaligned, reference, n_seqs, ref_length.
Paths are relative to the project root; ref_length is the reference alignment width.
"""

import glob
import os

from stage_rose import ROOT, read_fasta, write_if_changed

COLUMNS = ["name", "condition", "replicate", "unaligned", "reference", "n_seqs", "ref_length"]
CONDITION_ORDER = ["1000M1", "1000L1", "1000S1", "RNASim"]


def rows():
    for d in glob.glob(os.path.join(ROOT, "data", "datasets", "*_R[0-9][0-9]")):
        name = os.path.basename(d)
        condition, replicate = name.rsplit("_R", 1)
        unaligned = os.path.join(d, "unaligned.fasta")
        reference = os.path.join(d, "reference.fasta")
        ref = read_fasta(reference)
        yield {
            "name": name,
            "condition": condition,
            "replicate": int(replicate),
            "unaligned": os.path.relpath(unaligned, ROOT),
            "reference": os.path.relpath(reference, ROOT),
            "n_seqs": len(read_fasta(unaligned)),
            "ref_length": len(ref[0][1]),
        }


def main():
    ordered = sorted(rows(), key=lambda r: (CONDITION_ORDER.index(r["condition"]), r["replicate"]))
    text = "\t".join(COLUMNS) + "\n" + "".join("\t".join(str(r[c]) for c in COLUMNS) + "\n" for r in ordered)
    path = os.path.join(ROOT, "data", "manifest.tsv")
    print("{} rows, {}".format(len(ordered), "written" if write_if_changed(path, text) else "unchanged"))


if __name__ == "__main__":
    main()
