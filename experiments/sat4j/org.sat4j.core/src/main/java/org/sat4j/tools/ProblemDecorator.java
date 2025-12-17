package org.sat4j.tools;

import java.io.PrintWriter;

import org.sat4j.specs.IProblem;
import org.sat4j.specs.IVecInt;
import org.sat4j.specs.TimeoutException;

/**
 * Decorator design pattern for the IProblem interface.
 * 
 * @author leberre
 *
 * @param <T>
 * @since 2.3.6
 */
public class ProblemDecorator<T extends IProblem> implements IProblem {

    /**
     * 
     */
    private static final long serialVersionUID = 1L;
    private final T decorated;

    public ProblemDecorator(T decorated) {
        this.decorated = decorated;
    }

    @Override
    public boolean model(int variable) {
        return decorated.model(variable);
    }

    @Override
    public int[] model() {
        return decorated.model();
    }

    @Override
    public int[] primeImplicant() {
        return decorated.primeImplicant();
    }

    @Override
    public boolean primeImplicant(int p) {
        return decorated.primeImplicant(p);
    }

    @Override
    public boolean isSatisfiable() throws TimeoutException {
        return decorated.isSatisfiable();
    }

    @Override
    public boolean isSatisfiable(IVecInt assumps, boolean globalTimeout)
            throws TimeoutException {
        return decorated.isSatisfiable(assumps, globalTimeout);
    }

    @Override
    public boolean isSatisfiable(boolean globalTimeout)
            throws TimeoutException {
        return decorated.isSatisfiable(globalTimeout);
    }

    @Override
    public boolean isSatisfiable(IVecInt assumps) throws TimeoutException {
        return decorated.isSatisfiable(assumps);
    }

    @Override
    public int[] findModel() throws TimeoutException {
        return decorated.findModel();
    }

    @Override
    public int[] findModel(IVecInt assumps) throws TimeoutException {
        return decorated.findModel(assumps);
    }

    @Override
    public int nConstraints() {
        return decorated.nConstraints();
    }

    @Override
    public int newVar(int howmany) {
        return decorated.newVar(howmany);
    }

    @Override
    public int nVars() {
        return decorated.nVars();
    }

    @Override
    public void printInfos(PrintWriter out) {
        decorated.printInfos(out);
    }

    public T decorated() {
        return decorated;
    }

    @Override
    public int[] decisions() {
        return decorated.decisions();
    }

    @Override
    public void preprocessing() {
        decorated().preprocessing();
    }

}
