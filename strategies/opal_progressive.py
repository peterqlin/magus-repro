# AI-assisted (Claude), exploration code for CS581 project
"""Whole merge, OPAL: profile-profile merges of the subset alignments with OPAL (PASTA's merger for DNA/RNA) along a
UPGMA guide tree over the subsets (6-mer distance). Unlike PASTA, every merge is progressive along that tree (no
transitivity merge of overlapping pairs). Backbones unused. OPAL jar: $OPAL_JAR (the image sets it); heap: $OPAL_XMX."""
import os

from graphmods import merge as M

FAMILY = "whole"
GRID = [{}]


def merge(job):
    jar = os.environ.get("OPAL_JAR", "/opt/opal/opal.jar")
    xmx = os.environ.get("OPAL_XMX", "8g")

    def merge_two(a, b, out):
        M.run(["java", "-Xmx" + xmx, "-jar", jar, "--in", a, "--in2", b, "--out", out, "--align_method", "profile",
               "--quiet"], log=job.path("tool.log"))
    M.finish(job, M.progressive(job, merge_two))
