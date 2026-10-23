# Build context: the project root (see .dockerignore); built by scripts/build_image.sh.
FROM python:3.9-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends time procps openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir dendropy==4.5.2

COPY vendor/MAGUS /opt/MAGUS
RUN rm -rf /opt/MAGUS/.git \
    && chmod -R a+rX /opt/MAGUS \
    && find /opt/MAGUS/tools -type f -exec chmod a+x {} +

ENV HOME=/tmp
WORKDIR /work
