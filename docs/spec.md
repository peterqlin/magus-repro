# Spec: Reproduce MAGUS results on ROSE and RNASim datasets

## Goal

Run MAGUS (Smirnov & Warnow, *Bioinformatics* 2021, doi:10.1093/bioinformatics/btaa992) locally on **70 datasets** and score the alignments against the reference alignments:

| Condition | Source | Replicates | Sequences each |
|---|---|---|---|
| 1000M1 | ROSE (from the MAGUS data archive) | 20 | 1000 |
| 1000L3 | ROSE | 20 | 1000 |
| 1000S1 | ROSE | 20 | 1000 |
| RNASim-1000 | RNASim, 1000-sequence samples | 10 | 1000 |

Outputs: one MAGUS alignment per dataset, SPFN/SPFP (FastSP), wall time and peak memory per run, a per-condition summary, and a comparison against the published/archived MAGUS results where those exist.

## Rules for Claude Code

1. Do the steps **in order**. A step is done only when every item under **Verify** passes.
2. If a Verify check fails, fix it within that step. If it can't be fixed without a decision from me (the user), **stop and ask**. Do not skip ahead or weaken a check to make it pass.
3. If a step depends on a manual prerequisite (section M) that isn't satisfied, stop and tell me exactly which one and what you found.
4. Keep a running log in `PROGRESS.md`: step number, date/time, what was done, the verification output (abbreviated), and any deviations from this spec.
5. Never delete anything under `data/raw/`. Treat it as read-only.
6. Every script must be rerunnable (idempotent): rerunning a finished step must not corrupt results or redo completed MAGUS runs.
7. All tool execution (MAGUS, MAFFT, MCL, FastSP) happens **inside the Docker image** built in Step 2, so results don't depend on the host.

## Directory layout

```
magus-repro/
  spec.md
  PROGRESS.md
  config.env              # all tunable settings (Step 0)
  docker/Dockerfile
  vendor/MAGUS/           # pinned checkout
  vendor/FastSP/          # FastSP source/jar
  data/raw/               # manual downloads, read-only
  data/datasets/<name>/   # unaligned.fasta, reference.fasta (one dir per dataset)
  data/manifest.tsv       # 70 rows
  scripts/                # all scripts
  runs/<name>/            # work/, magus.aln, time.txt, magus.log, DONE
  results/                # scores.csv, summary.csv, comparison.csv
  REPORT.md
```

---

## M. Manual prerequisites (done by me, not Claude Code)

- **M1. Docker installed and running.** `docker info` works without sudo. In Docker Desktop, give the VM enough CPUs (≥ 8 recommended) and RAM (≥ 16 GB).
- **M2. MAGUS data archive downloaded.** From the Illinois Data Bank record **IDB-2643961** ("Data and results for: MAGUS: Multiple Sequence Alignment using Graph Clustering"), download `Datasets.zip` and any results archive. Put them in `data/raw/` unextracted.
- **M3. RNASim source (only if needed).** If Step 5 finds no ready-made 1000-sequence RNASim samples in the archive, I provide the full RNASim reference alignment in `data/raw/rnasim/`.
- **M4. Pinned MAGUS commit approved.** Claude Code proposes a commit in Step 1; I confirm it.
- **M5. Disk space.** At least ~20 GB free; MAGUS working dirs hold backbones and graphs.
- **M6. Long-running batch.** I start Step 9's full batch in a terminal that survives (tmux/screen) and keep the machine awake, or explicitly ask Claude Code to run it in the background.

---

## Step 0 — Scaffold and config

**Do**
- Create the directory layout above, `PROGRESS.md`, and `config.env` with:
  - `MAGUS_COMMIT=` (filled in Step 1)
  - `TOTAL_CORES=` (detected host cores, minus 1)
  - `THREADS_PER_JOB=4`
  - `PARALLEL_JOBS=` (floor of TOTAL_CORES / THREADS_PER_JOB, minimum 1)
  - `RNASIM_SEED=20261023`
  - `RNASIM_N=10`
  - `RNASIM_SIZE=1000`
  - `JOB_TIMEOUT_MIN=240`
  - `DOCKER_IMAGE=magus-repro:pinned`
  - `DOCKER_PLATFORM=linux/amd64`
- Check the manual prerequisites that can be checked now: M1 (`docker info`), M2 (files exist in `data/raw/`), M5 (`df -h .`).

**Verify**
- `config.env` exists, and `source config.env` defines every variable above (all but MAGUS_COMMIT non-empty).
- `docker info` exits 0.
- `data/raw/` contains the archive(s) from M2.
- Free disk ≥ 20 GB.

## Step 1 — Pin MAGUS

