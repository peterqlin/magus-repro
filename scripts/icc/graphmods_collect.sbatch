#!/usr/bin/env bash
# Collect the graphmods sweep rows into results/ (graphmods_rows.jsonl, graphmods_scores.csv) and write the
# paired tables (graphmods.md, graphmods.csv). Submitted by scripts/icc/submit_graphmods.sh to start after
# the sweep array.
#SBATCH --job-name=graphmods-collect
#SBATCH --nodes=1
#SBATCH --ntasks=1
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"

scripts/dk.sh env GRAPHMODS_TAG="${GRAPHMODS_TAG:-}" GRAPHMODS_ONLY="${GRAPHMODS_ONLY:-}" python3 scripts/graphmods_collect.py
status=$?
out="results/graphmods${GRAPHMODS_TAG:+_$GRAPHMODS_TAG}"
scripts/dk.sh python3 -m graphmods.tables "${out}_rows.jsonl" --md "$out.md" --csv "$out.csv" || status=1
exit "$status"
