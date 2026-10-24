#!/usr/bin/env python3
"""Score an estimated alignment against a reference with FastSP (run in the container).

Usage: score.py <reference.fasta> <estimated.fasta>

Prints one JSON line with SP-Score, Modeler, SPFN, SPFP, TC and
SPFN_SPFP_mean = (SPFN + SPFP) / 2.
Both files must be inside the project directory, which the container mounts at /work.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DK = os.path.join(ROOT, "scripts", "dk.sh")
JAR = "vendor/FastSP/FastSP.jar"
METRICS = ["SP-Score", "Modeler", "SPFN", "SPFP", "TC"]


def container_path(path):
    rel = os.path.relpath(os.path.abspath(path), ROOT)
    if rel.startswith(".."):
        raise ValueError("{} is outside the project directory {}".format(path, ROOT))
    return rel


def parse(output):
    values = {}
    for line in output.splitlines():
        parts = line.rsplit(None, 1)
        if len(parts) == 2 and parts[0] in METRICS:
            values[parts[0]] = float(parts[1])
    return values


def score(reference, estimated):
    cmd = [DK, "java", "-jar", JAR, "-r", container_path(reference), "-e", container_path(estimated)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("FastSP exited {}:\n{}".format(proc.returncode, proc.stderr))
    values = parse(proc.stdout + "\n" + proc.stderr)
    missing = [m for m in METRICS if m not in values]
    if missing:
        raise RuntimeError("FastSP output is missing {}:\n{}{}".format(missing, proc.stdout, proc.stderr))
    values["SPFN_SPFP_mean"] = (values["SPFN"] + values["SPFP"]) / 2
    return values


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    try:
        values = score(sys.argv[1], sys.argv[2])
    except (ValueError, RuntimeError) as e:
        sys.exit("score.py: {}".format(e))
    print(json.dumps(values))


if __name__ == "__main__":
    main()
