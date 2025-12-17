package org.sat4j.reader;

import java.io.IOException;

import org.sat4j.core.VecInt;
import org.sat4j.specs.ContradictionException;
import org.sat4j.specs.ISolver;
import org.sat4j.specs.IVecInt;

public class KlauseReader extends DimacsReader {

    public KlauseReader(ISolver solver) {
        super(solver, "knf");
    }

    @Override
    protected boolean handleLine()
            throws ContradictionException, IOException, ParseFormatException {
        if (this.scanner.currentChar() == 'k') {
            // reading a klause
            this.scanner.next(); // skip k char
            int k = this.scanner.nextInt();
            IVecInt literals = new VecInt();
            do {
                literals.push(this.scanner.nextInt());
            } while (literals.last() != 0);
            literals.pop();
            this.solver.addAtLeast(literals, k);
            return true;
        }
        return super.handleLine();
    }

}
