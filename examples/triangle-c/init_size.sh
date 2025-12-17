#!/usr/bin/env bash
export LD_LIBRARY_PATH="/mnt/e/Dropbox/INVESTIGACION/GeneticImprovement/srcml/lib:$LD_LIBRARY_PATH"

srcml triangle.c > _magpie/triangle_size.c.xml
mv _magpie/triangle_size.c.xml triangle.c.xml
