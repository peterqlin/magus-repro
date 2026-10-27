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

**Addendum (2026-10-25)** — **re-pinned to the newest commit, `39041fc8da5dcb44c95e90c212c667cf225ec129`** (2024-03-25, "Merge pull request #33 from lrauschning/master", HEAD of `vlasmirnov/MAGUS`), at the team's request: the project's own methods are built on this version of MAGUS. `vendor/MAGUS` submodule and `MAGUS_COMMIT` updated.

- Entry point: the `magus` package (`magus.main:main`), run as `magus` in the image (see Step 2 addendum); `magus.py` no longer exists.
- Defaults: the HEAD column of the table above. Step 1's PASTA-style starting tree is still the default: `-t fasttree` builds "PASTA-style FastTree initial tree … with skeleton size 300" (MAFFT L-INS-i on a 300-sequence skeleton, HMM-extend the rest, FastTreeMP), as the Step 3 log shows.
- New defaults absent at the old pin: `-c/--constrain` true, `--recurse` true with `--recursethreshold 200` (only subsets larger than 200 sequences are aligned recursively; with `--maxsubsetsize 50` and 25 subsets of 1000 sequences none are).

| Check | Result |
|---|---|
| `rev-parse HEAD` == `MAGUS_COMMIT` | PASS (`39041fc8da5dcb44c95e90c212c667cf225ec129`) |
| `git status --porcelain` empty (in `vendor/MAGUS`) | PASS |

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

**Addendum (2026-10-25)** — rebuilt for the new pin. `docker/Dockerfile`: MAGUS is now a package with its tools under `magus/tools/`, so it is copied to `/opt/MAGUS` and run from there on `PYTHONPATH` (the tools stay where `magus.configuration` looks for them); `/usr/local/bin/magus` is upstream's console script (`python3 -m magus.main`). Added `libgomp1`: the bundled FastTreeMP (the default guide tree) is linked against OpenMP and does not start without it. Built and checked on a Linux x86-64 host (native, 4 cores, Docker 29.8.2), label `magus.commit=39041fc8da5dcb44c95e90c212c667cf225ec129`; rebuild locally with `scripts/build_image.sh`.

| Check | Result |
|---|---|
| `dk.sh magus -h` exits 0, shows Step 1 flags | PASS (-t, --maxnumsubsets, --maxsubsetsize, -r, -m, --graphtracemethod, -np; also -c, --recurse) |
| Bundled MAFFT runs | PASS — `v7.450 (2019/Aug/23)` |
| Bundled MCL runs | PASS — `mcl 14-137` |
| Bundled FastTreeMP runs | PASS — `FastTree Version 2.1.11 SSE3, OpenMP` |
| `/usr/bin/time -v true` prints max RSS | PASS |
| `java -version` exits 0 | PASS — OpenJDK 17.0.21 |

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

**Addendum (2026-10-25)** — smoke test rerun at the new pin (same host as the Step 2 addendum). Command: `scripts/dk.sh /usr/bin/time -v -o runs/_smoke/time.txt magus -d runs/_smoke/work -i runs/_smoke/unaligned.fasta -o runs/_smoke/magus.aln -np 4`.

| Phase | Time |
|---|---|
| Guide tree (MAFFT 300-seq skeleton + HMM extend + FastTreeMP) | 262 s |
| Subset alignments, 10 backbones, graph, MCL | 20:26 |
| Trace + write (1007 clusters, trace of 1036) | 3 s |
| **Total** | **24:51 wall** (MAGUS: 1490.5 s); max RSS 451 MiB |

| Check | Result |
|---|---|
| MAGUS exits 0, output non-empty | PASS — exit 0; `magus.aln` 3.8 MB, 1000 seqs |
| `validate_alignment.py` passes on the smoke output | PASS |
| Fails on a copy with one residue changed | PASS — exit 1, "1 rows don't degap to their input sequence" (SHEF) |
| Fails on a copy with one sequence removed | PASS — exit 1, "1 IDs missing from alignment" (SHEF) |
| Step 4: smoke alignment vs itself | PASS — SPFN 0.0, SPFP 0.0, TC 1.0 |

For reference, vs the example's `true_alignment.txt`: SPFN 0.1077, SPFP 0.0962, TC 0.195 (old pin: 0.0994, 0.0945, 0.173).

## Step 4 — Set up FastSP

**2026-10-23 20:35 UTC** — step COMPLETE

Done:
- `vendor/FastSP` added as a git submodule (`https://github.com/smirarab/FastSP`, at `146c4096d2ec96c1227188b3aed18d09440bf4c9`, 2021-08-11, "1.7.1: small logging change"), the same approach as MAGUS. It ships a prebuilt `FastSP.jar` (FastSP 1.7.1), so no build was needed. It runs in the container via the `/work` mount.
- `scripts/score.py <reference> <estimated>`: runs `java -jar vendor/FastSP/FastSP.jar -r … -e …` via `dk.sh`, parses SP-Score, Modeler, SPFN, SPFP and TC from stdout+stderr, and prints one JSON line. It exits non-zero if FastSP fails, a metric is missing, or a path is outside the project.

