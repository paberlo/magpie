package org.sat4j.tools;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.IOException;

import org.junit.Test;
import org.sat4j.minisat.SolverFactory;
import org.sat4j.minisat.core.Counter;
import org.sat4j.reader.LecteurDimacs;
import org.sat4j.reader.ParseFormatException;
import org.sat4j.specs.ContradictionException;
import org.sat4j.specs.TimeoutException;

public class BugSAT175 {

    @Test
    public void testWithInternalIterator() throws ParseFormatException,
            IOException, ContradictionException, TimeoutException {
        checkCountWithInternal("src/test/testfiles/bug175.cnf", 2);
    }

    @Test
    public void testWithInternalIteratorOne() throws ParseFormatException,
            IOException, ContradictionException, TimeoutException {
        checkCountWithInternal("src/test/testfiles/bug175-1.cnf", 2);
    }

    @Test
    public void testWithInternalIteratorTwo() throws ParseFormatException,
            IOException, ContradictionException, TimeoutException {
        checkCountWithInternal("src/test/testfiles/bug175-2.cnf", 3);
    }

    @Test
    public void testWithInternalIteratorThree() throws ParseFormatException,
            IOException, ContradictionException, TimeoutException {
        checkCountWithInternal("src/test/testfiles/bug175-3.cnf", 4);
    }

    @Test
    public void testWithInternalIteratorFour() throws ParseFormatException,
            IOException, ContradictionException, TimeoutException {
        checkCountWithInternal("src/test/testfiles/bug175-4.cnf", 6);
    }

    @Test
    public void testWithInternalIteratorFive() throws ParseFormatException,
            IOException, ContradictionException, TimeoutException {
        checkCountWithInternal("src/test/testfiles/bug175-5.cnf", 4);
    }

    @Test
    public void testWithInternalIteratorSix() throws ParseFormatException,
            IOException, ContradictionException, TimeoutException {
        checkCountWithInternal("src/test/testfiles/bug175-6.cnf", 3);
    }

    @Test
    public void testWithInternalIteratorSeven() throws ParseFormatException,
            IOException, ContradictionException, TimeoutException {
        checkCountWithInternal("src/test/testfiles/bug175-7.cnf", 2);
    }

    private void checkCountWithInternal(String file, int expectedNumberOfModels)
            throws ParseFormatException, IOException, ContradictionException,
            TimeoutException {
        var satSolver = SolverFactory.newDefault();
        var reader = new LecteurDimacs(satSolver);
        var p = reader.parseInstance(file);
        var counter = new Counter();
        SolutionFoundListener sfl = new SolutionFoundListener() {

            @Override
            public void onSolutionFound(int[] solution) {
                counter.inc();
            }

        };
        var enumerator = new SearchEnumeratorListener(sfl);
        satSolver.setSearchListener(enumerator);
        assertTrue(satSolver.isSatisfiable());
        assertEquals(expectedNumberOfModels,
                enumerator.getNumberOfSolutionFound());
    }

    @Test
    public void testWithExternalIterator() throws ParseFormatException,
            IOException, ContradictionException, TimeoutException {
        var satSolver = SolverFactory.newDefault();
        var reader = new LecteurDimacs(satSolver);
        var p = reader.parseInstance("src/test/testfiles/bug175.cnf");

        var enumerator = new ModelIterator(satSolver);
        while (enumerator.isSatisfiable()) {
            assertNotNull(enumerator.model());
        }
        assertEquals(2, enumerator.numberOfModelsFoundSoFar());
    }

}
