# Build context: the project root (see .dockerignore); built by scripts/build_image.sh.
FROM python:3.9-slim-bookworm

# libgomp1: the bundled FastTreeMP (the default guide tree) needs OpenMP.
RUN apt-get update \
    && apt-get install -y --no-install-recommends time procps openjdk-17-jre-headless libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir dendropy==4.5.2

# MAGUS is a package (tools in magus/tools/), run from /opt/MAGUS on PYTHONPATH; /usr/local/bin/magus is
# upstream's console script (magus = "magus.main:main").
COPY vendor/MAGUS /opt/MAGUS
RUN rm -rf /opt/MAGUS/.git \
    && chmod -R a+rX /opt/MAGUS \
    && find /opt/MAGUS/magus/tools -type f -exec chmod a+x {} + \
    && printf '#!/bin/sh\nexec python3 -m magus.main "$@"\n' > /usr/local/bin/magus \
    && chmod a+x /usr/local/bin/magus
ENV PYTHONPATH=/opt/MAGUS

ENV HOME=/tmp
WORKDIR /work
