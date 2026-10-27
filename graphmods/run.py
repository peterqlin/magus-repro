# AI-assisted (Claude), exploration code for CS581 project
"""Run MAGUS with a graph strategy hooked in.

    python -m graphmods.run --strategy strict_k --param K=5 [--cache DIR] [--info FILE] -- <MAGUS arguments>

Everything after "--" goes to MAGUS unchanged, so this is a drop-in replacement for `python -m magus.main ...`:
  full run:    -- -i unaligned.fasta -d work -o out.fasta -np 4
  merge only:  -- -s SUBSET_DIR -b BACKBONE_FILES... -d work -o out.fasta -np 4 --graphclustermethod mcl \
                  --graphtracemethod minclusters --graphtraceoptimize false -f 4
"""
import argparse
import sys

from . import hook, registry


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        raise SystemExit("usage: python -m graphmods.run --strategy NAME [--param k=v ...] -- <MAGUS arguments>")
    i = argv.index("--")
    ap = argparse.ArgumentParser(prog="graphmods.run")
    ap.add_argument("--strategy", default="magus")
    ap.add_argument("--param", action="append", default=[], help="strategy parameter k=v (repeatable)")
    ap.add_argument("--strategies", help="strategies folder (default <repo>/strategies)")
    ap.add_argument("--cache", help="directory to cache the graph and features between runs on the same inputs")
    ap.add_argument("--info", help="write strategy info (edges kept / added, timings) to this JSON file")
    a = ap.parse_args(argv[:i])
    hook.install(a.strategy, registry.parse_params(a.param), a.strategies, a.cache, a.info)
    from magus.main import main as magus_main
    sys.argv = ["magus"] + argv[i + 1:]
    magus_main()


if __name__ == "__main__":
    main()
