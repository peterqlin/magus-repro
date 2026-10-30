<!-- AI-assisted (Claude), exploration code for CS581 project -->
# graphmods: alignment-graph strategies hooked into MAGUS

`strategies/` is a folder of strategies, one file each, that change the alignment graph MAGUS builds in its
merge step. Everything else in MAGUS is unchanged: decomposition, subset and backbone alignment, MCL and the
trace. A sweep runs every strategy in the folder over its parameter grid on every dataset. It does this
merge-only, on each MAGUS run's own subsets and backbones, so every setting is compared with stock MAGUS on
identical inputs.

```
graphmods/   the package: hook, edge features, runners, FastSP scoring, tables
strategies/  one .py per strategy; the sweep picks up every file here
tests/       test_strategies.py (no MAGUS needed)
scripts/graphmods_reps.py   reps.tsv for the sweep from finished runs (runs/<name>/work)
```

## How it plugs into MAGUS

`python3 -m graphmods.run` is a drop-in for `magus`. At runtime it patches one function,
`magus.align.merge.graph_build.graph_builder.buildMatrix`, then calls MAGUS's own `main()`. MAGUS's source
(`vendor/MAGUS`, commit `MAGUS_COMMIT`) is not edited. With `--strategy magus`, the graph is MAGUS's own and so is
the alignment.

```
# stock MAGUS
scripts/dk.sh magus -i unaligned.fasta -d work -o out.fasta -np 4
# the same run with a strategy in the graph step
scripts/dk.sh python3 -m graphmods.run --strategy strict_k --param K=4 -- -i unaligned.fasta -d work -o out.fasta -np 4
```

The hook needs the package layout of MAGUS 39041fc; the late-2020 `magus.py` layout won't work. The image
provides numpy and scipy; scoring uses `vendor/FastSP/FastSP.jar` (override with `$FASTSP_JAR`).
`--graphbuildrestrict` is not supported.

## Writing a strategy

A strategy is a file `strategies/NAME.py`:

```python
"""One-line description."""
import numpy as np

FAMILY = "strict"                        # strict | adaptive | network | control
GRID = [{"K": K} for K in range(2, 11)]  # the sweep for this strategy

def apply(g, K):
    return np.where(g.k >= K, g.w, 0)    # new weight per cross-subset edge; 0 deletes it
```

`apply` gets a `graphmods.graph.EdgeGraph` `g`, with one entry per cross-subset edge (`g.a`, `g.b` are the node
ids). It returns the new weights, or `(weights, (add_a, add_b, add_w))` to also add edges. The edge features
available on `g` are:

| attribute | meaning |
|---|---|
| `w` | MAGUS's weight: letter pairs aligned between the two columns, summed over backbones |
| `k` | support: backbones that align at least one letter pair of the two columns |
| `n` | exposure: backbones that hold a letter in both columns |
| `poss` | possible letter pairs between the two columns over all backbones |
| `s` | normalised strength `w / poss`, in [0, 1] |
| `emb` | embeddedness: common neighbours of the two columns |
| `ovl` | neighbourhood overlap: `emb / (deg_a - 1 + deg_b - 1 - emb)` |
| `tc` | triadic-closure score (resource allocation on `s`) |
| `missing_tc()` | `(a, b, t, poss)` for missing pairs that are each other's best missing partner |
| `posterior(kind)` | mixture posterior that an edge is a true homology (`kind` = `binom` or `bb`) |

A feature is computed the first time it is used and cached per dataset. The cache keeps how long it took, and
the tables charge each setting the cold cost of every feature it uses. So `merge×` is what one MAGUS run with
that strategy would pay, relative to the control timed on the same machine.

### Changing the rest of the merge, or all of it

A strategy can do more than change the graph:

- **Rest of the merge** (`FAMILY = "merge"`): also define `magus_args(**params)`, returning MAGUS flags. They are
  appended after the caller's, so they win.
  - `strategies/trace.py` sets `--graphtracemethod` and `--graphtraceoptimize`.
  - `strategies/strict_k_optimize.py` combines the k ≥ K cutoff with the trace optimizer.
