#!/bin/sh
#
# Usage: test.sh FOLD
#
# Quick functional filter MAGPIE runs before run.sh: the same oracle as run.sh
# (expected answer, valid model) on the first two training instances of the
# fold, without measuring anything. Validation instances are never used
# during the search.

exec bash run.sh "${1:?usage: test.sh FOLD}" --smoke
