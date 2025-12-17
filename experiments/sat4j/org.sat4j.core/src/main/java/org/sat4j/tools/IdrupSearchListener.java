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

import org.sat4j.annotations.Feature;
import org.sat4j.core.LiteralsUtils;
import org.sat4j.specs.IConstr;
import org.sat4j.specs.ISolverService;

/**
 * Output an unsat proof using the Idrup format.
 * 
 * @author daniel
 * 
 * @param <S>
 *            a solver service
 * @since 3.0
 */
@Feature("searchlistener")
public class IdrupSearchListener<S extends ISolverService>
        extends ICnfSearchListener<S> {

    /**
     * 
     */
    private static final long serialVersionUID = 1L;

    public IdrupSearchListener(String filename) {
        super(filename);
    }

    @Override
    protected String header() {
        return "p idrup";
    }

    @Override
    public void learn(IConstr c) {
        out.print("l ");
        printConstr(c);
    }

    @Override
    public void delete(IConstr c) {
        out.print("d ");
        printConstr(c);
    }

    private void printConstr(IConstr c) {
        for (var i = 0; i < c.size(); i++) {
            out.print(LiteralsUtils.toDimacs(c.get(i)));
            out.print(" ");
        }
        out.println("0");
    }

    @Override
    public void learnUnit(int p) {
        out.print("l ");
        out.print(p);
        out.println(" 0");
    }
}
