#!/usr/bin/env bash
# Run a command inside the project image with the project mounted at /work.
# Set DK_NAME to give the container a name (docker refuses a second container with the same name).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/config.env"
exec docker run --rm -i \
    ${DK_NAME:+--name "$DK_NAME"} \
    --platform "$DOCKER_PLATFORM" \
    --user "$(id -u):$(id -g)" \
    -v "$ROOT":/work -w /work \
    "$DOCKER_IMAGE" "$@"
