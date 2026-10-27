#!/usr/bin/env bash
# Submit the manifest's MAGUS runs as a Slurm job array on the Illinois Campus Cluster, plus a scoring job
# that starts once every array task has ended: submit.sh [array spec]   (default: every manifest row)
#
# Array task i runs manifest row i. Finished runs (runs/<name>/DONE) are skipped, so resubmitting reruns
# only what is missing. Account, partition and resources come from config.icc.env; logs go to runs/slurm/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export MAGUS_SITE=icc
source scripts/config.sh

if [ ! -f "$SIF_IMAGE" ]; then
    echo "$SIF_IMAGE not found; build it with scripts/build_sif.sh" >&2
    exit 1
fi

rows=$(( $(wc -l < data/manifest.tsv) - 1 ))
mkdir -p runs/slurm
common=(--parsable --account "$SLURM_ACCOUNT" --partition "$SLURM_PARTITION")

array_job="$(sbatch "${common[@]}" \
    --time "$SLURM_TIME" --cpus-per-task "$SLURM_CPUS_PER_JOB" --mem "$SLURM_MEM" \
    --array "${1:-1-$rows}" --output 'runs/slurm/magus_%A_%a.out' \
    scripts/icc/magus_array.sbatch | cut -d';' -f1)"

score_job="$(sbatch "${common[@]}" \
    --time 01:00:00 --cpus-per-task 4 --mem 8G \
    --dependency "afterany:$array_job" --output 'runs/slurm/score_%j.out' \
    scripts/icc/score.sbatch | cut -d';' -f1)"

echo "array job $array_job (${1:-1-$rows}), scoring job $score_job"
