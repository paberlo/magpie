/*******************************************************************************
 * SAT4J: a SATisfiability library for Java Copyright (C) 2004-2008 Daniel Le Berre
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
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
 *******************************************************************************/
package org.sat4j.minisat.constraints.cnf;

import static org.sat4j.Messages.NOT_IMPLEMENTED_YET;

import java.io.Serializable;

import org.sat4j.annotations.Feature;
import org.sat4j.core.VecInt;
import org.sat4j.minisat.core.ILits;
import org.sat4j.specs.Constr;
import org.sat4j.specs.IVecInt;
import org.sat4j.specs.MandatoryLiteralListener;
import org.sat4j.specs.Propagatable;
import org.sat4j.specs.UnitPropagationListener;
import org.sat4j.specs.VarMapper;

/**
 * Concise representation of binary clauses.
 * 
 * @author leberre
 */
@Feature("constraint")
public class BinaryClauses implements Constr, Propagatable, Serializable {

    private static final long serialVersionUID = 1L;

    private final ILits voc;

    private final IVecInt clauses = new VecInt();

    private final int reason;

    private int conflictindex = -1;

    /**
     * 
     */
    public BinaryClauses(ILits voc, int p) {
        this.voc = voc;
        this.reason = p;
    }

    public void addBinaryClause(int p) {
        clauses.push(p);
    }

    public void removeBinaryClause(int p) {
        clauses.remove(p);
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#remove()
     */
    public void remove() {
        throw new UnsupportedOperationException();
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#propagate(org.sat4j.minisat.
     * UnitPropagationListener , int)
     */
    public boolean propagate(UnitPropagationListener s, int p) {
        voc.watch(p, this);
        for (var i = 0; i < clauses.size(); i++) {
            int q = clauses.get(i);
            if (!s.enqueue(q, this)) {
                conflictindex = i;
                return false;
            }
        }
        return true;
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#simplify()
     */
    public boolean simplify() {
        return false;
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#undo(int)
     */
    public void undo(int p) {
        // no to do
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#calcReason(int, org.sat4j.datatype.VecInt)
     */
    public void calcReason(int p, IVecInt outReason) {
        outReason.push(this.reason ^ 1);
        if (p == ILits.UNDEFINED) {
            assert conflictindex > -1;
            outReason.push(clauses.get(conflictindex) ^ 1);
        }
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#learnt()
     */
    public boolean learnt() {
        return false;
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#locked()
     */
    public boolean locked() {
        return false;
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#setLearnt()
     */
    public void setLearnt() {
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#register()
     */
    public void register() {
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#size()
     */
    public int size() {
        return clauses.size();
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.sat4j.minisat.Constr#get(int)
     */
    public int get(int i) {
        throw new UnsupportedOperationException();
    }

    public void assertConstraint(UnitPropagationListener s) {
        throw new UnsupportedOperationException();
    }

    public boolean canBePropagatedMultipleTimes() {
        return true;
    }

    public String toString(VarMapper mapper) {
        throw new UnsupportedOperationException(NOT_IMPLEMENTED_YET);
    }

    public void propagatePI(MandatoryLiteralListener l, int p) {
        for (var i = 0; i < clauses.size(); i++) {
            l.isMandatory(clauses.get(i));
        }
    }

    public Constr toConstraint() {
        return this;
    }

    public void remove(UnitPropagationListener upl) {
        throw new UnsupportedOperationException(
                "Cannot remove all the binary clauses at once!");
    }

    public void calcReasonOnTheFly(int p, IVecInt trail, IVecInt outReason) {
        throw new UnsupportedOperationException(NOT_IMPLEMENTED_YET);
    }

    public void assertConstraintIfNeeded(UnitPropagationListener s) {
        throw new UnsupportedOperationException(NOT_IMPLEMENTED_YET);
    }

    public boolean canBeSatisfiedByCountingLiterals() {
        throw new UnsupportedOperationException(NOT_IMPLEMENTED_YET);
    }

    public int requiredNumberOfSatisfiedLiterals() {
        throw new UnsupportedOperationException(NOT_IMPLEMENTED_YET);
    }

    public boolean isSatisfied() {
        throw new UnsupportedOperationException(NOT_IMPLEMENTED_YET);
    }

    public int getAssertionLevel(IVecInt trail, IVecInt trailLim, int decisionLevel, ILits voc) {
        throw new UnsupportedOperationException(NOT_IMPLEMENTED_YET);
    }

    @Override
    public String dump() {
        throw new UnsupportedOperationException(NOT_IMPLEMENTED_YET);
    }
}
