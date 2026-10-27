#!/usr/bin/env bash
# Submit the graphmods sweep as a Slurm job array on the Illinois Campus Cluster (one task per manifest
# row, merge-only replays of every strategy setting on that dataset's MAGUS run), plus a collect job that
# starts once every task has ended: submit_graphmods.sh [array spec]   (default: every manifest row)
#
# The sweep skips (dataset, setting) pairs already in its rows file, so resubmitting continues where a task
# stopped. Account and partition come from config.icc.env; logs go to runs/slurm/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export MAGUS_SITE=icc
source scripts/config.sh

python3 scripts/graphmods_reps.py
rows=$(( $(wc -l < data/manifest.tsv) - 1 ))
mkdir -p runs/slurm runs/_graphmods/rows
common=(--parsable --account "$SLURM_ACCOUNT" --partition "$SLURM_PARTITION")

array_job="$(sbatch "${common[@]}" \
    --time "$SLURM_TIME" --cpus-per-task "$GRAPHMODS_CPUS_PER_JOB" --mem "$GRAPHMODS_MEM" \
    --array "${1:-1-$rows}" --output 'runs/slurm/graphmods_%A_%a.out' \
    scripts/icc/graphmods_array.sbatch | cut -d';' -f1)"

collect_job="$(sbatch "${common[@]}" \
    --time 00:30:00 --cpus-per-task 2 --mem 8G \
    --dependency "afterany:$array_job" --output 'runs/slurm/graphmods_collect_%j.out' \
    scripts/icc/graphmods_collect.sbatch | cut -d';' -f1)"

echo "sweep array job $array_job (${1:-1-$rows}), collect job $collect_job"
