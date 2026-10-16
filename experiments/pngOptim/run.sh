#!/bin/bash
#
# Usage: run.sh FOLD [-v] [--smoke]
#
# Runs OptiPNG -o2 on every image listed in data/trainFOLD (data/validateFOLD
# with -v), measuring only the OptiPNG process with perf, and checks each output:
#   1. OptiPNG exits with status 0 and writes the output file;
#   2. the output decodes to exactly the same pixels as the input
#      (oracle/pngpixcmp; OptiPNG is lossless);
#   3. the output is no larger than the one the unmodified OptiPNG produces for
#      that image (data/expected/o2_sizes.txt, see oracle/make_reference.sh),
#      which also covers images the original program cannot make smaller.
# The first failing check ends the run with status 1, so MAGPIE rejects the
# variant. On success the summed count is printed to stderr as
# "<total> cycles", the line MAGPIE's Perf<Cycles> fitness reads; the checks
# themselves are not measured.
#
# --smoke  checks only the first two images and measures nothing (test.sh).
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
OPTIPNG=./optipng-7.9.1/src/optipng/optipng
SIZES=data/expected/o2_sizes.txt
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "ORACLE FAILED: $*" >&2
    exit 1
}

[ -f "$LIST" ] || fail "missing $LIST"
[ -x oracle/pngpixcmp ] || fail "oracle/pngpixcmp is not built"

n=0
total=0
while IFS= read -r img || [ -n "$img" ]; do
    img=${img%$'\r'}
    [ -n "$img" ] || continue
    if [ "$SMOKE" -eq 1 ] && [ "$n" -ge 2 ]; then
        break
    fi
    n=$((n + 1))
    [ -f "$img" ] || fail "missing input $img"
    out=$TMP/out.png
    rm -f "$out"

    if [ "$SMOKE" -eq 1 ]; then
        "$OPTIPNG" "$img" -o2 -out "$out" >/dev/null 2>&1 || fail "optipng exit status $? on $img"
    else
        perf stat -x, -e "$EVENT" -o "$TMP/perf.txt" -- \
            "$OPTIPNG" "$img" -o2 -out "$out" >/dev/null 2>&1 || fail "optipng exit status $? on $img"
        count=$(awk -F, -v ev="$EVENT" 'index($3, ev) == 1 { print $1 }' "$TMP/perf.txt")
        case $count in
            '' | *[!0-9.]*) fail "perf could not count $EVENT on $img: '$count'" ;;
        esac
        total=$(awk -v a="$total" -v b="$count" 'BEGIN { printf "%.0f", a + b }')
    fi

    [ -s "$out" ] || fail "no output written for $img"
    oracle/pngpixcmp "$img" "$out" || fail "output pixels differ from the input for $img"
    ref=$(awk -v f="$img" '{ sub(/\r$/, "") } $1 == f { print $2 }' "$SIZES")
    [ -n "$ref" ] || fail "no reference size for $img in $SIZES"
    size=$(wc -c < "$out")
    [ "$size" -le "$ref" ] || fail "$img: output is $size bytes, the original program writes $ref"
done < "$LIST"

[ "$n" -gt 0 ] || fail "$LIST lists no images"
if [ "$SMOKE" -eq 0 ]; then
    echo "$total cycles" >&2
fi
exit 0
