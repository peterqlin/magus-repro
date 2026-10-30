#!/usr/bin/env bash
# Append one array task's outcome to a joblog under a lock:
#   joblog.sh <joblog.tsv> <name> <start> <runtime_s> <exitval>
set -euo pipefail
joblog="$1"
(
    flock 9
    [ -s "$joblog" ] || printf 'seq\tname\thost\tstart\truntime_s\texitval\tslurm_job\n' > "$joblog"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$SLURM_ARRAY_TASK_ID" "$2" "$(hostname -s)" "$3" "$4" "$5" \
        "${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" >> "$joblog"
) 9> "$joblog.lock"
