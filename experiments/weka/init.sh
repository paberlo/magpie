#!/usr/bin/env bash
#needed due to WSL environment
export LD_LIBRARY_PATH="/mnt/e/Dropbox/INVESTIGACION/GeneticImprovement/srcml/lib:$LD_LIBRARY_PATH"
set -e  # fail at first error

FOLD=weka-src/src/main/java/weka/classifiers/trees/
FILE=RandomForest.java

srcml $FOLD/$FILE> _magpie/$FILE.xml
cp _magpie/$FILE.xml $FILE.xml










