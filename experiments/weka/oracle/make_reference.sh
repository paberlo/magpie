#!/usr/bin/env bash
#
# Usage: oracle/make_reference.sh [--check]
#
# Writes data/expected/<dataset>.out for every dataset listed in the fold
# files (data/train* and data/validate*): the stdout of the UNMODIFIED
# RandomForest, with the same command line as run.sh, filtered by
# oracle/normalise.sh. run.sh rejects any variant whose output differs.
# Run from experiments/weka on a pristine build (no RandomForest.java variant
# compiled into weka-src/build/classes).
#
# --check  recomputes the outputs and compares them with the stored ones
#          instead of overwriting them (to confirm another machine, or another
#          JVM, gives the same outputs).

set -euo pipefail
export LC_ALL=C   # byte order for the dataset list, the same on every machine

EXPECTED=data/expected
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/out"
tr -d '\r' < <(cat data/train? data/validate?) | sort -u | while read -r arff; do
    [ -n "$arff" ] || continue
    name=$(basename "$arff" .arff)
    java -cp weka-src/build/classes weka.classifiers.trees.RandomForest -S 1 -s 1 -t "$arff" \
        > "$TMP/raw" 2> "$TMP/err"
    if [ -s "$TMP/err" ]; then
        echo "ERROR: the unmodified program writes to stderr on $arff:" >&2
        head -3 "$TMP/err" >&2
        exit 1
    fi
    sh oracle/normalise.sh < "$TMP/raw" > "$TMP/out/$name.out"
done

if [ "${1:-}" = "--check" ]; then
    if diff -r "$EXPECTED" "$TMP/out"; then
        echo "OK: outputs match $EXPECTED ($(ls "$EXPECTED" | wc -l) datasets)"
    else
        echo "MISMATCH with $EXPECTED" >&2
        exit 1
    fi
else
    rm -rf "$EXPECTED"
    mkdir -p "$EXPECTED"
    cp "$TMP"/out/*.out "$EXPECTED"/
    echo "wrote $EXPECTED ($(ls "$EXPECTED" | wc -l) datasets)"
fi
