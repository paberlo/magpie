#!/usr/bin/env bash
#needed due to WSL environment
export LD_LIBRARY_PATH="/mnt/e/Dropbox/INVESTIGACION/GeneticImprovement/srcml/lib:$LD_LIBRARY_PATH"
set -e  # fail at first error

FOLD=org.sat4j.core/src/main/java/org/sat4j/minisat/core/
FILE=Solver.java

srcml $FOLD/$FILE> _magpie/$FILE.xml
cp _magpie/$FILE.xml $FILE.xml










