# Progress log

Spec: `docs/spec.md` (the spec's layout shows `spec.md` at the repo root; it lives in `docs/` here and was left in place).

## Step 0 — Scaffold and config

**2026-10-23 14:18** — blocked on M2
**2026-10-23 14:25** — M2 satisfied; step COMPLETE

Done:
- `git init`; created `docker/`, `vendor/`, `data/raw/`, `data/datasets/`, `scripts/`, `runs/`, `results/`; `.gitignore` excludes `data/raw/*`, staged datasets, run dirs and `vendor/`.
- `config.env` written. Host: arm64 macOS, 6 cores → `TOTAL_CORES=5`, `PARALLEL_JOBS=1`.

Verification:
| Check | Result |
|---|---|
| `source config.env` defines all vars, all but MAGUS_COMMIT non-empty | PASS |
| `docker info` exits 0 | PASS (Docker Desktop, VM: 6 CPUs, 3.8 GiB RAM, aarch64) |
| `data/raw/` contains M2 archive(s) | PASS — `Datasets.zip` (392 MB; top-level groups: ROSE, RNASim, Gutell, balibase). No separate results archive provided. (Initially FAIL: empty.) |
| Free disk ≥ 20 GB | PASS (321 GiB free) |

Notes:
- Docker VM RAM is 3.8 GiB, below the ≥ 16 GB M1 recommends.
- Host is Apple Silicon, so the `linux/amd64` image runs under emulation; expect MAFFT/MCL to be noticeably slower than native.
- GNU `parallel` is not installed on the host (relevant for Step 9; can run it via the container instead).

## Step 1 — Pin MAGUS

**2026-10-23 14:30** — cloned `vendor/MAGUS` (103 commits); awaiting M4 approval

Proposed pin: `416ec513e4ef6bd5393f6ffb705cc3746a223bcd` (2020-09-20, "Renaming to MAGUS") — the last commit before `4137b1a` (2020-10-26, "First version of scalability"), which begins the recursive/scalability work. It predates the `Datasets.zip` archive timestamps (2020-09-25). HEAD for comparison: `39041fc` (2024-03-25, "Merge pull request #33 from lrauschning/master").

**2026-10-23 14:40** — pin approved (M4); step COMPLETE

Done: `git -C vendor/MAGUS checkout 416ec51`; `MAGUS_COMMIT` set in `config.env`.

Entry point: `magus.py` at the repo root, run as `python3 magus.py` (HEAD instead has a `magus` package with a `magus = "magus.main:main"` console script).

Defaults at the pinned commit (from the `magus.py` argparse):
| Setting | Flag | Pinned default | HEAD (39041fc) default |
|---|---|---|---|
| Guide tree | `-t/--guidetree` | `None` → PASTA-style tree: MAFFT on a 300-seq skeleton (`--decompskeletonsize 300`), HMM-extend all sequences, FastTree | `fasttree` (also `fasttree-noml`, `clustal`, `parttree` or a path) |
| Decomposition | `--decompstrategy` | `pastastyle` | `pastastyle` |
| Max # subsets | `--maxnumsubsets` | 25 | 25 |
| Max subset size | `--maxsubsetsize` | 50 | 50 |
| Backbone count | `-r/--mafftruns` | 10 | 10 |
| Backbone size | `-m/--mafftsize` | 200 | 200 |
| Graph build | `--graphbuildmethod` | `mafft` | `mafft` |
| Graph cluster | `--graphclustermethod` | `mcl` (inflation `-f` 4) | `mcl` (4) |
| Graph trace | `--graphtracemethod` | `minclusters` | `minclusters` |
| Trace optimize | `--graphtraceoptimize` | False | False |
| Threads | `-np/--numprocs` | −1 → `os.cpu_count()` | −1 → `os.cpu_count()` |

HEAD-only options (absent at the pin): `-c/--constrain` (true), `--recurse` (true), `--recurseguidetree` (fasttree), `--recursethreshold` (200), `--alignsizelimit` (100 GB), `--onlyguidetree`, `--overwrite`, `--version`.

Python dependency: `dendropy` (the only non-stdlib import). The bundled MCL binaries are x86-64 Linux ELF; `tools/mafft/mafft` is a bash wrapper around `tools/mafft/mafftdir`.

Verification:
| Check | Result |
|---|---|
| `rev-parse HEAD` == `MAGUS_COMMIT` | PASS (`416ec513e4ef6bd5393f6ffb705cc3746a223bcd`) |
| `git status --porcelain` empty | PASS |
| Defaults table and entry point in PROGRESS.md | PASS |