**Do**
- `git clone https://github.com/vlasmirnov/MAGUS vendor/MAGUS`.
- Inspect `git log` and propose a commit contemporaneous with the original paper (late 2020, before the Recursive MAGUS changes). Report the candidate SHA, its date, and its message, plus HEAD for comparison. **Stop and ask me to approve (M4).**
- After approval: `git checkout <sha>`, and write the SHA into `config.env`.
- From the pinned checkout, record in `PROGRESS.md`:
  - the entry point (`magus.py` at the repo root vs. the `magus` package),
  - the default values of: guide tree (`-t`), `--maxnumsubsets`, `--maxsubsetsize`, backbone count (`-r`), backbone size (`-m`), graph trace method, and the flag for thread count (e.g. `-np`), as read from the argument parser source, and
  - any differences from current HEAD defaults.

**Verify**
- `git -C vendor/MAGUS rev-parse HEAD` equals `MAGUS_COMMIT`.
- Working tree is clean (`git status --porcelain` empty).
- `PROGRESS.md` contains the defaults table and entry point.

## Step 2 — Build the Docker image

**Do**
- Write `docker/Dockerfile` (do not modify the upstream one): Python 3 base image, platform `linux/amd64` (the bundled MAFFT/MCL binaries are x86-64 Linux), install GNU `time`, a Java runtime (for FastSP), and `procps`. Copy `vendor/MAGUS` into the image, make the bundled binaries executable, and install any Python requirements the pinned checkout needs.
- Write `scripts/dk.sh`: a wrapper that runs a command in the image with the project mounted at `/work`, the `--platform` from config, and the host user's UID/GID so output files are not root-owned.
- Build with tag `DOCKER_IMAGE`.

**Verify**
- `scripts/dk.sh <magus entry point> -h` exits 0 and prints help that includes the flags recorded in Step 1.
- The bundled MAFFT and MCL run inside the container (`--version` or equivalent exits 0).
- `scripts/dk.sh /usr/bin/time -v true` prints "Maximum resident set size".
- `scripts/dk.sh java -version` exits 0.

## Step 3 — Smoke test MAGUS

**Do**
- Run MAGUS in the container on the repo's `example/` unaligned sequences, with a fresh work dir under `runs/_smoke/`.
- Write `scripts/validate_alignment.py <unaligned.fasta> <alignment.fasta>`. It must check:
  - the same set of sequence IDs, no duplicates;
  - all aligned rows have equal length;
  - removing gaps (`-`) from each aligned row reproduces the input sequence exactly (case-insensitive);
  - no all-gap columns (warn only).
  
  It should exit non-zero on any hard failure.

**Verify**
- MAGUS exits 0 and the output alignment is non-empty.
- `validate_alignment.py` passes on the smoke output.
- `validate_alignment.py` **fails** on a deliberately corrupted copy (one residue changed, and separately, one sequence removed). This proves the validator works.

## Step 4 — Set up FastSP

