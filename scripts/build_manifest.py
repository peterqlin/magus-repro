#!/usr/bin/env python3
"""Write data/manifest.tsv from the staged datasets in data/datasets/.

Usage: build_manifest.py

Columns: name, condition, replicate, unaligned, reference, n_seqs, ref_length.
Paths are relative to the project root; ref_length is the reference alignment width.
The rows are the datasets stage_rose.py and stage_rnasim.py stage (the archive's replicate names); any other
directory in data/datasets/ (e.g. left over from an earlier naming) is reported and left out.
"""

import os
import sys

from stage_rose import CONDITIONS, OUT, REPLICATES, ROOT, read_fasta, write_if_changed
from stage_rnasim import load_config, select

COLUMNS = ["name", "condition", "replicate", "unaligned", "reference", "n_seqs", "ref_length"]
CONDITION_ORDER = ["1000M1", "1000L3", "1000S1", "RNASim"]


def expected_names():
    config = load_config()
    rnasim = select(int(config["RNASIM_SEED"]), int(config["RNASIM_N"]))
    return (["{}_R{}".format(cond, k) for cond in CONDITIONS for k in range(REPLICATES)] +
            ["RNASim_R{}".format(k) for k in rnasim])


def rows(names):
    for name in names:
        d = os.path.join(OUT, name)
        if not os.path.isdir(d):
            sys.exit("missing staged dataset: " + os.path.relpath(d, ROOT))
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
    names = expected_names()
    extra = sorted(d for d in os.listdir(OUT) if os.path.isdir(os.path.join(OUT, d)) and d not in names)
    if extra:
        print("left out (not staged by stage_rose.py / stage_rnasim.py): " + " ".join(extra), file=sys.stderr)
    ordered = sorted(rows(names), key=lambda r: (CONDITION_ORDER.index(r["condition"]), r["replicate"]))
    text = "\t".join(COLUMNS) + "\n" + "".join("\t".join(str(r[c]) for c in COLUMNS) + "\n" for r in ordered)
    path = os.path.join(ROOT, "data", "manifest.tsv")
    print("{} rows, {}".format(len(ordered), "written" if write_if_changed(path, text) else "unchanged"))


if __name__ == "__main__":
    main()
