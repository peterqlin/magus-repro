# AI-assisted (Claude), exploration code for CS581 project
"""Discover graph strategies: every *.py file in the strategies folder (default: <repo>/strategies, or
$GRAPHMODS_STRATEGIES) that defines

    FAMILY = "strict" | "adaptive" | "network" | "merge" | "whole" | "ceiling" | "control"
    GRID   = [ {param: value, ...}, ... ]           # the sweep for this strategy
    def apply(g, **params): ...                      # g: graphmods.graph.EdgeGraph
    def magus_args(**params): ...                    # optional: extra MAGUS flags for the rest of the merge
    def merge(job, **params): ...                    # instead of apply: replace MAGUS's whole merge (merge.py)

apply returns the new weight of every existing cross-subset edge (array aligned with g.a / g.b; 0 deletes the edge),
or a pair (weights, (add_a, add_b, add_w)) to also add edges. magus_args returns MAGUS command-line flags (e.g. the
trace method) appended after the caller's, so they win. The module docstring is the strategy's description.
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(os.path.dirname(HERE), "strategies")


def strategies_dir(path=None):
    return os.path.abspath(path or os.environ.get("GRAPHMODS_STRATEGIES") or DEFAULT_DIR)


def load(name, path=None):
    f = os.path.join(strategies_dir(path), name + ".py")
    if not os.path.exists(f):
        raise SystemExit(f"no strategy {name!r} in {strategies_dir(path)}")
    spec = importlib.util.spec_from_file_location("graphmods_strategy_" + name, f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr in ("FAMILY", "GRID"):
        if not hasattr(mod, attr):
            raise SystemExit(f"strategy {name} lacks {attr}")
    if not hasattr(mod, "apply") and not hasattr(mod, "merge"):
        raise SystemExit(f"strategy {name} defines neither apply nor merge")
    mod.NAME = name
    return mod


def all_strategies(path=None, families=None):
    d = strategies_dir(path)
    out = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".py") and not f.startswith("_"):
            m = load(f[:-3], d)
            if families is None or m.FAMILY in families:
                out.append(m)
    return out


def variant_name(name, params):
    """strict_k + {"K": 5} -> "strict_k-K5"; parameters in the GRID's key order."""
    if not params:
        return name
    return name + "-" + "-".join(f"{k}{v}" for k, v in params.items())


def parse_params(items):
    """["K=5", "kind=bb"] -> {"K": 5, "kind": "bb"} (ints / floats parsed)."""
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        for cast in (int, float):
            try:
                v = cast(v)
                break
            except ValueError:
                pass
        out[k] = v
    return out
