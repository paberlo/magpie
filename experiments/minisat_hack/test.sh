#!/bin/sh

# Registrar una trampa para asegurarse de manejar señales y liberar recursos
#trap clean_up EXIT SIGINT  # test_timeout error does not unlock executable file

clean_up() {
#    # Finaliza cualquier proceso relacionado con el ejecutable en caso de error o interrupción
    pkill -f "./minisat_HACK_999ED_CSSC_static"
}



ARGV=$@

my_test() {
    FILENAME=$1
    EXPECTED=$2
    ./minisat_HACK_999ED_CSSC_static $FILENAME $ARGV > /dev/null
    RETURN=$?
    echo $RETURN
    if [ $RETURN -ne $((EXPECTED)) ]; then
        echo "FAILED ON FILE:" $FILENAME
        echo "GOT:" $RETURN
        echo "EXPECTED:" $EXPECTED
        exit -1
    fi
}

my_test data/uf50-01.cnf 10
my_test data/uf50-02.cnf 10
my_test data/uf100-01.cnf 10
my_test data/uf100-02.cnf 10
my_test data/uf150-01.cnf 10
my_test data/uf150-02.cnf 10

my_test data/uuf50-01.cnf 20
my_test data/uuf50-02.cnf 20
my_test data/uuf100-01.cnf 20
my_test data/uuf100-02.cnf 20
my_test data/uuf150-01.cnf 20
my_test data/uuf150-02.cnf 20



