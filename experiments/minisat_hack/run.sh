#!/bin/bash
#
# Usage: run.sh FOLD [-v] [--smoke]
#
# Runs the solver on every instance listed in data/trainFOLD
# (data/validateFOLD with -v), measuring only the solver process with perf,
# and checks each answer:
#   1. the exit status (10 = SAT, 20 = UNSAT) and the "s" line agree with the
#      answer of the unmodified solver (data/expected/answers.txt, see
#      oracle/make_reference.sh), which also matches the SATLIB file name
#      (uf* satisfiable, uuf* unsatisfiable);
#   2. for satisfiable instances, the assignment on the "v" lines satisfies
#      every clause of the instance (oracle/check_model.awk).
# The first failing check ends the run with status 1, so MAGPIE rejects the
# variant. On success the summed count is printed to stderr as
# "<total> cycles", the line MAGPIE's Perf<Cycles> fitness reads; the checks
# themselves are not measured.
#
# --smoke  checks only the first two instances and measures nothing (test.sh).
# PERF_EVENT overrides the counted event; only for machines without a cycle
# counter (e.g. WSL), never in the experiments.

set -u
export LC_ALL=C   # same number formats (perf, awk) whatever the caller's locale
# Output cap for the program under test: a variant that prints without end fails
# its evaluation instead of filling the node's /tmp, where its output goes (the
# largest legitimate output, an optimised image, is 15 MB); and no core file of
# the killed program.
ulimit -f "${PROGRAM_FILE_KB:-65536}" -c 0
# Memory cap for the program under test: a variant that allocates without bound
# fails its evaluation instead of getting the whole run killed by SLURM (cgroup OOM).
ulimit -v "${PROGRAM_MEM_KB:-2097152}"

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

SOLVER=(./minisat_HACK_999ED_CSSC_static)
EVENT=${PERF_EVENT:-cycles}
ANSWERS=data/expected/answers.txt
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "ORACLE FAILED: $*" >&2
    exit 1
}

[ -f "$LIST" ] || fail "missing $LIST"

n=0
total=0
while IFS= read -r cnf || [ -n "$cnf" ]; do
    cnf=${cnf%$'\r'}
    [ -n "$cnf" ] || continue
    if [ "$SMOKE" -eq 1 ] && [ "$n" -ge 2 ]; then
        break
    fi
    n=$((n + 1))
    [ -f "$cnf" ] || fail "missing input $cnf"
    expected=$(awk -v f="$cnf" '{ sub(/\r$/, "") } $1 == f { print $2 }' "$ANSWERS")
    [ -n "$expected" ] || fail "no reference answer for $cnf in $ANSWERS"

    if [ "$SMOKE" -eq 1 ]; then
        "${SOLVER[@]}" "$cnf" > "$TMP/out" 2> "$TMP/err"
        status=$?
    else
        perf stat -x, -e "$EVENT" -o "$TMP/perf.txt" -- "${SOLVER[@]}" "$cnf" > "$TMP/out" 2> "$TMP/err"
        status=$?
        count=$(awk -F, -v ev="$EVENT" 'index($3, ev) == 1 { print $1 }' "$TMP/perf.txt")
        case $count in
            '' | *[!0-9.]*) fail "perf could not count $EVENT on $cnf: '$count'" ;;
        esac
        total=$(awk -v a="$total" -v b="$count" 'BEGIN { printf "%.0f", a + b }')
    fi

    [ "$status" -eq "$expected" ] || fail "$cnf: exit status $status, expected $expected"
    if [ "$expected" -eq 10 ]; then
        grep -qx 's SATISFIABLE' "$TMP/out" || fail "$cnf: no 's SATISFIABLE' line"
        awk -f oracle/check_model.awk "$TMP/out" "$cnf" || fail "$cnf: the model does not satisfy the instance"
    else
        grep -qx 's UNSATISFIABLE' "$TMP/out" || fail "$cnf: no 's UNSATISFIABLE' line"
    fi
done < "$LIST"

[ "$n" -gt 0 ] || fail "$LIST lists no instances"
if [ "$SMOKE" -eq 0 ]; then
    echo "$total cycles" >&2
fi
exit 0
