# Progress log

Spec: `docs/spec.md` (the spec's layout shows `spec.md` at the repo root; it lives in `docs/` here and was left in place).

## Step 0 — Scaffold and config

**2026-10-23 14:18** — blocked on M2
**2026-10-23 14:25** — M2 satisfied; step COMPLETE

Done:
- `git init`; created `docker/`, `vendor/`, `data/raw/`, `data/datasets/`, `scripts/`, `runs/`, `results/`; `.gitignore` excludes `data/raw/*`, staged datasets and run dirs. (`vendor/` was also ignored at first; see the Step 1 addendum.)
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

**Addendum (2026-10-23 ~20:00 UTC)** — at the user's request, `vendor/MAGUS` is now a git submodule (url `https://github.com/vlasmirnov/MAGUS`, recorded at `416ec51`) instead of an untracked, gitignored clone. `scripts/build_image.sh` runs `git submodule update --init vendor/MAGUS` and refuses to build unless `vendor/MAGUS` is at `MAGUS_COMMIT` with no uncommitted changes. It labels the image `magus.commit=<sha>`. Image rebuilt (layers unchanged); label verified = `416ec513e4ef6bd5393f6ffb705cc3746a223bcd`; a deliberately wrong `MAGUS_COMMIT` makes the build exit 1.

## Step 2 — Build the Docker image

**2026-10-23 14:50** — step COMPLETE

Done:
- `docker/Dockerfile`: `python:3.9-slim-bookworm` (linux/amd64), GNU `time`, `procps`, `openjdk-17-jre-headless`, `dendropy==4.5.2` (2020-era release); `vendor/MAGUS` copied to `/opt/MAGUS` (without `.git`), bundled tools made executable. Upstream Dockerfile not touched (none exists at the pin).
- `.dockerignore` limits the build context to `vendor/MAGUS`, so `data/raw` isn't sent to the daemon.
- `scripts/build_image.sh` builds with `--platform $DOCKER_PLATFORM`; `scripts/dk.sh` runs commands with the project at `/work`, the host UID/GID, `HOME=/tmp`.
- Image `magus-repro:pinned` = `sha256:d6900c262559`.

Verification:
| Check | Result |
|---|---|
| `dk.sh python3 /opt/MAGUS/magus.py -h` exits 0, shows Step 1 flags | PASS (-t, --maxnumsubsets, --maxsubsetsize, -r, -m, --graphtracemethod, -np all present) |
| Bundled MAFFT runs | PASS — `v7.450 (2019/Aug/23)` |
| Bundled MCL runs | PASS — `mcl 14-137` |
| `/usr/bin/time -v true` prints max RSS | PASS |
| `java -version` exits 0 | PASS — OpenJDK 17.0.20.1 |
| Output files owned by host user | PASS |

## Step 3 — Smoke test MAGUS

**2026-10-23 19:28 UTC** — attempt 1 ABORTED at the user's request after ~22 min. It was still in the first phase (MAFFT L-INS-i on the 300-seq guide-tree skeleton, 4 threads, ~500 MiB RSS) under QEMU amd64 emulation. `runs/_smoke/` removed. The user is enabling Rosetta for x86/amd64 emulation in Docker Desktop before retrying.

**2026-10-23 19:52 UTC** — attempt 2, with Docker Desktop's Rosetta x86/amd64 emulation enabled (`UseVirtualizationFrameworkRosetta: true`); step COMPLETE

Done:
- Input: `vendor/MAGUS/example/unaligned_sequences.txt` (1000 seqs) → `runs/_smoke/unaligned.fasta`.
- Command: `scripts/dk.sh /usr/bin/time -v -o runs/_smoke/time.txt python3 /opt/MAGUS/magus.py -d runs/_smoke/work -i runs/_smoke/unaligned.fasta -o runs/_smoke/magus.aln -np 4`
- Wrote `scripts/validate_alignment.py`.

Timing (from the MAGUS log):
| Phase | Time |
|---|---|
| Guide tree (MAFFT 300-seq skeleton + HMM extend + FastTree) | 350 s (attempt 1 under QEMU: not done after ~22 min) |
| 25 subset alignments | 134 s |
| 10 backbones (4 workers × `--thread 4`) | ~19 min (20:00:20 → 20:19:16) |
| Graph + MCL + minclusters trace + write | ~26 s (trace: 1017 clusters) |
| **Total** | **27:27 wall** (MAGUS: 1646.5 s); max RSS 531 MiB |

Verification:
| Check | Result |
|---|---|
| MAGUS exits 0, output non-empty | PASS — exit 0; `magus.aln` 3.8 MB, 1000 seqs |
| `validate_alignment.py` passes on the smoke output | PASS (no all-gap-column warning) |
| Fails on a copy with one residue changed | PASS — exit 1, "1 rows don't degap to their input sequence" (SEJG, G→A) |
| Fails on a copy with one sequence removed | PASS — exit 1, "1 IDs missing from alignment" (SEJG) |

Extra check: the validator also passes on the example's `true_alignment.txt`.

Notes:
- GNU time's "Maximum resident set size" is the peak of the single largest process (MAFFT or Python), not the sum over concurrent MAFFT workers; `docker stats` showed ~1.8 GiB for the whole container during the backbone phase. Relevant to the `max_rss_mb` column in Step 10.
- `-np 4` gives 4 concurrent MAFFT backbones × 4 threads each = 16 threads on the VM's 6 CPUs.
