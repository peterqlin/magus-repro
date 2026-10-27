#!/usr/bin/env bash
# Build the Apptainer image SIF_IMAGE from a `docker save` archive of DOCKER_IMAGE: build_sif.sh <image.tar>
# Make the archive where the Docker image was built (scripts/build_image.sh):
#   docker save magus-repro:pinned -o magus-repro.tar
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/config.sh"
CONTAINER_RUNTIME=apptainer

archive="${1:?usage: build_sif.sh <image.tar>}"
apptainer build --force "$ROOT/$SIF_IMAGE" "docker-archive:$archive"

actual="$(image_commit)"
if [ "$actual" != "$MAGUS_COMMIT" ]; then
    echo "$SIF_IMAGE has magus.commit=$actual, expected MAGUS_COMMIT=$MAGUS_COMMIT" >&2
    exit 1
fi
echo "built $SIF_IMAGE (magus.commit=$actual)"
