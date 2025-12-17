/*******************************************************************************
 * SAT4J: a SATisfiability library for Java Copyright (C) 2004, 2012 Artois University and CNRS
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 *  http://www.eclipse.org/legal/epl-v10.html
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU Lesser General Public License Version 2.1 or later (the
 * "LGPL"), in which case the provisions of the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of the LGPL, and not to allow others to use your version of
 * this file under the terms of the EPL, indicate your decision by deleting
 * the provisions above and replace them with the notice and other provisions
 * required by the LGPL. If you do not delete the provisions above, a recipient
 * may use your version of this file under the terms of the EPL or the LGPL.
 *
 * Based on the original MiniSat specification from:
 *
 * An extensible SAT solver. Niklas Een and Niklas Sorensson. Proceedings of the
 * Sixth International Conference on Theory and Applications of Satisfiability
 * Testing, LNCS 2919, pp 502-518, 2003.
 *
 * See www.minisat.se for the original solver in C++.
 *
 * Contributors:
 *   CRIL - initial API and implementation
 *******************************************************************************/
package org.sat4j.tools;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.PrintStream;

import org.sat4j.annotations.Feature;
import org.sat4j.specs.ISolverService;
import org.sat4j.specs.IVecInt;
import org.sat4j.specs.Lbool;
import org.sat4j.specs.SearchListener;

/**
 * Output an incremental solving session using the icnf format.
 * 
 * @author daniel
 * 
 * @param <S>
 *            a solver service
 * @since 3.0
 */
@Feature("searchlistener")
public class ICnfSearchListener<S extends ISolverService>
        implements SearchListener<S> {

    /**
     * 
     */
    private static final long serialVersionUID = 1L;

    protected PrintStream out;
    private final File file;
    private S solverService;

    public ICnfSearchListener(String filename) {
        file = new File(filename);
    }

    @Override
    public void init(S solverService) {
        try {
            out = new PrintStream(new FileOutputStream(file), true);
            out.println(header());
            this.solverService = solverService;
        } catch (FileNotFoundException e) {
            out = System.out;
        }
    }

    protected String header() {
        return "p icnf";
    }

    @Override
    public void end(Lbool result) {
        if (result == Lbool.FALSE) {
            out.println("s UNSATISFIABLE");
            out.print("u ");
            IVecInt explanation = solverService.unsatExplanation();
            if (explanation != null) {
                for (var i = 0; i < explanation.size(); i++) {
                    out.print(explanation.get(i));
                    out.print(" ");
                }
            }
            out.println("0");
        } else if (result == Lbool.TRUE) {
            out.println("s SATISFIABLE");
            out.print("m ");
            int[] model = solverService.model();
            for (var i = 0; i < model.length; i++) {
                out.print(model[i]);
                out.print(" ");
            }
            out.println("0");
        }
    }

    @Override
    public void addClause(IVecInt clause) {
        out.print("i ");
        for (var i = 0; i < clause.size(); i++) {
            out.print(clause.get(i));
            out.print(" ");
        }
        out.println("0");
    }

    @Override
    public void checkSatisfiability(IVecInt assumptions, boolean global) {
        out.print("q ");
        for (var i = 0; i < assumptions.size(); i++) {
            out.print(assumptions.get(i));
            out.print(" ");
        }
        out.println("0");
    }
}
