#!/usr/bin/env bash
# Collect the graphmods sweep rows into results/ (graphmods_rows.jsonl, graphmods_scores.csv) and write the
# paired tables (graphmods.md, graphmods.csv). Submitted by scripts/icc/submit_graphmods.sh to start after
# the sweep array.
#SBATCH --job-name=graphmods-collect
#SBATCH --nodes=1
#SBATCH --ntasks=1
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"

scripts/dk.sh python3 scripts/graphmods_collect.py
status=$?
scripts/dk.sh python3 -m graphmods.tables results/graphmods_rows.jsonl \
    --md results/graphmods.md --csv results/graphmods.csv || status=1
exit "$status"
