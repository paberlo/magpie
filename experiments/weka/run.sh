#!/bin/bash
#
# Usage: run.sh FOLD [-v] [--smoke]
#
# Runs Weka's RandomForest (training-set evaluation plus 10-fold
# cross-validation, explicit seeds -S 1 -s 1) on every dataset listed in
# data/trainFOLD (data/validateFOLD with -v), measuring only the Java process
# with perf, and checks each run:
#   1. Java exits with status 0 and writes nothing to stderr (any exception
#      fails the run; Weka itself can print an exception and still exit 0);
#   2. stdout, without the "Time taken" lines, is identical to the output of
#      the unmodified program (data/expected/<dataset>.out, see
#      oracle/make_reference.sh): same model summary, same evaluation
#      statistics, same confusion matrices.
# The first failing check ends the run with status 1, so MAGPIE rejects the
# variant. On success the summed count is printed to stderr as
# "<total> cycles", the line MAGPIE's Perf<Cycles> fitness reads; the checks
# themselves are not measured.
#
# --smoke  checks only the first two datasets and measures nothing (test.sh).
# PERF_EVENT overrides the counted event; only for machines without a cycle
# counter (e.g. WSL), never in the experiments.

set -u

FOLD=${1:?usage: run.sh FOLD [-v] [--smoke]}
shift
LIST=data/train$FOLD
SMOKE=0
for arg in "$@"; do
    case $arg in
        -v) LIST=data/validate$FOLD ;;
        --smoke) SMOKE=1 ;;
        *) echo "run.sh: unknown option $arg" >&2; exit 2 ;;
    esac
done

EVENT=${PERF_EVENT:-cycles}
EXPECTED=data/expected
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "ORACLE FAILED: $*" >&2
    exit 1
}

CLASSIFY=(java -cp weka-src/build/classes weka.classifiers.trees.RandomForest -S 1 -s 1 -t)

[ -f "$LIST" ] || fail "missing $LIST"

n=0
total=0
while IFS= read -r arff || [ -n "$arff" ]; do
    arff=${arff%$'\r'}
    [ -n "$arff" ] || continue
    if [ "$SMOKE" -eq 1 ] && [ "$n" -ge 2 ]; then
        break
    fi
    n=$((n + 1))
    [ -f "$arff" ] || fail "missing input $arff"

    if [ "$SMOKE" -eq 1 ]; then
        "${CLASSIFY[@]}" "$arff" > "$TMP/out" 2> "$TMP/err" || fail "java exit status $? on $arff"
    else
        perf stat -x, -e "$EVENT" -o "$TMP/perf.txt" -- "${CLASSIFY[@]}" "$arff" \
            > "$TMP/out" 2> "$TMP/err" || fail "java exit status $? on $arff"
        count=$(awk -F, -v ev="$EVENT" 'index($3, ev) == 1 { print $1 }' "$TMP/perf.txt")
        case $count in
            '' | *[!0-9.]*) fail "perf could not count $EVENT on $arff: '$count'" ;;
        esac
        total=$(awk -v a="$total" -v b="$count" 'BEGIN { printf "%.0f", a + b }')
    fi

    [ ! -s "$TMP/err" ] || fail "$arff: java wrote to stderr: $(head -c 300 "$TMP/err" | tr '\n' ' ')"
    ref=$EXPECTED/$(basename "$arff" .arff).out
    [ -f "$ref" ] || fail "no reference output $ref"
    grep -v '^Time taken' "$TMP/out" | diff -q - <(tr -d '\r' < "$ref") > /dev/null \
        || fail "$arff: output differs from the unmodified program ($ref)"
done < "$LIST"

[ "$n" -gt 0 ] || fail "$LIST lists no datasets"
if [ "$SMOKE" -eq 0 ]; then
    echo "$total cycles" >&2
fi
exit 0
