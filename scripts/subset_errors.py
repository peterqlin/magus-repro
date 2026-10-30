#!/usr/bin/env python3
# AI-assisted (Claude), exploration code for CS581 project
"""Errors already inside the subset alignments, which no change to the alignment graph can fix.

Usage: subset_errors.py [name ...]   (default: every manifest dataset with a finished run; run in the image)
       subset_errors.py --summary    (results/ceiling_subset_errors.csv from the per-dataset JSON files)

For each dataset's MAGUS run (runs/<name>/work/subalignments, runs/<name>/magus.aln):
- every subset alignment is scored with FastSP against the reference restricted to the subset's sequences (all-gap
  columns removed) -> results/ceiling_subsets/<name>.csv;
- MAGUS's final alignment is split into letter pairs within one subset and pairs across subsets, counting reference
  pairs, estimated pairs and shared pairs in each -> results/ceiling_subsets/<name>.json. SPFN = 1 - shared / reference
  pairs and SPFP = 1 - shared / estimated pairs, so within_FN / ref_pairs + cross_FN / ref_pairs = SPFN; the
  within-subset share is the part the graph step cannot change, since MAGUS keeps each subset alignment's columns.
The within-subset counts of the final alignment are checked against the same counts from the subset files.
"""

import csv
import glob
import json
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from graphmods.oracle import residues, reference_columns  # noqa: E402
from graphmods.score import fastsp, read_fasta, write_fasta  # noqa: E402

OUT = os.path.join(ROOT, "results", "ceiling_subsets")


def pairs(*keys):
    """Sum of C(n, 2) over the groups of letters that agree on every key."""
    _, n = np.unique(np.stack(keys), axis=1, return_counts=True)
    return int((n * (n - 1) // 2).sum())


def letters(aln, refcol, subset_of):
    """(alignment column, reference column, subset) of every letter of an alignment."""
    col, ref, sub = [], [], []
    for taxon, seq in aln.items():
        pos = residues(seq)
        col.append(pos)
        ref.append(refcol[taxon])
        sub.append(np.full(len(pos), subset_of[taxon]))
    return np.concatenate(col), np.concatenate(ref), np.concatenate(sub)


def counts(col, ref, sub):
    """Reference, estimated and shared pairs: in total and within subsets."""
    return {"ref_pairs": pairs(ref), "est_pairs": pairs(col), "shared": pairs(col, ref),
            "ref_within": pairs(ref, sub), "est_within": pairs(col, sub), "shared_within": pairs(col, ref, sub)}


def dataset(name, reference):
    run = os.path.join(ROOT, "runs", name)
    refcol, _ = reference_columns(reference)
    ref = read_fasta(reference)
    paths = sorted(glob.glob(os.path.join(run, "work", "subalignments", "*")))
    subsets = [read_fasta(p) for p in paths]
    subset_of = {t: i for i, s in enumerate(subsets) for t in s}

    rows, within = [], {"ref_within": 0, "est_within": 0, "shared_within": 0}
    with tempfile.TemporaryDirectory() as tmp:
        for i, (path, aln) in enumerate(zip(paths, subsets)):
            sub_ref = {t: ref[t] for t in aln}
            keep = np.zeros(len(next(iter(sub_ref.values()))), dtype=bool)
            for seq in sub_ref.values():
                keep[residues(seq)] = True
            sub_ref = {t: "".join(np.array(list(s))[keep]) for t, s in sub_ref.items()}
            ref_path = os.path.join(tmp, "ref.fasta")
            write_fasta(sub_ref, ref_path)
            s = fastsp(ref_path, path)
            c = counts(*letters(aln, refcol, {t: 0 for t in aln}))
            within["ref_within"] += c["ref_pairs"]
            within["est_within"] += c["est_pairs"]
            within["shared_within"] += c["shared"]
            rows.append({"name": name, "subset": os.path.basename(path), "n_seqs": len(aln),
                         "SPFN": s["SPFN"], "SPFP": s["SPFP"], "TC": s["TC"],
                         "ref_pairs": c["ref_pairs"], "est_pairs": c["est_pairs"], "shared": c["shared"]})

    final = counts(*letters(read_fasta(os.path.join(run, "magus.aln")), refcol, subset_of))
    for k, v in within.items():
        if final[k] != v:
            raise SystemExit(f"{name}: {k} is {final[k]} in magus.aln but {v} in the subset alignments")
    fn_within = final["ref_within"] - final["shared_within"]
    fp_within = final["est_within"] - final["shared_within"]
    fn = final["ref_pairs"] - final["shared"]
    fp = final["est_pairs"] - final["shared"]
    summary = dict(final, name=name, subsets=len(paths),
                   SPFN=fn / final["ref_pairs"], SPFP=fp / final["est_pairs"],
                   SPFN_within=fn_within / final["ref_pairs"], SPFP_within=fp_within / final["est_pairs"],
                   FN_within_share=fn_within / fn if fn else 0.0, FP_within_share=fp_within / fp if fp else 0.0,
                   subset_SPFN_mean=float(np.mean([r["SPFN"] for r in rows])),
                   subset_SPFP_mean=float(np.mean([r["SPFP"] for r in rows])))
    return rows, summary


def summarize(manifest):
    """results/ceiling_subset_errors.csv: one row per dataset from results/ceiling_subsets/<name>.json."""
    rows = [json.load(open(os.path.join(OUT, d["name"] + ".json"))) for d in manifest
            if os.path.exists(os.path.join(OUT, d["name"] + ".json"))]
    out = os.path.join(ROOT, "results", "ceiling_subset_errors.csv")
    fields = ["name", "condition", "subsets", "SPFN", "SPFP", "SPFN_within", "SPFP_within", "FN_within_share",
              "FP_within_share", "subset_SPFN_mean", "subset_SPFP_mean", "ref_pairs", "est_pairs", "shared",
              "ref_within", "est_within", "shared_within"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("wrote {} ({} of {} datasets)".format(os.path.relpath(out, ROOT), len(rows), len(manifest)))
    if len(rows) != len(manifest):
        sys.exit(1)


def main():
    manifest = list(csv.DictReader(open(os.path.join(ROOT, "data", "manifest.tsv")), delimiter="\t"))
    if sys.argv[1:] == ["--summary"]:
        return summarize(manifest)
    names = set(sys.argv[1:])
    os.makedirs(OUT, exist_ok=True)
    for d in manifest:
        if (names and d["name"] not in names) or not os.path.exists(os.path.join(ROOT, "runs", d["name"], "DONE")):
            continue
        rows, summary = dataset(d["name"], os.path.join(ROOT, d["reference"]))
        summary["condition"] = d["condition"]
        with open(os.path.join(OUT, d["name"] + ".csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        json.dump(summary, open(os.path.join(OUT, d["name"] + ".json"), "w"), indent=1)
        print("{}: SPFN {:.4f} (within subsets {:.4f}), SPFP {:.4f} (within {:.4f}); mean subset SPFN {:.4f}".format(
            d["name"], summary["SPFN"], summary["SPFN_within"], summary["SPFP"], summary["SPFP_within"],
            summary["subset_SPFN_mean"]))


if __name__ == "__main__":
    main()
