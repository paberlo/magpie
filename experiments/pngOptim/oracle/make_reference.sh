#!/usr/bin/env bash
#
# Usage: oracle/make_reference.sh [--check]
#
# Writes data/expected/o2_sizes.txt: for every image in data/, the size in
# bytes of the file the UNMODIFIED OptiPNG writes with -o2. run.sh rejects any
# variant whose output is larger. Run from experiments/pngOptim on a pristine
# build (compile.sh on the original sources).
#
# --check  recomputes the sizes and compares them with the stored file instead
#          of overwriting it (to confirm another machine gives the same sizes).

set -euo pipefail
export LC_ALL=C   # byte order for data/*.png, the same on every machine

OPTIPNG=./optipng-7.9.1/src/optipng/optipng
SIZES=data/expected/o2_sizes.txt
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

for img in data/*.png; do
    "$OPTIPNG" "$img" -o2 -out "$TMP/out.png" >/dev/null 2>&1
    oracle/pngpixcmp "$img" "$TMP/out.png"
    echo "$img $(wc -c < "$TMP/out.png")"
    rm -f "$TMP/out.png"
done > "$TMP/sizes.txt"

if [ "${1:-}" = "--check" ]; then
    if diff "$SIZES" "$TMP/sizes.txt"; then
        echo "OK: sizes match $SIZES"
    else
        echo "MISMATCH with $SIZES" >&2
        exit 1
    fi
else
    mkdir -p "$(dirname "$SIZES")"
    cp "$TMP/sizes.txt" "$SIZES"
    echo "wrote $SIZES ($(wc -l < "$SIZES") images)"
fi
