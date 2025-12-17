#!/usr/bin/env bash
#needed due to WSL environment
export LD_LIBRARY_PATH="/mnt/e/Dropbox/INVESTIGACION/GeneticImprovement/srcml/lib:$LD_LIBRARY_PATH"
set -e  # fail at first error

patch triangle.c _magpie/triangle_slow.c.diff
patch triangle.h _magpie/triangle_slow.h.diff
#/mnt/e/Dropbox/INVESTIGACION/GeneticImprovement/srcml/bin/
srcml triangle.c -o _magpie/triangle_slow.c.xml
cp _magpie/triangle_slow.c.xml triangle.c.xml


