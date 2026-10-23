#!/usr/bin/env python3
"""List every dataset directory in the extracted archive and classify its files.

Usage: inventory.py [extracted_root]   (default: data/raw/extracted/Datasets)

A dataset directory is any directory that directly contains files. For each one,
prints the group (e.g. ROSE/1000M1), the replicate directory, the file that looks
like the unaligned input, the file that looks like the reference alignment, the
number of sequences in the reference, and any other files. Flags directories where
the classification is ambiguous (zero or several candidates).
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, "data", "raw", "extracted", "Datasets")

REFERENCE = re.compile(r"(true.*\.(fasta|fa|fas|txt|aln)$|\.aln\.true\.fasta$|^true_align)", re.I)
UNALIGNED = re.compile(r"(unalign|raw|input).*\.(fasta|fa|fas|txt)$", re.I)
EXCLUDE = re.compile(r"internal|\.tre(e)?$|\.tt$|\.mt", re.I)


def count_seqs(path):
    with open(path) as f:
        return sum(1 for line in f if line.startswith(">"))


def classify(files):
    refs = [f for f in files if REFERENCE.search(f) and not EXCLUDE.search(f)]
    unaligned = [f for f in files if UNALIGNED.search(f) and not EXCLUDE.search(f)]
    return refs, unaligned


def main():
    top = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    print("\t".join(["group", "replicate", "unaligned", "reference", "n_ref_seqs", "other_files", "status"]))
    for dirpath, dirnames, filenames in sorted(os.walk(top)):
        dirnames.sort()
        files = sorted(f for f in filenames if not f.startswith("."))
        if not files:
            continue
        rel = os.path.relpath(dirpath, top)
        group, replicate = os.path.split(rel)
        refs, unaligned = classify(files)
        other = [f for f in files if f not in refs and f not in unaligned]
        status = "ok" if len(refs) == 1 and len(unaligned) <= 1 else "AMBIGUOUS"
        n = str(count_seqs(os.path.join(dirpath, refs[0]))) if len(refs) == 1 else ""
        print("\t".join([group, replicate, ",".join(unaligned) or "-", ",".join(refs) or "-", n, ",".join(other) or "-", status]))


if __name__ == "__main__":
    main()
