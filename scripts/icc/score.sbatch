#!/usr/bin/env bash
# Re-validate every finished alignment and write results/scores.csv. Submitted by scripts/icc/submit.sh
# to start after the MAGUS array.
#SBATCH --job-name=magus-score
#SBATCH --nodes=1
#SBATCH --ntasks=1
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"

invalid=0
while IFS=$'\t' read -r name _ _ unaligned _; do
    [ -f "runs/$name/DONE" ] || continue
    python3 scripts/validate_alignment.py "$unaligned" "runs/$name/magus.aln" > /dev/null \
        || { echo "$name: alignment failed validation" >&2; invalid=1; }
done < <(tail -n +2 data/manifest.tsv)

python3 scripts/score_all.py
status=$?
[ "$invalid" -eq 0 ] && exit "$status" || exit 1
