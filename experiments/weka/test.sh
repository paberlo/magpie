#!/bin/sh
#
# Usage: test.sh FOLD
#
# Quick functional filter MAGPIE runs before run.sh: the same oracle as run.sh
# (same seeds, same output comparison) on the first two training datasets of
# the fold, without measuring anything. Validation datasets are never used
# during the search.

exec bash run.sh "${1:?usage: test.sh FOLD}" --smoke
