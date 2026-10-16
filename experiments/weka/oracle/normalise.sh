#!/bin/sh
#
# Usage: oracle/normalise.sh < weka_stdout > normalised
#
# Drops the lines of Weka's stdout that describe the run rather than the
# classifier, so that outputs can be compared across runs and machines:
#   - "Time taken ..." (elapsed time);
#   - the JVM classloader warning about the mtj jar files, which embeds an
#     object identity hash that changes from one JVM to another.
# Used by both run.sh and oracle/make_reference.sh.

tr -d '\r' | grep -v -e '^Time taken' -e '^WARNING: core mtj jar files are not available'
exit 0
