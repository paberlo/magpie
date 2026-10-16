#!/usr/bin/env bash
#
# Usage: oracle/make_reference.sh [--check]
#
# Writes data/expected/answers.txt: for every instance listed in the fold
# files (data/train* and data/validate*), the exit status of the UNMODIFIED
# solver (10 = SAT, 20 = UNSAT). Before writing, each answer is checked
# against the SATLIB file name (uf* satisfiable, uuf* unsatisfiable) and each
# model against oracle/check_model.awk, so a wrong reference cannot be stored.
# Run from the experiment directory on a pristine build.
#
# --check  recomputes the answers and compares them with the stored file
#          instead of overwriting it (to confirm another machine gives the
#          same answers).

set -euo pipefail
export LC_ALL=C   # byte order for the instance list, the same on every machine

SOLVER=(./minisat_HACK_999ED_CSSC_static)
ANSWERS=data/expected/answers.txt
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

tr -d '\r' < <(cat data/train? data/validate?) | sort -u | while read -r cnf; do
    [ -n "$cnf" ] || continue
    set +e
    "${SOLVER[@]}" "$cnf" > "$TMP/out" 2> /dev/null
    status=$?
    set -e
    case $(basename "$cnf") in
        uuf*) want=20 ;;
        uf*) want=10 ;;
        *) echo "ERROR: cannot tell the expected answer of $cnf from its name" >&2; exit 1 ;;
    esac
    if [ "$status" -ne "$want" ]; then
        echo "ERROR: the unmodified solver returns $status on $cnf, expected $want" >&2
        exit 1
    fi
    if [ "$status" -eq 10 ]; then
        awk -f oracle/check_model.awk "$TMP/out" "$cnf"
    fi
    echo "$cnf $status"
done > "$TMP/answers.txt"

if [ "${1:-}" = "--check" ]; then
    if diff "$ANSWERS" "$TMP/answers.txt"; then
        echo "OK: answers match $ANSWERS ($(wc -l < "$ANSWERS") instances)"
    else
        echo "MISMATCH with $ANSWERS" >&2
        exit 1
    fi
else
    mkdir -p "$(dirname "$ANSWERS")"
    cp "$TMP/answers.txt" "$ANSWERS"
    echo "wrote $ANSWERS ($(wc -l < "$ANSWERS") instances)"
fi
