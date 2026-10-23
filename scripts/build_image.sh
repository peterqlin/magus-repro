#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/config.env"
docker build --platform "$DOCKER_PLATFORM" -f "$ROOT/docker/Dockerfile" -t "$DOCKER_IMAGE" "$ROOT"
