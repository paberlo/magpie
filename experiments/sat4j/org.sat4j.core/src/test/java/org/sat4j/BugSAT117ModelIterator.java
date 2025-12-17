package org.sat4j;

import static org.junit.Assert.assertEquals;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import org.junit.Test;
import org.sat4j.core.VecInt;
import org.sat4j.minisat.SolverFactory;
import org.sat4j.specs.ContradictionException;
import org.sat4j.specs.ISolver;
import org.sat4j.specs.IVecInt;
import org.sat4j.specs.TimeoutException;
import org.sat4j.tools.GateTranslator;
import org.sat4j.tools.ModelIterator;

public class BugSAT117ModelIterator {
    private GateTranslator gateTranslator;
    private ISolver solver;
    private ModelIterator modelIterator;

    @Test
    public void testIt() {
        solver = SolverFactory.newLight();
        gateTranslator = new GateTranslator(solver);
        modelIterator = new ModelIterator(solver);
        Date begin = new Date();
        long beginTime = begin.getTime();

        // this code used to launch an OutOfMemoryError
        // due to the creation of too many new threads
        // see https://gitlab.ow2.org/sat4j/sat4j/-/issues/117
        Date now = new Date();
        while (now.getTime() - beginTime < 60000) {
            assertEquals(15, solve().size());
            now = new Date();
        }
    }

    private List<List<Integer>> solve() {
        List<List<Integer>> solution = new ArrayList<List<Integer>>();
        solver.newVar(5);

        // (x1 v -x5 v x4) ^ (-x1 v x5 v x3 v x4)
        try {
            gateTranslator.not(6, 5);
            IVecInt disjuncts1 = new VecInt(new int[] { 1, 6, 4 });
            gateTranslator.or(7, disjuncts1);
            gateTranslator.not(8, 1);
            IVecInt disjuncts2 = new VecInt(new int[] { 8, 5, 3, 4 });
            gateTranslator.or(9, disjuncts2);
            gateTranslator.gateTrue(9);
            while (modelIterator.isSatisfiable()) {
                final int[] model = modelIterator.model();
                List<Integer> modelList = new ArrayList<Integer>(model.length);
                for (int literal : model) {
                    modelList.add(literal);
                }
                solution.add(modelList);
            }
        } catch (ContradictionException ex) {
            ex.printStackTrace();
        } catch (TimeoutException ex) {
            ex.printStackTrace();
        } finally {
            gateTranslator.reset();
            solver.reset();
            modelIterator.reset();
        }

        return solution;
    }
}
