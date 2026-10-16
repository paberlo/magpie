#!/bin/sh
#
# Usage: test.sh FOLD
#
# Quick functional filter MAGPIE runs before run.sh: the same oracle as run.sh
# (same -o2 option, same pixel and size checks) on the first two training
# images of the fold, without measuring anything. Validation images are never
# used during the search.

exec bash run.sh "${1:?usage: test.sh FOLD}" --smoke
