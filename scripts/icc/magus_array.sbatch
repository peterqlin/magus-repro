#!/usr/bin/env bash
# One Slurm array task: run_one.sh on manifest row SLURM_ARRAY_TASK_ID, then append the outcome to
# runs/joblog.tsv. Submitted by scripts/icc/submit.sh from the project root.
#SBATCH --job-name=magus
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
scripts/run_one.sh "$name"
status=$?

joblog=runs/joblog.tsv
(
    flock 9
    [ -s "$joblog" ] || printf 'seq\tname\thost\tstart\truntime_s\texitval\tslurm_job\n' > "$joblog"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$SLURM_ARRAY_TASK_ID" "$name" "$(hostname -s)" "$start" \
        "$SECONDS" "$status" "${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" >> "$joblog"
) 9> runs/.joblog.lock
exit "$status"
