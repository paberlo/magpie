#!/bin/sh
#ejecutar java dist/CUSTOM/sat4j-sat.jar sobre cada archivo del listado recibido como parametro (traint, validate,test...)

java -jar dist/CUSTOM/sat4j-sat.jar data/uf50-01.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uf50-02.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uf100-01.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uf100-02.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uf150-01.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uf150-02.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uf200-01.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uf200-02.cnf $@
# java -jar dist/CUSTOM/sat4j-sat.jar data/uf250-01.cnf $@
# java -jar dist/CUSTOM/sat4j-sat.jar data/uf250-02.cnf $@

java -jar dist/CUSTOM/sat4j-sat.jar data/uuf50-01.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uuf50-02.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uuf100-01.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uuf100-02.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uuf150-01.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uuf150-02.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uuf200-01.cnf $@
java -jar dist/CUSTOM/sat4j-sat.jar data/uuf200-02.cnf $@
# java -jar dist/CUSTOM/sat4j-sat.jar data/uuf250-01.cnf $@
# java -jar dist/CUSTOM/sat4j-sat.jar data/uuf250-02.cnf $@

exit 0
