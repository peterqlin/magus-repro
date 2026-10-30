# AI-assisted (Claude), exploration code for CS581 project
"""Split an alignment's SP error into pairs inside one subset and pairs across subsets.

    python3 -m graphmods.spsplit --reference REF --estimate EST --subsets DIR [--json]

A merge that keeps the subset alignments' columns fixed (MAGUS, every strategy here) cannot change the residue
pairs inside one subset: those are the subset alignments' own pairs. So the within-subset part of SPFN / SPFP is a
floor given the subset alignments, and only the cross-subset part depends on the merge. Counts are homologous
residue pairs, as FastSP counts them (SPFN = 1 - shared / reference pairs, SPFP = 1 - shared / estimated pairs).
`floor_err` is the error with every cross-subset pair right; `cross_err_share` is the part of err the merge owns.
"""
import argparse
import collections
import glob
import json
import os

import numpy as np

from .score import read_fasta


def _residue_columns(aln):
    """name -> array of the alignment column of each residue (in order)."""
    out = {}
    for name, row in aln.items():
        r = np.frombuffer(row.upper().encode(), dtype=np.uint8)
        out[name] = np.flatnonzero((r != ord("-")) & (r != ord(".")))
    return out


def _pairs(groups):
    """sum of C(size, 2) over a Counter of group -> size."""
    return sum(c * (c - 1) // 2 for c in groups.values())


def split(reference, estimate, subsets):
    ref = _residue_columns(read_fasta(reference))
    est = _residue_columns(read_fasta(estimate))
    subset_of = {}
    for i, path in enumerate(sorted(subsets)):
        for name in read_fasta(path):
            subset_of[name] = i
    names = [n for n in ref if n in est]
    by = {k: collections.Counter() for k in ("ref", "ref_s", "est", "est_s", "both", "both_s")}
    for n in names:
        s = subset_of[n]
        rc, ec = ref[n], est[n]
        assert len(rc) == len(ec), "sequence {} differs between reference and estimate".format(n)
        for r, e in zip(rc.tolist(), ec.tolist()):
            by["ref"][r] += 1
            by["ref_s"][(r, s)] += 1
            by["est"][e] += 1
            by["est_s"][(e, s)] += 1
            by["both"][(e, r)] += 1
            by["both_s"][(e, r, s)] += 1
    T, Ts = _pairs(by["ref"]), _pairs(by["ref_s"])
    E, Es = _pairs(by["est"]), _pairs(by["est_s"])
    S, Ss = _pairs(by["both"]), _pairs(by["both_s"])
    out = {
        "SPFN": 1 - S / T, "SPFP": 1 - S / E,
        "within_SPFN": (Ts - Ss) / T, "cross_SPFN": ((T - Ts) - (S - Ss)) / T,
        "within_SPFP": (Es - Ss) / E, "cross_SPFP": ((E - Es) - (S - Ss)) / E,
        "true_pairs": T, "true_pairs_within": Ts, "est_pairs": E, "est_pairs_within": Es,
    }
    out["err"] = (out["SPFN"] + out["SPFP"]) / 2
    # every cross-subset pair right: shared cross = reference cross = estimated cross
    fn_floor = (Ts - Ss) / T
    fp_floor = (Es - Ss) / (Es + (T - Ts))
    out["floor_err"] = (fn_floor + fp_floor) / 2
    out["cross_err_share"] = (out["cross_SPFN"] + out["cross_SPFP"]) / 2 / out["err"] if out["err"] else 0.0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--estimate", required=True)
    ap.add_argument("--subsets", required=True, help="dir of the subset alignments (or a glob)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    paths = sorted(glob.glob(os.path.join(a.subsets, "*"))) if os.path.isdir(a.subsets) else sorted(glob.glob(a.subsets))
    r = split(a.reference, a.estimate, paths)
    if a.json:
        print(json.dumps(r))
    else:
        print("err {:.3%} = SPFN {:.3%} (within {:.3%}, cross {:.3%}) / SPFP {:.3%} (within {:.3%}, cross {:.3%}); "
              "floor {:.3%}; merge owns {:.0%}".format(r["err"], r["SPFN"], r["within_SPFN"], r["cross_SPFN"],
                                                      r["SPFP"], r["within_SPFP"], r["cross_SPFP"], r["floor_err"],
                                                      r["cross_err_share"]))


if __name__ == "__main__":
    main()
