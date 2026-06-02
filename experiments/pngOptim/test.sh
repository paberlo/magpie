#!/bin/sh
set -e

trap 'rm -f data/temp.png' EXIT

my_test() {
    INPUT=$1
    ./optipng-7.9.1/src/optipng/optipng "$INPUT" -o1 -out data/temp.png
    if ! file data/temp.png | grep -q "PNG image"; then
        echo "FAILED: output is not a valid PNG for input: $INPUT"
        exit 1
    fi
    rm -f data/temp.png
}

my_test data/logo.png
my_test data/granite.png