- **Whole merge** (`FAMILY = "whole"`): define `merge(job, **params)` instead of `apply`. `graphmods.run` then calls
  it in place of MAGUS. `job` holds the subset alignments, backbones, output path, work dir and thread count.
  `graphmods/merge.py` has the shared pieces: MAGUS's bundled tools, a UPGMA guide tree over the subsets and a
  progressive pairwise merge.
  - `mafft_merge`: `mafft --merge` on the 25 fixed subset alignments.
  - `clustalo_progressive`: Clustal Omega profile–profile merges along the guide tree.
  - `opal_progressive`: OPAL profile–profile merges along the guide tree (PASTA's DNA merger; `$OPAL_JAR`).
  - `hmm_merge`: UPP-like. An HMM is built from one backbone and every sequence is aligned to it.
- **Ceilings** (`FAMILY = "ceiling"`): `g.true_pairs` and `g.true_missing()` give, from the reference alignment,
  the true residue pairs of each edge and the true column pairs MAGUS has no edge for. `graphmods.replay` passes the
  reference in `$GRAPHMODS_REFERENCE`. The tables list ceilings separately and leave them out of the Holm
  correction.
  - `oracle_edges`: MAGUS's graph with every false edge deleted.
  - `oracle_graph`: the graph built from true homologies, i.e. a merge of these subsets with perfect evidence.

## Running a sweep

The sweep reads `runs/<name>/work`, which `run_one.sh` keeps, plus the dataset's reference alignment.

```
scripts/dk.sh python3 scripts/graphmods_reps.py                 # -> runs/graphmods_reps.tsv
scripts/dk.sh python3 -m graphmods.sweep --reps runs/graphmods_reps.tsv --out results/graphmods_rows.jsonl
scripts/dk.sh python3 -m graphmods.tables results/graphmods_rows.jsonl --md results/graphmods.md --csv results/graphmods.csv
scripts/dk.sh python3 tests/test_strategies.py                  # quick check, no MAGUS run needed
```

- **Restartability:** the sweep can be restarted; a (dataset, setting) pair already in the rows file is skipped.
- **Order:** the MAGUS control runs first on each dataset.
- **Options:** `--only strict_k,overlap` or `--families network` restrict the strategies, and `--names` restricts the datasets.
- **Scratch space:** runs live under `runs/_graphmods/`, and each run's outputs are deleted after scoring.
- **One run:** `python3 -m graphmods.replay` does a single merge-only run with its score.
- **On ICC:** `scripts/icc/submit_graphmods.sh` writes `runs/graphmods_reps.tsv` and submits one array task per
  dataset (every setting, rows in `runs/_graphmods/rows/<name>.jsonl`), then a collect job. That job runs
  `scripts/graphmods_collect.py` (→ `results/graphmods_rows.jsonl` and `results/graphmods_scores.csv`, scored like
  `results/scores.csv`) and `graphmods.tables` (→ `results/graphmods.md`, `results/graphmods.csv`).

Results of the 70-dataset sweep (on the project's own MAGUS(Fast) runs) are in `cs581/graphmods/results/` of
evanlin23/scratch.

## Checks (2026-10-25, in the image, Linux x86-64)

- `tests/test_strategies.py` passes. It covers every strategy at every grid point, `magus` leaving the graph unchanged,
  the feature cache and the cold-cost accounting.
- Control replay on the Step 3 smoke run (`--subsets runs/_smoke/work/subalignments --backbones runs/_smoke/work/graph`):
  - SPFN 0.107653, SPFP 0.096226 and TC 0.195420, identical to the full MAGUS run.
  - The alignment has the same 3808 columns as the full run, in a different order.
- `graphmods.sweep --only strict_k,triadic_drop` on the smoke run: 15 settings, no failures, 5.5 min. `graphmods.tables`
  then reads the rows.