Verification:
| Check | Result |
|---|---|
| Smoke alignment vs itself: SPFN = 0, SPFP = 0 | PASS — `{"SP-Score": 1.0, "Modeler": 1.0, "SPFN": 0.0, "SPFP": 0.0, "TC": 1.0}` |
| vs a copy with one column's gaps shifted: SPFN > 0 or SPFP > 0 | PASS — column 1, 2 rows' residue/gap swapped (copy still passes `validate_alignment.py`): SPFN 4.04e-6, SPFP 4.06e-6, TC 0.99924 |

Extra checks: a path outside the project is rejected (exit 1). For reference, the smoke output vs the example's `true_alignment.txt` scores SPFN 0.0994, SPFP 0.0945, TC 0.173.

## Step 5 — Inventory and stage the ROSE datasets

**2026-10-23 20:45 UTC** — step COMPLETE

Done:
- Extracted `data/raw/Datasets.zip` → `data/raw/extracted/Datasets/` (`unzip -n`, zip untouched).
- `scripts/inventory.py` walks the extracted tree and classifies each dataset directory's files; full output in `data/inventory.tsv` (243 dirs: 200 ROSE, 30 RNASim, 4 Gutell, 8 balibase, 1 stray `outputs/`).
- `scripts/stage_rose.py` stages the 60 ROSE datasets and is idempotent (a rerun reported 60 × "unchanged").

Archive structure (Datasets/):
| Group | Replicates | Reference file | Unaligned file | Other files |
|---|---|---|---|---|
| ROSE/1000{M1–M4,L1–L3,S1–S3} | R0–R19 (20 each), 1000 seqs | `rose.aln.true.fasta` (leaves only) | none | `rose.aln.true.internal.fasta` (includes ancestral seqs; not used), `random.tree`, `rose.mt`, `rose.mt.internal`, `rose.tt` |
| RNASim/1000 | R0–R19 (20), 1000 seqs | `true_align.txt` | none | `true_tree.tre` |
| RNASim/10000 | 10, 10000 seqs | `true_align.txt` | none | `true_tree.tre` |
| Gutell/{16S.3, 16S.B.ALL, 16S.M, 16S.T} | 1 each | `true_align_clean.txt` | none | `cleaned.alignment.fasta(.name_map)`, reference trees |
| balibase/RV100_* | 8 | `true.fasta` | none | `true.tt` |

Staging decisions:
- Reference = `rose.aln.true.fasta`; `unaligned.fasta` = its rows with gaps stripped (the archive has no unaligned files).
- Replicate numbering: archive `R<k>` (0-based) → `<cond>_R<k+1>` (`R0` → `R01`, …, `R19` → `R20`). Each staged dir has `source.txt` naming its archive file.
- All-gap column stripping is applied, but the archive references had none (0 removed in all 60).
- Ignored: `ROSE/1000M1/R4/outputs/` holds `logdet.txt` and `logdet_2.txt` (LogDet distance matrices left over from some earlier analysis). It is the only such directory, and R4's own files are the standard set.

Archive contents relevant to later steps:
- **1000-sequence RNASim samples: YES** — `RNASim/1000/R0–R19` (20 samples), so Step 6 picks 10 of them with `RNASIM_SEED` and M3 isn't needed.
- **Published MAGUS alignments or scores: NO** — the archive holds only true alignments and trees; no estimated alignments or score files. Step 11 will need `published_manual.csv` from the paper's figures.

Verification:
| Check | Result |
|---|---|
| 20 staged dirs per ROSE condition (60 total) | PASS — 1000M1: 20, 1000L1: 20, 1000S1: 20 |
| Each unaligned has exactly 1000 seqs, unique IDs | PASS (60/60) |
| `validate_alignment.py unaligned reference` passes | PASS (60/60) |
| No reference has all-gap columns | PASS (0 total) |

Dataset shape: reference width 1000M1 3443–4517, 1000L1 3309–4446, 1000S1 1898–2357 columns; mean unaligned length ≈ 1000–1015 nt in all three.

