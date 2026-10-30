# AI-assisted (Claude), exploration code for CS581 project
"""Sweep tables from rows.jsonl files: every variant against the MAGUS control on the same dataset (paired).

    python -m graphmods.tables ROWS.jsonl [ROWS2.jsonl ...] [--md OUT.md] [--csv OUT.csv] [--exclude NAME,...]

Per variant: n datasets, mean change in SPFN, SPFP and err = (SPFN + SPFP) / 2 versus MAGUS (percentage points; negative =
fewer errors), wins / ties / losses at |change in err| <= 0.1, two-sided Wilcoxon signed-rank p (unadjusted, and Holm-adjusted
across every variant in the table),
mean change in err per condition, and the median ratio of merge time to MAGUS's merge time on the same dataset (both
under the hook, from the same cached graph; each variant charged the cold cost of the features it uses, see cost_s).
"""
import argparse
import collections
import csv
import json
import statistics as st

FAMILY_ORDER = ["strict", "adaptive", "network", "merge", "whole", "ceiling"]


def load(paths):
    rows = {}
    for p in paths:
        for line in open(p):
            line = line.strip()
            if line:
                r = json.loads(line)
                r["_src"] = p
                # a rerun of the same (dataset, variant) replaces the earlier row; every file's control is kept, so a
                # variant's merge time is compared with the control timed on the same machine (same rows file)
                key = (r["name"], r["variant"], p) if r["variant"] == "magus" else (r["name"], r["variant"])
                rows[key] = r
    return list(rows.values())


def cost_s(r):
    """Merge time as one MAGUS run with this strategy would pay it: the run's wall time, minus features it computed,
    plus the cold compute time of every feature it used (whether computed in this run or loaded from the cache)."""
    if r.get("merge_s") is None:
        return None
    cold = r.get("feature_cold_s")
    if cold is None:  # rows from before feature accounting
        return r["merge_s"]
    if any(v is None for v in cold.values()):
        return None
    here = sum(v for v in (r.get("feature_s") or {}).values() if isinstance(v, (int, float)))
    return r["merge_s"] - here + sum(cold.values())


def wilcoxon_p(d):
    from scipy.stats import wilcoxon
    d = [x for x in d if x != 0]
    if len(d) < 2:
        return None
    return float(wilcoxon(d).pvalue)


def summarize(rows):
    ctrl = {r["name"]: r for r in rows if r["variant"] == "magus" and not r.get("failed")}
    ctrl_src = {(r["name"], r.get("_src")): r for r in rows if r["variant"] == "magus" and not r.get("failed")}
    tctrl = lambda r: ctrl_src.get((r["name"], r.get("_src")), ctrl[r["name"]])  # control timed alongside r
    conds = sorted({r.get("condition") for r in ctrl.values()}, key=str)
    by = collections.defaultdict(list)
    meta = {}
    for r in rows:
        if r["variant"] == "magus":
            continue
        meta.setdefault(r["variant"], (r.get("family"), r.get("strategy"), r.get("params")))
        by[r["variant"]].append(r)
    out = []
    for v, rs in by.items():
        fam, strat, params = meta[v]
        ok = [r for r in rs if not r.get("failed") and r["name"] in ctrl]
        failed = len(rs) - len(ok)
        if not ok:
            out.append(dict(variant=v, family=fam, strategy=strat, params=params, n=0, failed=failed))
            continue
        d = [r["err"] - ctrl[r["name"]]["err"] for r in ok]
        dfn = [r["SPFN"] - ctrl[r["name"]]["SPFN"] for r in ok]
        dfp = [r["SPFP"] - ctrl[r["name"]]["SPFP"] for r in ok]
        tm = [cost_s(r) / cost_s(tctrl(r)) for r in ok if cost_s(r) is not None and cost_s(tctrl(r))]
        kept = [r["kept_edges"] / r["edges"] for r in ok if r.get("edges")]
        row = dict(variant=v, family=fam, strategy=strat, params=params, n=len(ok), failed=failed,
                   d_err=st.mean(d), d_spfn=st.mean(dfn), d_spfp=st.mean(dfp),
                   wins=sum(x < -0.1 for x in d), ties=sum(abs(x) <= 0.1 for x in d), losses=sum(x > 0.1 for x in d),
                   p=wilcoxon_p(d), merge_x=st.median(tm) if tm else None, kept_frac=st.mean(kept) if kept else None,
                   added=st.mean([r.get("added_edges", 0) for r in ok]))
        for c in conds:
            dc = [r["err"] - ctrl[r["name"]]["err"] for r in ok if r.get("condition") == c]
            row["d_" + str(c)] = st.mean(dc) if dc else None
        out.append(row)
    holm(out)
    fam_rank = {f: i for i, f in enumerate(FAMILY_ORDER)}
    out.sort(key=lambda r: (fam_rank.get(r["family"], 9), r["strategy"] or "", tuple((r["params"] or {}).values())))
    return out, conds, ctrl


