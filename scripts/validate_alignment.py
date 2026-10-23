#!/usr/bin/env python3
"""Check that an alignment is consistent with a set of unaligned sequences.

Usage: validate_alignment.py <unaligned.fasta> <alignment.fasta>

Hard failures (exit 1): ID sets differ, duplicate IDs, unequal row lengths,
a degapped row that doesn't match its input sequence (case-insensitive),
or an empty alignment. All-gap columns are reported as a warning only.
"""

import sys


def read_fasta(path):
    records = []
    name, chunks = None, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    records.append((name, "".join(chunks)))
                name, chunks = line[1:].strip(), []
            else:
                chunks.append(line)
    if name is not None:
        records.append((name, "".join(chunks)))
    return records


def duplicates(records):
    seen, dups = set(), set()
    for name, _ in records:
        if name in seen:
            dups.add(name)
        seen.add(name)
    return dups


def validate(unaligned_path, aligned_path):
    errors, warnings = [], []
    unaligned = read_fasta(unaligned_path)
    aligned = read_fasta(aligned_path)

    if not aligned:
        return ["alignment is empty"], warnings

    for label, records in (("unaligned", unaligned), ("alignment", aligned)):
        dups = duplicates(records)
        if dups:
            errors.append("{} has {} duplicate IDs, e.g. {}".format(label, len(dups), sorted(dups)[:5]))

    raw = {n: s.replace("-", "").upper() for n, s in unaligned}
    aln = dict(aligned)

    missing = raw.keys() - aln.keys()
    extra = aln.keys() - raw.keys()
    if missing:
        errors.append("{} IDs missing from alignment, e.g. {}".format(len(missing), sorted(missing)[:5]))
    if extra:
        errors.append("{} IDs not in unaligned input, e.g. {}".format(len(extra), sorted(extra)[:5]))

    lengths = {len(s) for s in aln.values()}
    if len(lengths) > 1:
        errors.append("rows have unequal lengths: {}".format(sorted(lengths)[:10]))

    mismatched = [n for n in raw.keys() & aln.keys() if aln[n].replace("-", "").upper() != raw[n]]
    if mismatched:
        errors.append("{} rows don't degap to their input sequence, e.g. {}".format(len(mismatched), sorted(mismatched)[:5]))

    if len(lengths) == 1:
        width = lengths.pop()
        rows = list(aln.values())
        all_gap = sum(1 for i in range(width) if all(r[i] == "-" for r in rows))
        if all_gap:
            warnings.append("{} all-gap columns".format(all_gap))

    return errors, warnings


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    errors, warnings = validate(sys.argv[1], sys.argv[2])
    for w in warnings:
        print("WARN: " + w, file=sys.stderr)
    for e in errors:
        print("FAIL: " + e, file=sys.stderr)
    if errors:
        sys.exit(1)
    print("OK: {}".format(sys.argv[2]))


if __name__ == "__main__":
    main()
