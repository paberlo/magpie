package org.sat4j.tools;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;
import org.sat4j.core.VecInt;
import org.sat4j.minisat.SolverFactory;
import org.sat4j.specs.ContradictionException;
import org.sat4j.specs.ISolver;
import org.sat4j.specs.TimeoutException;

public class BugSAT176 {

    @Test
    public void testKatalinExample()
            throws ContradictionException, TimeoutException {
        ISolver solver = SolverFactory.newDefault();
        var idrup = new IdrupSearchListener<>("/tmp/test.idrup");
        var icnf = new ICnfSearchListener<>("/tmp/test.icnf");
        var both = new MultiTracing<>(icnf, idrup);
        solver.setSearchListener(both);
        solver.addClause(VecInt.of(-1, 3, 4));
        solver.addClause(VecInt.of(-1, 3, -4));
        solver.addClause(VecInt.of(-2, -3, 4));
        solver.addClause(VecInt.of(-2, -3, -4));
        assertFalse(solver.isSatisfiable(VecInt.of(1, 2), true));
        solver.addClause(VecInt.of(-1, 2));
        solver.addClause(VecInt.of(1, -2));
        assertTrue(solver.isSatisfiable(true));
        solver.addClause(VecInt.of(1, 2));
        assertFalse(solver.isSatisfiable(true));
    }

}
