#!/usr/bin/env bash
# One Slurm array task: the graphmods sweep (every strategy, every setting) on manifest row
# SLURM_ARRAY_TASK_ID, merge-only on that dataset's finished MAGUS run. Rows go to
# runs/_graphmods/rows/<name>.jsonl, and the outcome is appended to runs/graphmods_joblog.tsv.
# Submitted by scripts/icc/submit_graphmods.sh from the project root.
#SBATCH --job-name=graphmods
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
echo "$name: started $start"
scripts/dk.sh python3 -m graphmods.sweep --reps runs/graphmods_reps.tsv --names "$name" \
    --out "runs/_graphmods/rows/$name.jsonl" --threads "$SLURM_CPUS_PER_TASK"
status=$?
echo "$name: exit $status after $SECONDS s"

scripts/icc/joblog.sh runs/graphmods_joblog.tsv "$name" "$start" "$SECONDS" "$status"
exit "$status"
