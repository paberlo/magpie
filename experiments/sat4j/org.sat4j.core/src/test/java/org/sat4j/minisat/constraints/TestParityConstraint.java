package org.sat4j.minisat.constraints;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;
import org.sat4j.core.VecInt;
import org.sat4j.minisat.SolverFactory;
import org.sat4j.specs.ISolver;
import org.sat4j.specs.TimeoutException;
import org.sat4j.tools.ModelIterator;

public class TestParityConstraint {

    @Test
    public void testParityTwo() throws TimeoutException {
        ISolver solver = SolverFactory.newDefault();
        solver.newVar(2);
        solver.addParity(VecInt.of(1, 2), true);
        assertTrue(solver.isSatisfiable());
        ModelIterator iterator = new ModelIterator(solver);
        assertTrue(iterator.isSatisfiable());
        iterator.model();
        assertTrue(iterator.isSatisfiable());
        iterator.model();
        assertFalse(iterator.isSatisfiable());
    }

    @Test
    public void testParityThree() throws TimeoutException {
        ISolver solver = SolverFactory.newDefault();
        solver.newVar(3);
        solver.addParity(VecInt.of(1, 2, 3), false);
        assertTrue(solver.isSatisfiable());
        ModelIterator iterator = new ModelIterator(solver);
        while (iterator.isSatisfiable()) {
            iterator.model();
        }
        assertEquals(4, iterator.numberOfModelsFoundSoFar());
    }

    @Test
    public void testParityThreeUnsat() throws TimeoutException {
        ISolver solver = SolverFactory.newDefault();
        solver.newVar(3);
        solver.addParity(VecInt.of(1, 2, 3), false);
        solver.addParity(VecInt.of(1, 2, 3), true);
        assertFalse(solver.isSatisfiable());
    }
}
