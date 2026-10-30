#!/usr/bin/env bash
# The learned_weights pipeline on the Illinois Campus Cluster in one go (docs/graphmods.md, "Learned weights"):
#   1. dump_edge_features on every manifest row (array, rows in runs/_graphmods/rows_dump/),
#   2. scripts/graphmods_train.py once every dump task has ended (-> results/graphmods_edge_model.json),
#   3. the learned_weights sweep once the fit succeeded (array, rows in runs/_graphmods/rows_learned/),
#      then its collect job (-> results/graphmods_learned.md, _rows.jsonl, _scores.csv, .csv).
# Usage: submit_learned.sh [array spec]   (default: every manifest row). Resubmitting skips finished settings.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export MAGUS_SITE=icc
source scripts/config.sh

python3 scripts/graphmods_reps.py
rows=$(( $(wc -l < data/manifest.tsv) - 1 ))
mkdir -p runs/slurm runs/_graphmods/rows_dump runs/_graphmods/rows_learned
source scripts/icc/slurm_common.sh
array=(--time "${GRAPHMODS_TIME:-$SLURM_TIME}" --cpus-per-task "$GRAPHMODS_CPUS_PER_JOB" --mem "$GRAPHMODS_MEM"
       --array "${1:-1-$rows}")

dump_job="$(GRAPHMODS_ONLY=dump_edge_features GRAPHMODS_TAG=dump sbatch "${common[@]}" "${array[@]}" \
    --output 'runs/slurm/graphmods_dump_%A_%a.out' scripts/icc/graphmods_array.sbatch | cut -d';' -f1)"

train_job="$(sbatch "${common[@]}" --time 01:00:00 --cpus-per-task 4 --mem 16G \
    --dependency "afterany:$dump_job" --output 'runs/slurm/graphmods_train_%j.out' --job-name graphmods-train \
    --wrap "scripts/dk.sh python3 scripts/graphmods_train.py" | cut -d';' -f1)"

learned_job="$(GRAPHMODS_ONLY=learned_weights GRAPHMODS_TAG=learned sbatch "${common[@]}" "${array[@]}" \
    --dependency "afterok:$train_job" --output 'runs/slurm/graphmods_learned_%A_%a.out' \
    scripts/icc/graphmods_array.sbatch | cut -d';' -f1)"

collect_job="$(GRAPHMODS_ONLY=learned_weights GRAPHMODS_TAG=learned sbatch "${common[@]}" \
    --time 00:30:00 --cpus-per-task 2 --mem 8G \
    --dependency "afterany:$learned_job" --output 'runs/slurm/graphmods_collect_%j.out' \
    scripts/icc/graphmods_collect.sbatch | cut -d';' -f1)"

echo "dump array $dump_job, train $train_job, learned array $learned_job, collect $collect_job (${1:-1-$rows})"
