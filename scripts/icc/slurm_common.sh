# Sourced by the ICC submit scripts after scripts/config.sh. Defines `common`, the sbatch options every job
# gets. Jobs never run on the tallis partition or its nodes: tallis is reserved for months-long research
# projects, not this one.

if tr ',' '\n' <<< "$SLURM_PARTITION" | grep -qix tallis; then
    echo "SLURM_PARTITION=$SLURM_PARTITION: this project must not use the tallis partition" >&2
    exit 1
fi

common=(--parsable --account "$SLURM_ACCOUNT" --partition "$SLURM_PARTITION")
tallis_nodes="$(sinfo -h -p tallis -o %N 2>/dev/null)"
if [ -n "$tallis_nodes" ]; then
    common+=(--exclude "$tallis_nodes")
fi
