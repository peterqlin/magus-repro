#!/usr/bin/env python3
"""Stage the ROSE 1000M1, 1000L3 and 1000S1 replicates from the extracted archive.

Usage: stage_rose.py

Archive replicate R<k> (k = 0..19) becomes data/datasets/<cond>_R<k>/ (the archive's own name) with:
  reference.fasta  rose.aln.true.fasta with all-gap columns removed
  unaligned.fasta  the reference rows with gaps removed
  source.txt       the archive file the dataset came from
Files whose content is unchanged are not rewritten.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "data", "raw", "extracted", "Datasets", "ROSE")
OUT = os.path.join(ROOT, "data", "datasets")
CONDITIONS = ["1000M1", "1000L3", "1000S1"]
REPLICATES = 20


def read_fasta(path):
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                records.append([line[1:].strip(), []])
            else:
                records[-1][1].append(line)
    return [(name, "".join(chunks)) for name, chunks in records]


def drop_all_gap_columns(records):
    width = len(records[0][1])
    keep = [i for i in range(width) if any(seq[i] != "-" for _, seq in records)]
    return [(name, "".join(seq[i] for i in keep)) for name, seq in records]


def to_fasta(records):
    return "".join(">{}\n{}\n".format(name, seq) for name, seq in records)


def write_if_changed(path, text):
    if os.path.exists(path):
        with open(path) as f:
            if f.read() == text:
                return False
    with open(path, "w") as f:
        f.write(text)
    return True


def main():
    for cond in CONDITIONS:
        for k in range(REPLICATES):
            src = os.path.join(ARCHIVE, cond, "R{}".format(k), "rose.aln.true.fasta")
            name = "{}_R{}".format(cond, k)
            dest = os.path.join(OUT, name)
            os.makedirs(dest, exist_ok=True)

            reference = drop_all_gap_columns(read_fasta(src))
            unaligned = [(n, s.replace("-", "")) for n, s in reference]
            changed = [
                write_if_changed(os.path.join(dest, "reference.fasta"), to_fasta(reference)),
                write_if_changed(os.path.join(dest, "unaligned.fasta"), to_fasta(unaligned)),
                write_if_changed(os.path.join(dest, "source.txt"), os.path.relpath(src, ROOT) + "\n"),
            ]
            print("{}\t{}".format(name, "written" if any(changed) else "unchanged"))


if __name__ == "__main__":
    main()
