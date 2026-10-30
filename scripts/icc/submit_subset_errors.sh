#!/usr/bin/env bash
# Submit the subset-error breakdown (scripts/subset_errors.py) as a Slurm job array on the Illinois Campus Cluster,
# one task per manifest row, plus a job that writes results/ceiling_subset_errors.csv once every task has ended:
# submit_subset_errors.sh [array spec]   (default: every manifest row)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export MAGUS_SITE=icc
source scripts/config.sh

rows=$(( $(wc -l < data/manifest.tsv) - 1 ))
mkdir -p runs/slurm
source scripts/icc/slurm_common.sh

array_job="$(sbatch "${common[@]}" \
    --time 01:00:00 --cpus-per-task 2 --mem 8G \
    --array "${1:-1-$rows}" --output 'runs/slurm/subset_errors_%A_%a.out' \
    scripts/icc/subset_errors_array.sbatch | cut -d';' -f1)"

summary_job="$(sbatch "${common[@]}" \
    --time 00:15:00 --cpus-per-task 1 --mem 4G \
    --dependency "afterany:$array_job" --output 'runs/slurm/subset_errors_summary_%j.out' \
    --wrap 'scripts/dk.sh python3 scripts/subset_errors.py --summary' | cut -d';' -f1)"

echo "subset errors array job $array_job (${1:-1-$rows}), summary job $summary_job"
