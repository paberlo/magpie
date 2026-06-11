#!/usr/bin/env bash
set -e

FILE=Solver.java

# write_variant only writes $FILE when the patch actually changes the source;
# if absent, the static jar (original) is already correct
if [ ! -f "$FILE" ]; then
    exit 0
fi

BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT

javac -d "$BUILD_DIR" -cp "dist/CUSTOM/org.sat4j.core.jar:dist/CUSTOM/lib/*" $FILE
jar uf dist/CUSTOM/org.sat4j.core.jar -C "$BUILD_DIR" org/sat4j/minisat/core/Solver.class
