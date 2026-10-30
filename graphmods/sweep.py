# AI-assisted (Claude), exploration code for CS581 project
"""Sweep every strategy in the strategies folder over its GRID on every dataset (merge-only, paired).

    python -m graphmods.sweep --reps reps.tsv --out rows.jsonl [--work DIR] [--only strict_k,overlap] \
        [--families strict,adaptive,network] [--threads 4] [--commit-every 600 --commit-cmd "bash push.sh"]

reps.tsv: tab-separated with a header; columns name, condition, subsets, backbones, reference (paths: the MAGUS run's
subset-alignment dir, its backbone dir or files, the reference alignment). For a full MAGUS work dir use
work/subalignments and work/graph.

Restartable: a (name, variant) already in rows.jsonl is skipped. The MAGUS control ("magus") runs first on each dataset.
The graph is built once per dataset in an untimed warm-up run and cached in WORK/<name>/cache, with each feature the
first time a strategy needs it (its compute time is kept, so tables charge every variant the cold cost of the features
it uses). Per-run outputs are deleted after scoring (rows keep SPFN, SPFP, err, TC, merge time, edges kept / added).
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import time

from . import registry
from .replay import replay


def done_keys(path):
    keys = set()
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                r = json.loads(line)
                keys.add((r["name"], r["variant"]))
    return keys


def plan(strategies):
    """[(strategy module, params)], control first."""
    out = []
    for m in sorted(strategies, key=lambda m: (m.NAME != "magus", m.FAMILY, m.NAME)):
        for p in m.GRID:
            out.append((m, dict(p)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=os.path.join("runs", "_graphmods"))
    ap.add_argument("--strategies")
    ap.add_argument("--only", help="comma-separated strategy names (default: all)")
    ap.add_argument("--families", help="comma-separated families (default: all)")
    ap.add_argument("--names", help="comma-separated dataset names from reps.tsv (default: all)")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--commit-every", type=float, default=0, help="seconds between --commit-cmd calls (0: never)")
    ap.add_argument("--commit-cmd")
    a = ap.parse_args()

    fams = set(a.families.split(",")) if a.families else None
    mods = registry.all_strategies(a.strategies, fams)
    if a.only:
        keep = set(a.only.split(",")) | {"magus"}
        mods = [m for m in mods if m.NAME in keep]
    if not any(m.NAME == "magus" for m in mods):
        mods.append(registry.load("magus", a.strategies))
    todo = plan(mods)
    reps = list(csv.DictReader(open(a.reps), delimiter="\t"))
    if a.names:
        names = set(a.names.split(","))
        reps = [r for r in reps if r["name"] in names]
    done = done_keys(a.out)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    last_commit = time.time()
    for rep in reps:
        name = rep["name"]
        cache = os.path.join(a.work, name, "cache")
        if any((name, registry.variant_name(m.NAME, p)) not in done for m, p in todo) and \
                not os.path.exists(os.path.join(cache, "graph.json")):
            # build the graph cache in an untimed run, so every timed run (the control included) loads the same cache
            warm = os.path.join(a.work, name, "runs", "_warmup")
            replay(rep["subsets"], rep["backbones"].split(","), rep["reference"], warm, "magus", {}, cache, a.threads,
                   a.strategies, name=name)
            shutil.rmtree(warm, ignore_errors=True)
        for m, params in todo:
            variant = registry.variant_name(m.NAME, params)
            if (name, variant) in done:
                continue
            run_dir = os.path.join(a.work, name, "runs", variant)
            try:
                row = replay(rep["subsets"], rep["backbones"].split(","), rep["reference"], run_dir, m.NAME, params,
                             cache, a.threads, a.strategies, name=name)
                row.update(name=name, condition=rep.get("condition"), family=m.FAMILY)
            except subprocess.CalledProcessError as e:
                log = os.path.join(run_dir, "magus.log")
                tail = open(log).read()[-2000:] if os.path.exists(log) else ""
                row = {"name": name, "condition": rep.get("condition"), "variant": variant, "strategy": m.NAME,
                       "family": m.FAMILY, "params": params, "failed": f"exit {e.returncode}", "log_tail": tail}
            shutil.rmtree(run_dir, ignore_errors=True)
            with open(a.out, "a") as f:
                f.write(json.dumps(row, default=str) + "\n")
            done.add((name, variant))
            print(name, variant, "FAILED" if row.get("failed") else "err={:.3f} merge_s={}".format(
                row["err"], row["merge_s"]), flush=True)
            if a.commit_cmd and a.commit_every and time.time() - last_commit >= a.commit_every:
                subprocess.run(a.commit_cmd, shell=True)
                last_commit = time.time()
        shutil.rmtree(os.path.join(a.work, name), ignore_errors=True)  # cache no longer needed
        if a.commit_cmd:
            subprocess.run(a.commit_cmd, shell=True)
            last_commit = time.time()


if __name__ == "__main__":
    main()
