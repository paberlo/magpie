#!/bin/bash

SHDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
if [ -z "$SHDIR" ]; then SHDIR="."; fi

cd $SHDIR

cd sources/simp
make clean

make rs
cp -f minisat_HACK_999ED_CSSC_static ../..
