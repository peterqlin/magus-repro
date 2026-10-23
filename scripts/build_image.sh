#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/config.env"

git -C "$ROOT" submodule update --init vendor/MAGUS

actual="$(git -C "$ROOT/vendor/MAGUS" rev-parse HEAD)"
if [ "$actual" != "$MAGUS_COMMIT" ]; then
    echo "vendor/MAGUS is at $actual, expected MAGUS_COMMIT=$MAGUS_COMMIT" >&2
    exit 1
fi
if [ -n "$(git -C "$ROOT/vendor/MAGUS" status --porcelain)" ]; then
    echo "vendor/MAGUS has uncommitted changes" >&2
    exit 1
fi

docker build --platform "$DOCKER_PLATFORM" -f "$ROOT/docker/Dockerfile" \
    --label "magus.commit=$MAGUS_COMMIT" \
    -t "$DOCKER_IMAGE" "$ROOT"