**Addendum (2026-10-25)** — restaged with **1000L3 instead of 1000L1** (the professor's dataset list is 1000M1, 1000S1, 1000L3) and with the **archive's own replicate names**: archive `R<k>` → `<cond>_R<k>` (`R0`–`R19`), no renumbering, so a name means the same replicate here, in the archive and in the project's other results. `stage_rose.py`: `CONDITIONS = ["1000M1", "1000L3", "1000S1"]`, `name = <cond>_R<k>`. Same archive as above (`inventory.py` output identical to `data/inventory.tsv`, 244 lines). Rerun: 60 × "written", then 60 × "unchanged".

| Check | Result |
|---|---|
| 20 staged dirs per ROSE condition (60 total) | PASS — 1000M1: 20, 1000L3: 20, 1000S1: 20 |
| Each unaligned has exactly 1000 seqs, unique IDs | PASS (60/60) |
| `validate_alignment.py unaligned reference` passes | PASS (60/60) |
| No reference has all-gap columns | PASS (0 total) |

1000L3 reference width: 6030–7965 columns. 1000M1 and 1000S1 are unchanged apart from the names (same `n_seqs` and `ref_length` per replicate as before).

## Step 6 — Stage the RNASim datasets

**2026-10-23 20:55 UTC** — step COMPLETE (took the archive branch: ready-made 1000-sequence samples exist, so M3 and `sample_rnasim.py` aren't needed)

Done:
- `scripts/stage_rnasim.py` chooses `RNASIM_N`=10 of the 20 archive samples `RNASim/1000/R0–R19` with `random.Random(RNASIM_SEED=20261023).sample(range(20), 10)`, sorted, and stages them as `RNASim_R01–R10`. Same transformation as ROSE: all-gap columns stripped from `true_align.txt` → `reference.fasta` (0 removed, since the archive has none), gaps stripped → `unaligned.fasta`; also `ids.txt` and `source.txt`. The mapping is in `data/datasets/rnasim_selection.tsv`.

Selection (staged name ← archive sample):
| R01 | R02 | R03 | R04 | R05 | R06 | R07 | R08 | R09 | R10 |
|---|---|---|---|---|---|---|---|---|---|
| R0 | R1 | R5 | R6 | R7 | R8 | R9 | R11 | R17 | R19 |

Verification:
| Check | Result |
|---|---|
| Exactly 10 RNASim dirs | PASS |
| 1000 seqs each, unique IDs | PASS (10/10) |
| `validate_alignment.py unaligned reference` passes | PASS (10/10) |
| No reference has all-gap columns | PASS (0) |
| *(sampled branch only)* rerun gives byte-identical outputs | not required (archive branch); checked anyway: rerun → 10 × "unchanged", `shasum` of all 41 files identical |
| *(sampled branch only)* samples share no IDs | not required (archive branch); see note |

Dataset shape: reference width 4702–4903 columns; mean unaligned length ≈ 1554 nt (about 1.5× the ROSE sequences, so expect longer MAGUS runs).

Note — overlap between archive samples: the 20 archive samples share 162 IDs (19,837 distinct of 20,000); our 10 share 41 IDs (each in at most 2 samples), and every shared ID has an identical sequence in both. So the archive's samples were drawn independently from the full RNASim alignment, not as disjoint sets. This is how the original data was built; replicates overlap by ~0.4% of sequences.

**Addendum (2026-10-25)** — RNASim directories now carry the archive sample's name (`RNASim_R<k>`): `RNASim_R0 R1 R5 R6 R7 R8 R9 R11 R17 R19` (same seed, same 10 samples). `data/datasets/rnasim_selection.tsv` still records the selection. Rerun: 10 × "unchanged"; 10 dirs, 1000 seqs each, unique IDs, `validate_alignment.py` passes (10/10), no all-gap columns.

## Step 7 — Build the manifest

**2026-10-23 21:05 UTC** — step COMPLETE

Done:
- `scripts/build_manifest.py` scans `data/datasets/*_R??` and writes `data/manifest.tsv` (columns `name, condition, replicate, unaligned, reference, n_seqs, ref_length`). Paths are relative to the project root; `ref_length` = reference alignment width; `replicate` is an integer. Rows are ordered 1000M1, 1000L1, 1000S1, RNASim, then by replicate. The condition label for RNASim is `RNASim`, matching the directory names (the spec's table calls it RNASim-1000). A rerun reports "unchanged".

Verification:
| Check | Result |
|---|---|
| Exactly 70 data rows: 20 × 1000M1, 20 × 1000L1, 20 × 1000S1, 10 × RNASim | PASS |
| All paths exist | PASS (140/140) |
| `n_seqs` = 1000 for every row | PASS |
| Names unique | PASS |

**Addendum (2026-10-25)** — `build_manifest.py` now lists exactly the datasets the two staging scripts produce (ROSE `<cond>_R0`–`R19` for each condition, and the RNASim names from `RNASIM_SEED`). It exits non-zero if one is missing, and any other directory in `data/datasets/` (for example `1000L1_R01`… left over from the earlier staging) is reported on stderr and left out; those can be deleted (`data/datasets/*/` is derived from `data/raw/`). Rows are ordered 1000M1, 1000L3, 1000S1, RNASim, then by replicate.

| Check | Result |
|---|---|
| Exactly 70 data rows: 20 × 1000M1, 20 × 1000L3, 20 × 1000S1, 10 × RNASim | PASS |
| All paths exist | PASS (140/140) |
| `n_seqs` = 1000 for every row | PASS |
| Names unique | PASS |
| Rerun | "70 rows, unchanged" |
