# AI-assisted (Claude), exploration code for CS581 project
"""FastSP scoring: SPFN, SPFP, TC of an estimated alignment against a reference (fractions, as FastSP prints them).
FastSP.jar location: $FASTSP_JAR (default vendor/FastSP/FastSP.jar in this repo). The estimate is restricted to the
reference's sequences and both are upper-cased first."""
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FASTSP_JAR = os.environ.get("FASTSP_JAR", os.path.join(ROOT, "vendor", "FastSP", "FastSP.jar"))


def read_fasta(path):
    seqs, name = {}, None
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith(">"):
            name = line[1:].strip()
            seqs[name] = []
        elif name is not None:
            seqs[name].append(line.strip())
    return {k: "".join(v) for k, v in seqs.items()}


def write_fasta(seqs, path):
    with open(path, "w") as f:
        for k, v in seqs.items():
            f.write(f">{k}\n{v}\n")


def fastsp(reference, estimate):
    ref = {k: v.upper() for k, v in read_fasta(reference).items()}
    est = {k: v.upper() for k, v in read_fasta(estimate).items()}
    est = {k: est[k] for k in ref if k in est}
    with tempfile.TemporaryDirectory() as tmp:
        r, e = os.path.join(tmp, "ref.fa"), os.path.join(tmp, "est.fa")
        write_fasta(ref, r)
        write_fasta(est, e)
        out = subprocess.run(["java", "-Xmx" + os.environ.get("FASTSP_XMX", "4g"), "-jar", FASTSP_JAR, "-r", r, "-e", e],
                             capture_output=True, text=True, check=True)
    stats = {}
    for line in (out.stdout + out.stderr).splitlines():
        t = line.split()
        if len(t) == 2 and t[0] in ("SP-Score", "Modeler", "SPFN", "SPFP", "TC"):
            stats[t[0]] = float(t[1])
    return {"SPFN": stats["SPFN"], "SPFP": stats["SPFP"], "TC": stats.get("TC")}
