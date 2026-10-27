#!/usr/bin/env bash
# Run a command inside the project image with the project mounted at /work, with Docker or Apptainer
# (CONTAINER_RUNTIME). Set DK_NAME to give a Docker container a name (docker refuses a second container
# with the same name).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/config.sh"

if [ "$CONTAINER_RUNTIME" = apptainer ]; then
    exec apptainer exec --cleanenv --home /tmp \
        --bind "$ROOT":/work --pwd /work \
        "$ROOT/$SIF_IMAGE" "$@"
fi

exec docker run --rm -i \
    ${DK_NAME:+--name "$DK_NAME"} \
    --platform "$DOCKER_PLATFORM" \
    --user "$(id -u):$(id -g)" \
    -v "$ROOT":/work -w /work \
    "$DOCKER_IMAGE" "$@"
