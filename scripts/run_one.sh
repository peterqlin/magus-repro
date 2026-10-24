#!/usr/bin/env bash
# Run MAGUS on one manifest dataset: run_one.sh <name>
#
# Writes runs/<name>/{work/, magus.aln, time.txt, magus.log} and, only after the
# alignment validates, runs/<name>/DONE. Exits 0 immediately if DONE exists.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source config.env

name="${1:?usage: run_one.sh <name>}"
run="runs/$name"

if [ -f "$run/DONE" ]; then
    echo "$name: DONE exists, skipping"
    exit 0
fi

unaligned="$(awk -F'\t' -v n="$name" 'NR > 1 && $1 == n { print $4 }' data/manifest.tsv)"
if [ -z "$unaligned" ]; then
    echo "$name: not in data/manifest.tsv" >&2
    exit 1
fi

image_commit="$(docker image inspect "$DOCKER_IMAGE" --format '{{index .Config.Labels "magus.commit"}}')"
if [ "$image_commit" != "$MAGUS_COMMIT" ]; then
    echo "$name: image $DOCKER_IMAGE has magus.commit=$image_commit, expected $MAGUS_COMMIT" >&2
    exit 1
fi

rm -rf "$run/work" "$run/magus.aln" "$run/time.txt" "$run/magus.log"
mkdir -p "$run/work"

cmd=(/usr/bin/time -v -o "$run/time.txt"
     timeout "${JOB_TIMEOUT_MIN}m"
     python3 /opt/MAGUS/magus.py
     -d "$run/work" -i "$unaligned" -o "$run/magus.aln" -np "$THREADS_PER_JOB")

echo "$name: started $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
status=0
DK_NAME="magus-$name" scripts/dk.sh "${cmd[@]}" > "$run/magus.log" 2>&1 || status=$?

if [ "$status" -ne 0 ]; then
    [ "$status" -eq 124 ] && reason="timed out after ${JOB_TIMEOUT_MIN} min" || reason="exit $status"
    echo "$name: MAGUS failed ($reason); see $run/magus.log" >&2
    exit 1
fi

if ! python3 scripts/validate_alignment.py "$unaligned" "$run/magus.aln" >> "$run/magus.log" 2>&1; then
    echo "$name: alignment failed validation; see $run/magus.log" >&2
    exit 1
fi

{
    echo "magus_commit=$MAGUS_COMMIT"
    echo "image=$DOCKER_IMAGE $(docker image inspect "$DOCKER_IMAGE" --format '{{.Id}}')"
    echo "command=scripts/dk.sh ${cmd[*]}"
    echo "finished=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} > "$run/DONE"
echo "$name: finished $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
