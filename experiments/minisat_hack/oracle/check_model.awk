# Usage: awk -f oracle/check_model.awk solver_stdout instance.cnf
#
# Exit 0 if the assignment printed by the solver on its "v" lines satisfies
# every clause of the DIMACS instance, 1 otherwise. A variable missing from
# the assignment satisfies no literal, so an empty or partial model fails.
# The number of clauses read must match the "p cnf" header, as a check on the
# parsing itself. SATLIB files may end with a "%" line, which ends the
# clause list.

FNR == NR {
    sub(/\r$/, "")
    if ($1 == "v") {
        for (i = 2; i <= NF; i++) {
            lit = $i + 0
            if (lit == 0) continue
            var = lit < 0 ? -lit : lit
            if (var in value) duplicate = 1
            value[var] = lit > 0 ? 1 : -1
        }
    }
    next
}

{ sub(/\r$/, "") }
/^c/ { next }
/^p/ { declared = $4 + 0; next }
/^%/ { stop = 1 }
stop { next }

{
    for (i = 1; i <= NF; i++) {
        lit = $i + 0
        if (lit == 0) {
            if (open) { clauses++; if (!satisfied) unsatisfied++ }
            open = 0; satisfied = 0
            continue
        }
        open = 1
        var = lit < 0 ? -lit : lit
        if ((var in value) && value[var] == (lit > 0 ? 1 : -1)) satisfied = 1
    }
}

END {
    if (open) { clauses++; if (!satisfied) unsatisfied++ }
    if (duplicate) { print "check_model: a variable appears twice in the model" > "/dev/stderr"; exit 1 }
    if (clauses != declared) {
        printf "check_model: read %d clauses, header declares %d\n", clauses, declared > "/dev/stderr"; exit 1
    }
    if (unsatisfied) { printf "check_model: %d of %d clauses not satisfied\n", unsatisfied, clauses > "/dev/stderr"; exit 1 }
    exit 0
}
