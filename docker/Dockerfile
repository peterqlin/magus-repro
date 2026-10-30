# Build context: the project root (see .dockerignore); built by scripts/build_image.sh.
FROM python:3.9-slim-bookworm

# libgomp1: the bundled FastTreeMP (the default guide tree) needs OpenMP.
RUN apt-get update \
    && apt-get install -y --no-install-recommends time procps openjdk-17-jre-headless libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# numpy, scipy: graphmods (strategies/) only; MAGUS itself needs only dendropy.
RUN pip install --no-cache-dir dendropy==4.5.2 numpy==1.26.4 scipy==1.13.1

# MAGUS is a package (tools in magus/tools/), run from /opt/MAGUS on PYTHONPATH; /usr/local/bin/magus is
# upstream's console script (magus = "magus.main:main").
COPY vendor/MAGUS /opt/MAGUS
RUN rm -rf /opt/MAGUS/.git \
    && chmod -R a+rX /opt/MAGUS \
    && find /opt/MAGUS/magus/tools -type f -exec chmod a+x {} + \
    && printf '#!/bin/sh\nexec python3 -m magus.main "$@"\n' > /usr/local/bin/magus \
    && chmod a+x /usr/local/bin/magus
ENV PYTHONPATH=/opt/MAGUS

# OPAL (strategies/opal_progressive.py only), from smirarab/sate-tools-linux at a fixed commit.
ADD --checksum=sha256:542390231d98879f415fe1f93052744075030103e634e757aed9c7f3e13d58d3 \
    https://raw.githubusercontent.com/smirarab/sate-tools-linux/90fb074d61af554e94d1a67583dd3a80b11417ea/opal.jar \
    /opt/opal/opal.jar
RUN chmod a+r /opt/opal/opal.jar
ENV OPAL_JAR=/opt/opal/opal.jar

ENV HOME=/tmp
WORKDIR /work