**Do**
- Get FastSP (https://github.com/smirarab/FastSP) into `vendor/FastSP/`. Use the prebuilt `FastSP.jar` if present; otherwise build it inside the container.
- Write `scripts/score.py <reference.fasta> <estimated.fasta>`. It runs FastSP in the container, parses SP-Score, Modeler, SPFN, SPFP and TC from its output (stdout and stderr), and prints one JSON line.

**Verify**
- Scoring the smoke-test alignment against itself gives SPFN = 0 and SPFP = 0.
- Scoring it against a version with one column's gaps shifted gives SPFN > 0 or SPFP > 0.

## Step 5 — Inventory and stage the ROSE datasets

**Do**
- Extract the M2 archive(s) into `data/raw/extracted/` (without touching the original zip).
- Write `scripts/inventory.py` that lists every dataset directory found and, for each, the file that looks like the unaligned input and the reference/true alignment. Report the structure in `PROGRESS.md`. If the naming is ambiguous, **stop and ask** rather than guess.
- Stage each ROSE replicate as `data/datasets/<cond>_R<k>/unaligned.fasta` and `reference.fasta`, with `cond` ∈ {1000M1, 1000L3, 1000S1} and `R<k>` the archive's own replicate name (`R0`–`R19`), so a dataset has the same name here as in the archive. If the archive has only a reference alignment, make `unaligned.fasta` by stripping gaps from it.
- Strip all-gap columns from each staged reference.
- Determine whether the archive also includes **1000-sequence RNASim samples** and/or **published MAGUS alignments or scores** for these conditions; record the answer.

**Verify**
- Exactly 20 staged directories per ROSE condition (60 total).
- Every staged dataset: unaligned has exactly 1000 sequences, unique IDs; `validate_alignment.py unaligned.fasta reference.fasta` passes (reference is consistent with input).
- No reference has all-gap columns.

## Step 6 — Stage the RNASim datasets

**Do**
- **If** the archive contains 1000-sequence RNASim samples: stage 10 of them (if there are more than 10, choose with `RNASIM_SEED` and record which).
- **Else**: require M3 (stop if missing). Write `scripts/sample_rnasim.py`, which samples `RNASIM_N` disjoint sets of `RNASIM_SIZE` sequences from the full reference with `RNASIM_SEED`, writes the induced sub-alignment with all-gap columns removed as `reference.fasta`, and the gap-stripped sequences as `unaligned.fasta`. Record the sampled IDs in `data/datasets/RNASim_R<k>/ids.txt`.
- Name each directory after its archive sample, `RNASim_R<k>` (sampled branch: `RNASim_R0`–`RNASim_R9`).

**Verify**
- Exactly 10 RNASim directories, each passing the same checks as Step 5.
- If sampled: rerunning `sample_rnasim.py` with the same seed produces byte-identical outputs (checksum match), and the 10 samples share no sequence IDs.

## Step 7 — Build the manifest

**Do**
- Write `data/manifest.tsv` with columns: `name, condition, replicate, unaligned, reference, n_seqs, ref_length`.

**Verify**
- Exactly 70 data rows: 20 × 1000M1, 20 × 1000L3, 20 × 1000S1, 10 × RNASim.
- All paths exist; `n_seqs` = 1000 for every row.
- Names are unique.

## Step 8 — Runner and pilot runs

**Do**
- Write `scripts/run_one.sh <name>`:
  - Skip immediately if `runs/<name>/DONE` exists.
  - Otherwise delete and recreate `runs/<name>/work` (MAGUS won't overwrite existing backbone/graph/cluster files, and an interrupted run can leave empty backbone files that break reruns).
  - Run MAGUS in the container with the pinned defaults and `THREADS_PER_JOB` threads, wrapped in `/usr/bin/time -v` and `timeout JOB_TIMEOUT_MIN`. Write `magus.aln`, `time.txt` and `magus.log`.
  - Run `validate_alignment.py`. Only on success, write `DONE` containing the commit SHA, the exact command and a timestamp.
  - On failure, leave no `DONE` and exit non-zero.
- Pilot: run one dataset from each condition (`1000M1_R0`, `1000L3_R0`, `1000S1_R0`, `RNASim_R0`), then score them.

**Verify**
- All 4 pilots have `DONE`, pass validation and have parseable wall time and max RSS.
- Pilot SPFN/SPFP are in [0, 1]. If the archive has published scores for those exact replicates, the pilot values are within 0.02 of them; if not, report them for my review and **stop** until I confirm they look reasonable.
- Running `run_one.sh` again on a pilot returns immediately (skip works).
- Report the pilot runtimes and a projected total batch time given `PARALLEL_JOBS`.

## Step 9 — Full batch

**Do**
- Write `scripts/run_all.sh`: runs `run_one.sh` over every manifest row with `PARALLEL_JOBS` concurrent jobs (GNU parallel, installed on the host or run via the container), with a joblog at `runs/joblog.tsv` and resume support.
- Tell me the command and the projected time; I start it per M6 unless I ask you to run it.

**Verify**
- 70 `DONE` markers.
- `runs/joblog.tsv` shows exit code 0 for every job (after any reruns).
- Every alignment passes `validate_alignment.py` (re-check all 70, not just the per-job check).

## Step 10 — Score

**Do**
- Write `scripts/score_all.py`. It scores every run with FastSP and parses `time.txt`, producing `results/scores.csv` with columns `name, condition, replicate, SPFN, SPFP, SP_score, TC, wall_s, max_rss_mb`.

**Verify**
- 70 rows, no missing values.
- Every SPFN/SPFP is in [0, 1].
- Spot-check: recompute 3 random rows by hand with `score.py` and get identical values.

## Step 11 — Summarize and compare

**Do**
- `results/summary.csv`: per condition, the mean, SD and standard error of SPFN, SPFP, wall time and max RSS, plus n.
- If published/archived MAGUS results exist (Step 5): `results/comparison.csv`, with per-dataset and per-condition differences (ours − published) for SPFN and SPFP. If only figures from the paper are available, put those numbers in a clearly labeled `published_manual.csv` that I fill in, and compare against that.
- A plot of SPFN and SPFP by condition (ours vs. published where available) saved to `results/`.

**Verify**
- `summary.csv` has 4 condition rows with n = 20, 20, 20, 10.
- Means in `summary.csv` match a recomputation from `scores.csv`.
- Every comparison row has both values present, or an explicit "not available".

## Step 12 — Report

**Do**
- Write `REPORT.md` covering:
  - environment (image, MAGUS SHA, MAFFT/MCL/FastSP versions, host CPU, parallelism);
  - dataset provenance, including the RNASim sampling seed or archive source;
  - exact MAGUS command;
  - the summary table;
  - the comparison with published results;
  - any deviations from this spec, failures and reruns (from `PROGRESS.md`);
  - an interpretation of any difference larger than 0.02 in mean SPFN or SPFP.

**Verify**
- Every number in `REPORT.md` traces to a file in `results/`.
- `PROGRESS.md` shows every step 0–12 with its verification recorded.
