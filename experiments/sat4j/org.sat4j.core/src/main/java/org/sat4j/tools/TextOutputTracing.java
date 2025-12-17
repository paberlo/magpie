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

import java.util.Map;

import org.sat4j.annotations.Feature;
import org.sat4j.specs.IConstr;
import org.sat4j.specs.ISolverService;
import org.sat4j.specs.Lbool;
import org.sat4j.specs.RandomAccessModel;
import org.sat4j.specs.SearchListener;

/**
 * Debugging Search Listener allowing to follow the search in a textual way.
 * 
 * @author daniel
 * @since 2.2
 */
@Feature("searchlistener")
public class TextOutputTracing<T> implements SearchListener<ISolverService> {

    private static final long serialVersionUID = 1L;

    private final Map<Integer, T> mapping;

    /**
     * @since 2.1
     */
    public TextOutputTracing(Map<Integer, T> mapping) {
        this.mapping = mapping;
    }

    private String node(int dimacs) {

        if (this.mapping != null) {
            int variable = Math.abs(dimacs);
            var t = this.mapping.get(variable);
            if (t != null) {
                if (dimacs > 0) {
                    return t.toString();
                }
                return "-" + t.toString();
            }
        }
        return Integer.toString(dimacs);
    }

    @Override
    public void assuming(int p) {
        System.out.println("assuming " + node(p));
    }

    @Override
    public void propagating(int p) {
        System.out.println("propagating " + node(p));
    }

    @Override
    public void enqueueing(int p, IConstr reason) {
        System.out.println("enqueueing " + node(p));
    }

    @Override
    public void backtracking(int p) {
        System.out.println("backtracking " + node(p));
    }

    @Override
    public void adding(int p) {
        System.out.println("adding " + node(p));
    }

    @Override
    public void learn(IConstr clause) {
        System.out.println("learning " + clause);

    }

    @Override
    public void learnUnit(int p) {
        System.out.println("learning unit " + p);

    }

    @Override
    public void delete(IConstr c) {

    }

    @Override
    public void conflictFound(IConstr confl, int dlevel, int trailLevel) {
        System.out.println("conflict ");
    }

    @Override
    public void conflictFound(int p) {
        System.out.println("conflict during propagation");
    }

    @Override
    public void solutionFound(int[] model, RandomAccessModel lazyModel) {
        System.out.println("solution found ");
    }

    @Override
    public void beginLoop() {
    }

    @Override
    public void start() {
    }

    @Override
    public void end(Lbool result) {
    }

    @Override
    public void restarting() {
        System.out.println("restarting ");
    }

    public void backjump(int backjumpLevel) {
        System.out.println("backjumping to decision level " + backjumpLevel);
    }

    @Override
    public void init(ISolverService solverService) {
    }

    @Override
    public void cleaning() {
        System.out.println("cleaning");
    }

}