def holm(out):
    """Holm step-down adjustment of the Wilcoxon p-values across all variants in the table but the ceilings."""
    ps = sorted((r["p"], i) for i, r in enumerate(out) if r.get("p") is not None and r.get("family") != "ceiling")
    run = 0.0
    for rank, (p, i) in enumerate(ps):
        run = max(run, min(1.0, (len(ps) - rank) * p))
        out[i]["p_holm"] = run


def fmt(x, nd=3, sign=True):
    if x is None:
        return "–"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def markdown(out, conds, ctrl):
    L = [f"MAGUS control on {len(ctrl)} datasets: mean SPFN {st.mean(r['SPFN'] for r in ctrl.values()):.3f}, "
         f"SPFP {st.mean(r['SPFP'] for r in ctrl.values()):.3f}, err {st.mean(r['err'] for r in ctrl.values()):.3f} (%).", ""]
    head = ("| variant | n | ΔSPFN | ΔSPFP | Δerr | W/T/L | p | p (Holm) | " + " | ".join(f"Δerr {c}" for c in conds) +
            " | merge× | edges kept | added |")
    rule = "|---" * (11 + len(conds)) + "|"

    def line(r):
        if not r["n"]:
            return f"| {r['variant']} | 0 (failed {r['failed']}) |" + " |" * (9 + len(conds))
        p = "–" if r["p"] is None else f"{r['p']:.2g}"
        ph = "–" if r.get("p_holm") is None else f"{r['p_holm']:.2g}"
        cells = " | ".join(fmt(r.get("d_" + str(c))) for c in conds)
        fail = f" (+{r['failed']} failed)" if r["failed"] else ""
        return (f"| {r['variant']} | {r['n']}{fail} | {fmt(r['d_spfn'])} | {fmt(r['d_spfp'])} | {fmt(r['d_err'])} | "
                f"{r['wins']}/{r['ties']}/{r['losses']} | {p} | {ph} | {cells} | {fmt(r['merge_x'], 2, False)} | "
                f"{fmt(r['kept_frac'], 3, False)} | {r['added']:.0f} |")

    best = {}
    for r in out:
        if r["n"] and (r["strategy"] not in best or r["d_err"] < best[r["strategy"]]["d_err"]):
            best[r["strategy"]] = r
    L += ["## best setting per strategy (lowest mean Δerr)", "", head, rule]
    L += [line(r) for r in out if best.get(r["strategy"]) is r]
    L.append("")
    for fam in FAMILY_ORDER + sorted({r["family"] for r in out} - set(FAMILY_ORDER), key=str):
        rs = [r for r in out if r["family"] == fam]
        if not rs:
            continue
        L += [f"## {fam}", "", head, rule] + [line(r) for r in rs] + [""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", nargs="+")
    ap.add_argument("--md")
    ap.add_argument("--csv")
    ap.add_argument("--exclude", help="comma-separated dataset names to leave out (e.g. 1000M1_R16)")
    a = ap.parse_args()
    rows = load(a.rows)
    if a.exclude:
        drop = set(a.exclude.split(","))
        rows = [r for r in rows if r["name"] not in drop]
    out, conds, ctrl = summarize(rows)
    md = markdown(out, conds, ctrl)
    if a.md:
        open(a.md, "w").write(md + "\n")
    else:
        print(md)
    if a.csv:
        keys = list(out[0].keys()) if out else []
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted({k for r in out for k in r}), extrasaction="ignore")
            w.writeheader()
            for r in out:
                w.writerow({k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in r.items()})


if __name__ == "__main__":
    main()
