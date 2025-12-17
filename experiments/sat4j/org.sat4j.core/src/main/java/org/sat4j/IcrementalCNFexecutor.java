package org.sat4j;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import org.sat4j.core.VecInt;
import org.sat4j.minisat.SolverFactory;
import org.sat4j.specs.ContradictionException;
import org.sat4j.specs.ISolver;
import org.sat4j.specs.IVecInt;
import org.sat4j.specs.Lbool;
import org.sat4j.specs.TimeoutException;
import org.sat4j.tools.IdrupSearchListener;

/**
 * Simple class to execute incrementally a SAT solver according to an icnf
 * scenario.
 * 
 * The executor is simple, based on classical Java components. I will not scale
 * with icnf files of several MB. A more efficient one may be developed in a
 * near future.
 * 
 * @author leberre
 * @since 3.0
 */
public class IcrementalCNFexecutor {

    private static Lbool status = Lbool.UNDEFINED;

    private static IVecInt toVecInt(String[] tokens) {
        IVecInt literals = new VecInt(tokens.length - 2);
        for (int i = 1; i < tokens.length - 1; i++) {
            literals.push(Integer.valueOf(tokens[i]));
        }
        if (!"0".equals(tokens[tokens.length - 1])) {
            throw new IllegalStateException(
                    "List of literals should end with 0");
        }
        return literals;
    }

    private static void handleLine(String line, ISolver solver)
            throws ContradictionException, TimeoutException {
        String[] tokens = line.split(" ");
        switch (tokens[0]) {
        case "p":
            if (!"icnf".equals(tokens[1])) {
                throw new IllegalStateException(
                        "only icnf format is supported");
            }
            break;
        case "i":
            solver.addClause(toVecInt(tokens));
            if (status != Lbool.UNDEFINED) {
                status = Lbool.UNDEFINED;
            }
            break;
        case "q":
            if (solver.isSatisfiable(toVecInt(tokens), true)) {
                status = Lbool.TRUE;
            } else {
                status = Lbool.FALSE;
            }
            break;
        case "s":
            if (status == Lbool.TRUE) {
                if (!"SATISFIABLE".equals(tokens[1])) {
                    throw new IllegalStateException(
                            "Formula should be found SAT");
                }
            } else if (status == Lbool.FALSE) {
                if (!"UNSATISFIABLE".equals(tokens[1])) {
                    throw new IllegalStateException(
                            "Formula should be found UNSAT");
                }
            } else {
                // status == Lbool.UNDEFINED
                throw new IllegalStateException(
                        "Satisfiability of the formula could not be decided");
            }
            break;
        case "u":
            // do not use that information yet
            break;
        case "m":
            // do not use that information yet
            break;
        default:
            throw new IllegalStateException("unsupported command " + tokens[0]);
        }

    }

    public static void main(String[] args)
            throws IOException, ContradictionException, TimeoutException {
        var icnffilename = args[0];
        var path = Path.of(icnffilename);
        var idrup = new IdrupSearchListener<>(
                icnffilename.substring(0, icnffilename.length() - 4) + "idrup");
        ISolver solver = SolverFactory.newDefault();
        solver.setSearchListener(idrup);
        for (String line : Files.readAllLines(path)) {
            handleLine(line, solver);
        }
    }
}
