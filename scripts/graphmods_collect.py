#!/usr/bin/env python3
# AI-assisted (Claude), exploration code for CS581 project
"""Collect the per-dataset graphmods sweep rows (runs/_graphmods/rows/<name>.jsonl) into results/.

Usage: graphmods_collect.py      ($GRAPHMODS_TAG, $GRAPHMODS_ONLY: a tagged run of some strategies, as
                                  scripts/icc/submit_graphmods.sh documents)

Writes results/graphmods_rows.jsonl (every row, manifest order, then sweep order) and
results/graphmods_scores.csv (one row per dataset and setting, scored like results/scores.csv: SPFN, SPFP,
SPFN_SPFP_mean and TC as fractions). Datasets missing a setting, and failed runs, are listed on stderr and
make the exit status 1; the outputs still hold every row there is.
"""

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from graphmods import registry  # noqa: E402
from graphmods.sweep import plan  # noqa: E402

TAG = os.environ.get("GRAPHMODS_TAG") or ""
ONLY = [s for s in (os.environ.get("GRAPHMODS_ONLY") or "").split(",") if s]
SUFFIX = "_" + TAG if TAG else ""
ROWS_DIR = os.path.join(ROOT, "runs", "_graphmods", "rows" + SUFFIX)
COLUMNS = ["name", "condition", "replicate", "variant", "strategy", "family", "params", "SPFN", "SPFP",
           "SPFN_SPFP_mean", "TC", "merge_s", "edges", "kept_edges", "added_edges"]


def read_rows(path):
    rows = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                r = json.loads(line)
                rows[r["variant"]] = r
    return rows


def main():
    mods = [m for m in registry.all_strategies() if not ONLY or m.NAME in ONLY or m.NAME == "magus"]
    variants = [registry.variant_name(m.NAME, p) for m, p in plan(mods)]
    manifest = list(csv.DictReader(open(os.path.join(ROOT, "data", "manifest.tsv")), delimiter="\t"))

    rows, scored, problems = [], [], []
    for d in manifest:
        found = read_rows(os.path.join(ROWS_DIR, d["name"] + ".jsonl"))
        missing = [v for v in variants if v not in found]
        if missing:
            problems.append("{}: {} of {} settings missing".format(d["name"], len(missing), len(variants)))
        for v in variants:
            if v not in found:
                continue
            r = found[v]
            rows.append(r)
            if r.get("failed"):
                problems.append("{} {}: failed ({})".format(d["name"], v, r["failed"]))
                continue
            spfn, spfp = r["SPFN"] / 100, r["SPFP"] / 100
            scored.append([d["name"], d["condition"], d["replicate"], v, r["strategy"], r["family"],
                           json.dumps(r["params"], sort_keys=True), spfn, spfp, (spfn + spfp) / 2,
                           r["TC"] / 100 if r.get("TC") is not None else "", r["merge_s"],
                           r.get("edges", ""), r.get("kept_edges", ""), r.get("added_edges", "")])

    results = os.path.join(ROOT, "results")
    with open(os.path.join(results, "graphmods{}_rows.jsonl".format(SUFFIX)), "w") as f:
        f.writelines(json.dumps(r, default=str) + "\n" for r in rows)
    with open(os.path.join(results, "graphmods{}_scores.csv".format(SUFFIX)), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(scored)
    print("wrote results/graphmods{0}_rows.jsonl ({1} rows) and results/graphmods{0}_scores.csv ({2} scored; "
          "{3} datasets x {4} settings expected)".format(SUFFIX, len(rows), len(scored), len(manifest), len(variants)))

    if problems:
        sys.exit("\n".join(problems))


if __name__ == "__main__":
    main()
