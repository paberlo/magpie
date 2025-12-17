package org.sat4j.tools.counting;

import java.io.IOException;

import org.sat4j.minisat.SolverFactory;
import org.sat4j.reader.LecteurDimacs;
import org.sat4j.reader.ParseFormatException;
import org.sat4j.reader.Reader;
import org.sat4j.specs.ContradictionException;
import org.sat4j.specs.ISolver;

public class CounterCLI {
    public static void main(String[] args)
            throws ParseFormatException, IOException, ContradictionException {
        ISolver solver = SolverFactory.newDefault();
        ApproxMC2 approxMC;
        String filename;
        if (args.length == 3) {
            double epsilon = Double.parseDouble(args[0]);
            double delta = Double.parseDouble(args[1]);
            filename = args[2];
            approxMC = new ApproxMC2(solver, epsilon, delta);

        } else {
            approxMC = new ApproxMC2(solver);
            if (args.length != 1) {
                System.out.println("A filename is expected!");
                return;
            }
            filename = args[0];
        }
        Reader reader = new LecteurDimacs(solver);
        reader.parseInstance(filename);
        System.out.println(approxMC.countModels());
    }
}
