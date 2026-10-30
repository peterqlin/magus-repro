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

FAMILY = "strict"                        # a label for the tables, e.g. strict | adaptive | network | structure
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
| `kb` | per-backbone votes: bit j is set when backbone j aligns a letter pair of the two columns |
| `backbone_em` | posterior that the edge is true, with each backbone a noisy annotator (one-coin Dawid–Skene EM on `kb`) |
| `chain_offset` | columns between the edge and the heaviest non-crossing chain of edges (k ≥ 2) between its two subsets |
| `diag_support` | how many of `(a-1, b-1)` and `(a+1, b+1)` are edges too (0, 1 or 2) |
| `best_ratio` | `(ra, rb)`: `w` over the heaviest edge from `a` into `b`'s subset, and from `b` into `a`'s |
| `occupancy` | per node: fraction of its subset's sequences with a residue in the column |
| `opal_pairs` | letter pairs that OPAL's alignment of the edge's two subset alignments puts in one column |
| `opal_missing()` | `(a, b, pairs)` for the column pairs OPAL aligns that have no edge |

`occupancy` and `opal_pairs` read the subset alignments (the hook sets `g.subset_paths`; `opal_pairs` runs OPAL on
every pair of subsets, `graphmods/evidence.py`). Strategies that use them set `NEEDS_INPUTS = True`, so
`tests/test_strategies.py`, which has no subset alignments, skips them.

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

  A whole merge can also run MAGUS's own merge as a step (`merge.magus_merge`), on other backbones or subsets or
  with another graph strategy. Work shared by a strategy's settings (backbones, group merges) is built once per
  dataset in `merge.shared_dir`. Backbone builds are reported as `backbone_s` and left out of `merge_s`; other shared
  work is charged to every setting.
  - `more_backbones` (`evidence`): MAGUS's merge with a fresh set of r backbones of m sequences, built by MAGUS,
    optionally cut at k ≥ cutoff · r.
  - `custom_backbones` (`evidence`): backbones aligned with another MAFFT method (L-INS-i, G-INS-i, FFT-NS-2),
    added to the run's own or used instead of them. `pick=spread` picks per subset the sequences that fill columns
    few others fill.
  - `iterate` (`iterate`): MAGUS's merge, then again with the edges the first alignment did not use down-weighted
    (or the ones it used boosted).
  - `consensus_runs` (`iterate`): the 40 backbones of `more_backbones` r=40 in 4 groups, each merged on its own;
    the final merge on all 40 weights each edge by how many of the 4 group merges align its two columns.
  - `subset_repair` (`repair`): splits subset columns whose residues the backbones put in different columns
    (`graphmods/repair.py`), then MAGUS's merge on the repaired subsets. It is the only strategy that can change the
    subset alignments' own residue pairs.
- **Ceilings** (`FAMILY = "ceiling"`): `g.true_pairs` and `g.true_missing()` give, from the reference alignment,
  the true residue pairs of each edge and the true column pairs MAGUS has no edge for. `g.true_w` counts, per edge,
  the residue pairs the backbones aligned across it (the pairs `w` counts) that the reference also aligns
  (`graphmods/oracle.py`; it checks that its backbone mapping reproduces MAGUS's `w`). `graphmods.replay` passes the
  reference in `$GRAPHMODS_REFERENCE`. The tables list ceilings separately and leave them out of the Holm
  correction.
  - `oracle_edges`: MAGUS's graph with every false edge deleted. By default an edge is false when no residue pair of
    its two columns is aligned in the reference. With `f`, it is false unless more than a fraction `f` of its
    backbone-aligned pairs are (`f = 0.5`: the majority rule), which is the best any filter of the backbone evidence
    could do.
  - `oracle_graph`: the graph built from true homologies, i.e. a merge of these subsets with perfect evidence.
    `add=0` only reweights MAGUS's edges; `norm=none` keeps raw counts instead of MAGUS's total weight.
  - `oracle_add`: MAGUS's graph plus the true column pairs it has no edge for.
  - `oracle_merge` (whole merge): no graph, MCL or trace. Per subset, an order-preserving assignment of its columns
    to reference columns that puts the most residues in their own reference column; columns of different subsets
    assigned to the same reference column are merged. About the best these subset alignments allow.
- **The floor:** `python3 -m graphmods.spsplit --reference REF --estimate EST --subsets DIR` splits an alignment's
  SPFN and SPFP into residue pairs within one subset and across subsets. `floor_err` is the error left with every
  cross-subset pair right.
- **Errors inside the subsets:** `scripts/subset_errors.py` scores each subset alignment with FastSP against the
  reference restricted to its sequences, and splits MAGUS's final errors into within-subset pairs (which no graph
  change can fix, since the merge keeps each subset's columns) and cross-subset pairs. On ICC:
  `scripts/icc/submit_subset_errors.sh` → `results/ceiling_subsets/`, `results/ceiling_subset_errors.csv`.

### The graph-step strategies added for the merge-step study

| strategy | family | idea |
|---|---|---|
| `chain_filter` | structure | down-weight edges more than d columns off the heaviest non-crossing chain between their subsets |
| `diagonal` | structure | down-weight edges without neighbours on the diagonal |
| `gappy_discount` | structure | weight × (smaller column occupancy)^γ, or delete edges between columns below occupancy θ |
| `reciprocal` | network | keep an edge when it is close to the heaviest edge of its endpoints into each other's subset |
| `backbone_em` | adaptive | weight × (or cut at) the Dawid–Skene posterior |
| `opal_evidence` | evidence | add OPAL's pair counts to `w`, keep only edges OPAL supports, or use OPAL's counts alone; `missing=1` also adds the column pairs OPAL aligns that MAGUS has no edge for |
| `learned_weights` | learned | weight × (or cut at) a fitted probability that the edge's pairs are true (below) |

### Learned weights

`learned_weights` applies a fractional logistic regression from the edge features of `graphmods/learned.py` to the
fraction of an edge's weight that is true (`true_w / w`). `features=opal` adds OPAL's verdict on the edge to the
inputs. It is trained in three steps, since the labels need the reference:

1. `dump_edge_features` (a ceiling; it leaves the graph unchanged) writes up to 300,000 random edges per dataset,
   with features (both sets, so it runs OPAL) and labels, to `runs/_graphmods/edge_features/<name>.npz`.
2. `python3 scripts/graphmods_train.py` fits, per feature set, one model on the even replicates and one on the odd,
   and writes `results/graphmods_edge_model.json`. It prints each model's held-out log loss.
3. `learned_weights` scores a dataset with the model fitted on the other parity, so no dataset is scored by a model
   that saw it. The sweep passes the dataset name (`<condition>_R<replicate>`) as `$GRAPHMODS_NAME`.

On ICC, `scripts/icc/submit_learned.sh` submits the three steps as dependent jobs.

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
  `GRAPHMODS_ONLY` and `GRAPHMODS_TAG` run some strategies into their own rows, work dir and results files, and
  `GRAPHMODS_TIME` raises the per-dataset time limit (`scripts/icc/submit_graphmods.sh`).

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
