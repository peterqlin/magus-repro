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
