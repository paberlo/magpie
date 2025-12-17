#!/bin/sh

#./optipng-7.9.1/src/optipng/optipng data/small_rgba8.png -o1 -out data/temp.png
#-07 would b the highest optimization level. we set the minimum to 1 to reduce runtime, since it does not change
#the executed code but the number of iterations. We are testing that the code runs, not the optimization level.
./optipng-7.9.1/src/optipng/optipng data/logo.png -o1 -out data/temp.png
rm data/temp.png
./optipng-7.9.1/src/optipng/optipng data/granite.png -o1 -out data/temp.png
rm data/temp.png
