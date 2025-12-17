import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

import java.util.function.Consumer;

import org.junit.Test;
import org.sat4j.core.VecInt;
import org.sat4j.minisat.SolverFactory;
import org.sat4j.specs.ISolver;
import org.sat4j.tools.ModelIterator;

public class BugMark {

    @Test
    public void testWithTimeout() {
        communTestCase(s -> s.setTimeoutOnConflicts(Integer.MAX_VALUE));
    }

    @Test
    public void testWithoutTimeout() {
        communTestCase(s -> {
        });

    }

    private void communTestCase(Consumer<ISolver> f) {
        final int MAXVAR = 3;
        final int NBCLAUSES = 2;

        int n = 0;
        while (n < 10000) {
            ISolver solver = SolverFactory.newDefault();
            solver.newVar(MAXVAR);
            solver.setExpectedNumberOfClauses(NBCLAUSES);
            f.accept(solver);

            try {
                solver.addClause(VecInt.of(1, 2, -3));
                solver.addClause(VecInt.of(1, 3));
                solver.addExactly(VecInt.of(1, 2, 3), 1);

                ISolver iterator = new ModelIterator(solver);

                int num = 1;
                while (iterator.isSatisfiable(false)) {
                    iterator.model();
                    // System.out.println("Got solution: " + num);
                    num++;
                }
                assertEquals(2, num);

                iterator.getStat();
                // solver.reset();
            } catch (Exception ex) {
                fail();
            }
            n++;
        }
    }

}
