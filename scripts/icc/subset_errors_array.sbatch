#!/usr/bin/env bash
# One Slurm array task: scripts/subset_errors.py on manifest row SLURM_ARRAY_TASK_ID (into results/ceiling_subsets/),
# with the outcome appended to runs/subset_errors_joblog.tsv. Submitted by scripts/icc/submit_subset_errors.sh.
#SBATCH --job-name=subset-errors
#SBATCH --nodes=1
#SBATCH --ntasks=1
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"

name="$(awk -F'\t' -v i="$SLURM_ARRAY_TASK_ID" 'NR == i + 1 { print $1 }' data/manifest.tsv)"
if [ -z "$name" ]; then
    echo "no manifest row $SLURM_ARRAY_TASK_ID" >&2
    exit 1
fi

start="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
SECONDS=0
scripts/dk.sh python3 scripts/subset_errors.py "$name"
status=$?

scripts/icc/joblog.sh runs/subset_errors_joblog.tsv "$name" "$start" "$SECONDS" "$status"
exit "$status"
