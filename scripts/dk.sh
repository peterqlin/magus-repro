#!/usr/bin/env bash
# Run a command inside the project image with the project mounted at /work.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/config.env"
exec docker run --rm -i \
    --platform "$DOCKER_PLATFORM" \
    --user "$(id -u):$(id -g)" \
    -v "$ROOT":/work -w /work \
    "$DOCKER_IMAGE" "$@"
