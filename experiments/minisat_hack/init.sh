#!/usr/bin/env bash

#needed due to WSL environment
export LD_LIBRARY_PATH="/mnt/e/Dropbox/INVESTIGACION/GeneticImprovement/srcml/lib:$LD_LIBRARY_PATH"
set -e  # fail at first error

patch sources/core/Dimacs.h _magpie/dimacs.diff
srcml sources/core/Solver.cc > _magpie/Solver.cc.xml
cp _magpie/Solver.cc.xml sources/core
