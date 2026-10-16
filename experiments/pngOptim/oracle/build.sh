#!/usr/bin/env bash
# Builds oracle/pngpixcmp against the libpng and zlib that OptiPNG's own build
# leaves in third_party/. Run from experiments/pngOptim after "make".
set -e
SRC=optipng-7.9.1/third_party
gcc -O2 -Wall -I"$SRC/libpng" -I"$SRC/zlib" -o oracle/pngpixcmp oracle/pngpixcmp.c \
    "$SRC/libpng/libpng.a" "$SRC/zlib/libz.a" -lm
