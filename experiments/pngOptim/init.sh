#!/usr/bin/env bash
#needed due to WSL environment
export LD_LIBRARY_PATH="/mnt/e/Dropbox/INVESTIGACION/GeneticImprovement/srcml/lib:$LD_LIBRARY_PATH"
set -e  # fail at first error

#CACHE=$MAGPIE_ROOT/_magpie_cache
#ARCHIVE=optipng-7.9.1.tar.gz
FOLD=optipng-7.9.1/src/optipng

#mkdir -p _magpie_cache #$CACHE
#cp $ARCHIVE _magpie_cache/ #$CACHE

#  setup pre-computed XML AST
#cd _magpie_cache/
#tar xzf $ARCHIVE #$CACHE/$ARCHIVE*  #from sourceforge
srcml $FOLD/optipng.c > _magpie/optipng.c.xml
srcml $FOLD/optim.c > _magpie/optim.c.xml
cp _magpie/optipng.c.xml optipng.c.xml
cp _magpie/optim.c.xml optim.c.xml

