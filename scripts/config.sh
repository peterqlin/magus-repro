# Sourced by the shell scripts after they set ROOT. Loads config.env, then config.$MAGUS_SITE.env when
# MAGUS_SITE is set (MAGUS_SITE=icc on the Illinois Campus Cluster), and defines image helpers for the
# configured CONTAINER_RUNTIME (docker or apptainer).

source "$ROOT/config.env"
if [ -n "${MAGUS_SITE:-}" ]; then
    source "$ROOT/config.$MAGUS_SITE.env"
fi

# The magus.commit label of the configured image.
image_commit() {
    if [ "$CONTAINER_RUNTIME" = apptainer ]; then
        apptainer inspect --labels "$ROOT/$SIF_IMAGE" | awk '$1 == "magus.commit:" { print $2 }'
    else
        docker image inspect "$DOCKER_IMAGE" --format '{{index .Config.Labels "magus.commit"}}'
    fi
}

# "<image> <id>" for the configured image: the docker image ID, or the SIF's sha256.
image_desc() {
    if [ "$CONTAINER_RUNTIME" = apptainer ]; then
        echo "$SIF_IMAGE sha256:$(sha256sum "$ROOT/$SIF_IMAGE" | cut -d' ' -f1)"
    else
        echo "$DOCKER_IMAGE $(docker image inspect "$DOCKER_IMAGE" --format '{{.Id}}')"
    fi
}
