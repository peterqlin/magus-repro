#!/usr/bin/env python3
"""Stage RNASIM_N of the archive's 1000-sequence RNASim samples, chosen with RNASIM_SEED.

Usage: stage_rnasim.py

The chosen archive samples R<k> become data/datasets/RNASim_R<k> (the archive's own names) with:
  reference.fasta  true_align.txt with all-gap columns removed
  unaligned.fasta  the reference rows with gaps removed
  ids.txt          the sequence IDs, one per line
  source.txt       the archive file the dataset came from
data/datasets/rnasim_selection.tsv records the mapping. Unchanged files are not rewritten.
"""

import os
import random

from stage_rose import ROOT, OUT, drop_all_gap_columns, read_fasta, to_fasta, write_if_changed

ARCHIVE = os.path.join(ROOT, "data", "raw", "extracted", "Datasets", "RNASim", "1000")
SAMPLES = 20


def load_config():
    config = {}
    with open(os.path.join(ROOT, "config.env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key] = value
    return config


def select(seed, n):
    return sorted(random.Random(seed).sample(range(SAMPLES), n))


def main():
    config = load_config()
    seed, n = int(config["RNASIM_SEED"]), int(config["RNASIM_N"])
    chosen = select(seed, n)

    rows = ["name\tarchive_sample\tsource"]
    for k in chosen:
        src = os.path.join(ARCHIVE, "R{}".format(k), "true_align.txt")
        name = "RNASim_R{}".format(k)
        dest = os.path.join(OUT, name)
        os.makedirs(dest, exist_ok=True)

        reference = drop_all_gap_columns(read_fasta(src))
        unaligned = [(nm, s.replace("-", "")) for nm, s in reference]
        source = os.path.relpath(src, ROOT)
        changed = [
            write_if_changed(os.path.join(dest, "reference.fasta"), to_fasta(reference)),
            write_if_changed(os.path.join(dest, "unaligned.fasta"), to_fasta(unaligned)),
            write_if_changed(os.path.join(dest, "ids.txt"), "".join(nm + "\n" for nm, _ in reference)),
            write_if_changed(os.path.join(dest, "source.txt"), source + "\n"),
        ]
        rows.append("{}\tR{}\t{}".format(name, k, source))
        print("{}\tR{}\t{}".format(name, k, "written" if any(changed) else "unchanged"))

    header = "# RNASIM_SEED={} RNASIM_N={}; random.Random(seed).sample(range({}), n), sorted\n".format(seed, n, SAMPLES)
    write_if_changed(os.path.join(OUT, "rnasim_selection.tsv"), header + "\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
